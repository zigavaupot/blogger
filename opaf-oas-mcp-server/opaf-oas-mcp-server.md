# An MCP Server for Oracle Analytics Server: Connecting OAS to OPAF Agents

<!-- IMAGE (featured): architecture diagram. OPAF agent in subnet-opaf-private -> HTTP /mcp (Bearer token, NSG nsg-oas-mcp) -> oas-mcp Python service on oas001 -> SOAP /analytics-ws -> OAS bi_server1 :9502. Based on the ASCII diagram in RUNBOOK.md section 1. -->
![OPAF agent querying Oracle Analytics Server through a custom MCP server](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/00-oas-mcp-architecture.png)

Oracle Analytics Cloud has an MCP server built in. Oracle Analytics Server does not. Many customers run OAS on premises or on their own compute, and their semantic models hold years of curated business logic that AI agents should be able to use instead of rebuilding it from raw tables.

In this post I build a small MCP server for OAS in Python, run it as a service next to OAS on an OCI compute instance, and connect it to an agent in Oracle Private Agent Factory (OPAF). The server exposes four read-only tools: list subject areas, describe a subject area, run Logical SQL and a connectivity check. Under the hood it uses the OAS SOAP web services, which have been part of the product since OBIEE. The result is an OPAF agent that answers business questions from the OAS semantic model.

## Architecture

The environment runs in my OCI tenancy in Frankfurt, in one VCN (`vcn-analytics-shared`) with two subnets:

- `oas001` is an Oracle Linux 8.10 compute instance with OAS, in `subnet-oas-public` (10.0.1.0/24). The MCP server runs on the same host, so it talks to OAS on `localhost`.
- OPAF runs on `agentfactoryvm` in `subnet-opaf-private` (10.0.3.0/24).

<div class="zv-table-compact" markdown="1">

| Layer | Choice |
|---|---|
| MCP transport | Streamable HTTP (stateless, JSON responses), endpoint `/mcp`, health check `/health` |
| Authentication | Bearer token (`MCP_API_KEY`) |
| Network | Port 8000 open only to the OPAF subnet, through a dedicated NSG |
| OAS access | SOAP web services under `/analytics-ws/saw.dll` |
| Query scope | Read-only: only Logical SQL `SELECT` is allowed |

</div>

### Why the SOAP web services

The SOAP web services under `/analytics-ws/saw.dll` provide exactly the three things an agent needs: metadata about subject areas, column details and query execution. A quick check on `oas001` shows whether they respond:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9502/analytics-ws/saw.dll/wsdl/v12   # expect 200
```

Working through the semantic layer has a practical benefit. The agent writes Logical SQL against subject areas, so joins, aggregation rules, calculated measures and data security defined in the OAS semantic model all apply. The agent never sees physical tables.

## The four MCP tools

<div class="zv-table-compact" markdown="1">

| Tool | Purpose | OAS web service |
|---|---|---|
| `get_server_info` | Connectivity check, OAS user in use | nQSessionService.getCurUser |
| `list_subject_areas` | List subject areas | metadataService.getSubjectAreas |
| `describe_subject_area` | Tables (folders) and columns; columns with an aggregation rule are measures | metadataService.describeSubjectArea |
| `execute_logical_sql` | Run a read-only Logical SQL `SELECT`, return columns and rows | xmlViewService.executeSQLQuery / fetchNext |

</div>

The order follows how an agent should work: find the subject area, learn its exact table and column names, then query. The aggregation rule returned by `describe_subject_area` tells the agent which columns are measures, which is all it needs to know, because Logical SQL has no joins and no `GROUP BY`. OAS aggregates measures by the attributes selected.

## The code

The project has two main files, and the split is deliberate:

- `oas_client.py` talks only to OAS: logon, subject areas, describe, Logical SQL, sorting and top-N. It contains no MCP code.
- `server.py` is the MCP server built with FastMCP. It wraps the client methods as tools and adds the HTTP layer with the Bearer token check and `/health`.

With this split I can test OAS access with `test_oas.py` before MCP is involved at all. Together the two files are about 520 lines of Python. The dependencies are in `requirements.txt`:

```
mcp>=1.25,<2
requests>=2.31
uvicorn>=0.30
python-dotenv>=1.0
```

### Talking to OAS

Every call is a SOAP envelope posted to `saw.dll` with the service name in the `SoapImpl` parameter. The client logs on once with `nQSessionService`, keeps the session ID and logs on again if the session expires. Running Logical SQL looks like this:

```python
root = self._call(
    "xmlViewService",
    "<v12:executeSQLQuery>"
    f"<v12:sql>{_esc(sql)}</v12:sql>"
    "<v12:outputFormat>SAWRowsetSchemaAndData</v12:outputFormat>"
    "<v12:executionOptions><v12:async>false</v12:async>"
    f"<v12:maxRowsPerPage>{page}</v12:maxRowsPerPage>"
    "<v12:refresh>true</v12:refresh><v12:presentationInfo>true</v12:presentationInfo>"
    "<v12:type>query</v12:type></v12:executionOptions>"
    "<v12:sessionID>{sid}</v12:sessionID></v12:executeSQLQuery>",
)
```

`SAWRowsetSchemaAndData` returns an XML schema with the column headings together with the rows. The client reads the column headings and data types from the schema, converts numeric values and fetches further pages with `fetchNext` until the result is complete or the row limit is reached.

### Behaviour of the OAS web service

Three things in the OAS answers are handled in code, so the agent does not have to deal with them:

- **Names come back in double quotes** (`"Sales Facts"`). The client removes the quotes, so the names returned by `describe_subject_area` can be used directly in Logical SQL.
- **`executeSQLQuery` ignores `ORDER BY` and `FETCH FIRST n ROWS ONLY`.** The client parses both clauses from the query, sorts the rows and applies the row limit itself. Without this, "which region has the highest revenue" would return an unsorted list.
- **Large results.** If a result has more rows than `MAX_ROWS`, sorting and top-N apply only to the rows fetched. The tool then returns a `warning` that asks the agent to add filters.

### Read-only by design

Logical SQL can contain `EXECUTE PHYSICAL`, which sends SQL straight to a database connection. An agent must never do that, so every query passes a check before it reaches OAS:

```python
# Words that must never appear in a query sent by an AI agent (read-only PoC).
FORBIDDEN_SQL = re.compile(
    r"\b(EXECUTE\s+PHYSICAL|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|MERGE|CALL|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
```

`check_read_only` first removes quoted names and strings, so a column called `"Last Update Date"` does not trigger the filter. Then it requires the statement to start with `SELECT` (optionally after `SET VARIABLE ...;`) and rejects any forbidden keyword.

### The MCP server

FastMCP turns each Python function into a tool. The docstring becomes the tool description, which the agent's LLM reads to decide when and how to call the tool, so I put the Logical SQL rules there:

```python
@mcp.tool()
async def execute_logical_sql(sql: str, max_rows: int = 100) -> dict:
    """Execute a read-only Logical SQL SELECT against Oracle Analytics Server and return
    column headings and rows.

    Logical SQL rules:
      - Reference columns as "Table"."Column" exactly as returned by describe_subject_area.
      - FROM contains only the subject area name in double quotes, e.g. FROM "Sample Sales".
      - No joins and no GROUP BY: measures are aggregated automatically by the attributes selected.
      - Filter with WHERE, sort with ORDER BY, limit with FETCH FIRST n ROWS ONLY.

    Args:
        sql: the Logical SQL SELECT statement
        max_rows: maximum number of rows to return (default 100)
    """
    limit = max(1, min(int(max_rows), MAX_ROWS))
    log.info("Logical SQL (max %s rows): %s", limit, sql)
    return await _run(oas.execute_logical_sql, sql, limit)
```

The SOAP calls are blocking, so `_run` executes them in a worker thread and turns OAS errors into a readable tool error ("Oracle Analytics error: ..."). The server is created with `stateless_http=True` and `json_response=True`: every request stands on its own, and answers are plain JSON instead of an event stream.

Authentication is a small ASGI middleware in front of the MCP app. It requires `Authorization: Bearer <MCP_API_KEY>` on every request except `/health`:

```python
headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
token = headers.get("authorization", "")
token = token[7:] if token.lower().startswith("bearer ") else headers.get("x-api-key", "")
if token != self.api_key:
    return await JSONResponse({"error": "unauthorized"}, status_code=401)(scope, receive, send)
```

## Installing the server on oas001

Oracle Linux 8 ships with Python 3.6, which is too old for the MCP SDK. I use Python 3.11 (`/usr/bin/python3.11`). Outbound internet access is needed once, for `pip install`.

From my Mac I copy the project to the server:

```bash
cd ~/Documents/GitHub
scp -i ~/.ssh/oas001_key -r oas-mcp-server opc@<oas001-public-ip>:/tmp/
```

On `oas001` I put it in `/opt/oas-mcp-server` and create the virtual environment:

```bash
sudo mkdir -p /opt/oas-mcp-server
sudo cp -r /tmp/oas-mcp-server/. /opt/oas-mcp-server/
sudo chown -R opc:opc /opt/oas-mcp-server

cd /opt/oas-mcp-server
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Configuration

All settings come from a `.env` file. I generate a random API key and fill in the OAS password:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"    # -> value for MCP_API_KEY
nano .env
chmod 600 .env
```

```ini
OAS_URL=http://localhost:9502
OAS_USER=admin
OAS_PASSWORD=<OAS admin password>
OAS_VERIFY_SSL=true
OAS_TIMEOUT=120
MAX_ROWS=500

MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_API_KEY=<generated key>
```

`.env` stays out of Git.

### Testing OAS access without MCP

`test_oas.py` uses only the client, so it confirms that the SOAP layer works before the MCP server runs. My test subject area is `MCP Test Sales`:

```bash
python test_oas.py
python test_oas.py "MCP Test Sales"
python test_oas.py --sql 'SELECT "Sales Details"."REGION", "Sales Facts"."REVENUE" FROM "MCP Test Sales" ORDER BY 2 DESC FETCH FIRST 1 ROWS ONLY'
```

The first call logs on and lists the subject areas, the second lists tables and columns without quotes, and the third returns one row: the region with the highest revenue. The last test also proves that sorting and top-N work, because OAS itself ignores both.

<!-- IMAGE: terminal on oas001 running the three test_oas.py commands: "Connected as: admin", subject area list, the [table] / column / data type / aggregation listing for MCP Test Sales, and the one-row JSON result. -->
![test_oas.py: logon, subject areas, describe and a Logical SQL query](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/01-test-oas.png)

### Running as a systemd service

The unit file runs the server as `opc` from `/opt/oas-mcp-server`, starts it on boot and restarts it on failure:

```ini
[Unit]
Description=Oracle Analytics Server MCP server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=opc
WorkingDirectory=/opt/oas-mcp-server
ExecStart=/opt/oas-mcp-server/venv/bin/python server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp /opt/oas-mcp-server/oas-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now oas-mcp
sudo systemctl status oas-mcp --no-pager | head -8      # Active: active (running)
curl http://localhost:8000/health                        # {"status":"ok",...}
```

### Testing the MCP endpoint

Two checks with `curl`: a request without a key must be rejected, and `tools/list` with the key must return the four tool names.

```bash
KEY=$(grep ^MCP_API_KEY /opt/oas-mcp-server/.env | cut -d= -f2)

# without key -> 401
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/mcp

# list tools -> 4 names
curl -s -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 -m json.tool | grep '"name"'
```

`tools/list` is the same first request OPAF sends after connecting, so if this works, the server side is ready.

<!-- IMAGE: terminal on oas001: systemctl status oas-mcp (active/running), curl /health, the 401 check and the tools/list output with the four "name" lines. -->
![oas-mcp service running, health check, 401 without key and tools/list](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/02-mcp-service-curl.png)

## Opening the network for OPAF only

Port 8000 must be reachable from OPAF and from nowhere else. Two layers need a rule.

The OS firewall on `oas001`:

```bash
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports            # 8000/tcp
```

In OCI I create a dedicated Network Security Group, so the existing OAS security lists and NSGs stay unchanged: **Networking → Virtual Cloud Networks → `vcn-analytics-shared` → Network Security Groups → Create Network Security Group**.

<div class="zv-table-compact" markdown="1">

| Field | Value |
|---|---|
| Name | `nsg-oas-mcp` |
| Compartment | `shared` |
| Direction | Ingress |
| Stateless | No |
| Source type / CIDR | CIDR / `10.0.3.0/24` (subnet-opaf-private) |
| IP protocol | TCP |
| Destination port | `8000` |
| Description | `OPAF -> OAS MCP server` |

</div>

Then I attach it to the instance: **Compute → Instances → `oas001` → Networking → Attached VNICs → VNIC `oas001` → Network Security Groups → Edit**, add `nsg-oas-mcp` and save.

<!-- IMAGE: OCI Console, NSG nsg-oas-mcp with the single ingress rule (source 10.0.3.0/24, TCP, destination port 8000). Optionally a second image of the oas001 VNIC with the NSG attached. -->
![NSG nsg-oas-mcp allowing TCP 8000 from the OPAF subnet](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/03-nsg-oas-mcp.png)

On the OPAF side nothing changes: `subnet-opaf-private` uses the Default Security List, which allows all egress. Port 8000 is not open to the internet, because the security list of `subnet-oas-public` allows only SSH from outside.

To check the path manually, I open a Bastion port forwarding session to the OPAF VM and run, on `agentfactoryvm`:

```bash
curl -m 5 http://10.0.1.205:8000/health
```

A timeout here points to the NSG or the firewall. OPAF itself does not need the Bastion; it connects to the MCP server directly.

## Connecting OPAF

### Proxy Settings

By default OPAF refuses MCP servers on private IP addresses and over plain HTTP. Both apply here, so as an OPAF administrator I change two preferences in **Application Settings → Proxy Settings**:

<div class="zv-table-compact" markdown="1">

| Preference | Value | Why |
|---|---|---|
| Allow Insecure Http Urls | **Yes** | The MCP server uses HTTP inside the VCN |
| Allow User Supplied Proxy | No | Not needed |
| Block Private Outbound Urls | **No** | The MCP server is on a private IP (10.0.1.205) |

</div>

These settings are global for the OPAF instance. Without them, registration fails with "MCP server URL must use https" or "resolves to a private or non-routable network address".

<!-- IMAGE: OPAF Application Settings, Proxy Settings page with Allow Insecure Http Urls = Yes and Block Private Outbound Urls = No. -->
![OPAF Proxy Settings](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/04-opaf-proxy-settings.png)

HTTP is acceptable for this setup because the traffic stays inside the private VCN, the NSG admits only the OPAF subnet, and every request needs the Bearer token. The server also supports TLS (`MCP_SSL_CERTFILE` and `MCP_SSL_KEYFILE` in `.env`), but OPAF accepts only certificates from a CA it trusts and rejects self-signed ones. With a trusted certificate, Allow Insecure Http Urls can go back to No.

### Registering the MCP server

In OPAF: **Add MCP server**

- Server name: `oas001-mcp`
- Server URL: `http://10.0.1.205:8000/mcp`
- Authentication mode: **Bearer Token**
- Bearer token: only the value of `MCP_API_KEY`, without the word `Bearer`

I read the key on `oas001` with `grep ^MCP_API_KEY /opt/oas-mcp-server/.env | cut -d= -f2`. **Test connection** returns "MCP connection successful", then **Add MCP server**.

<!-- IMAGE: OPAF Add MCP server dialog for oas001-mcp (URL http://10.0.1.205:8000/mcp, Bearer Token) with the "MCP connection successful" message. Token value masked. -->
![OPAF Add MCP server for oas001-mcp](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/05-opaf-add-mcp-server.png)

The URL must end with `/mcp`. With a wrong path, OPAF can still report a successful connection but discover zero tools.

### The agent flow

In Agent Builder I create a Custom Flow with two nodes:

1. An **MCP server** node with server `oas001-mcp`, timeout `120` and **Allowed tools** left empty, which means all four tools. The dropdown lists `describe_subject_area`, `execute_logical_sql`, `get_server_info` and `list_subject_areas`.
2. An **Agent** node. The **Tools** output of the MCP server node connects to it.

<!-- IMAGE: MCP server node configuration with the Allowed tools dropdown open, showing the four tools. -->
![OPAF MCP server node listing the four OAS tools](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/06-opaf-mcp-tools.png)

<!-- IMAGE: Custom Flow canvas: MCP server node (oas001-mcp) Tools output connected to the Agent node. -->
![OPAF Custom Flow with the OAS MCP server and an Agent node](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/07-opaf-flow-canvas.png)

The agent instructions:

> You answer questions about sales data in Oracle Analytics Server. Always call
> list_subject_areas and describe_subject_area first to learn exact table and column names,
> then use execute_logical_sql. Never invent column names.
> Always answer in natural language. Present data as a markdown table with clear column
> headings, sorted in a meaningful order (e.g. highest value first). Add a one-sentence
> summary of the key finding. Never return raw JSON.

The first paragraph sets the order of tool calls. The second one is about the answer format: without it, the first answer in a new chat may come back as raw JSON from the tool.

## Testing the agent

I test with two questions:

- *What subject areas are available for sales data?*
- *What is the revenue by region? Which region is the highest?*

For the second question the agent goes through the whole sequence: it finds the subject area, reads its tables and columns, writes Logical SQL and presents the result as a sorted table with a one-sentence summary.

<!-- IMAGE: OPAF chat with both test questions and answers (subject area list; revenue by region table with the summary sentence). Expanded tool calls are a bonus if they show the generated Logical SQL. -->
![OPAF agent answering questions from OAS](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/08-opaf-chat.png)

The service log on `oas001` shows every Logical SQL statement the agent sends, which is the easiest way to see what the agent actually asked OAS:

```bash
journalctl -u oas-mcp -f
```

<!-- IMAGE: journalctl -u oas-mcp output with the "Logical SQL (max N rows): SELECT ..." lines generated by the OPAF agent. -->
![Logical SQL generated by the OPAF agent in the oas-mcp log](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/09-journalctl-logical-sql.png)

## Operations

A few things to know when the server runs for longer than a demo:

- **After a reboot** both OAS (`oas-full-stack.service`) and the MCP server start automatically. The MCP server is up within seconds, OAS needs 3 to 4 minutes. Agent requests in that window fail and work again once OAS is up.
- **Status:** `systemctl is-active oas-full-stack oas-mcp` and `curl http://localhost:8000/health`.
- **New code version:** copy `server.py` and `oas_client.py` to `/opt/oas-mcp-server/` and run `sudo systemctl restart oas-mcp`.
- **Key rotation:** generate a new key, replace `MCP_API_KEY` in `.env`, restart the service and update the Bearer token of `oas001-mcp` in OPAF:

```bash
cd /opt/oas-mcp-server
NEW=$(venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))")
sed -i "s/^MCP_API_KEY=.*/MCP_API_KEY=$NEW/" .env
sudo systemctl restart oas-mcp
echo $NEW
```

## Troubleshooting

<div class="zv-table-compact" markdown="1">

| Symptom | Check / fix |
|---|---|
| `/health` does not respond | `systemctl status oas-mcp`, `journalctl -u oas-mcp -n 50` |
| Service exits with status 3 | Port 8000 in use: stop any manually started `python server.py` |
| Tools return "Oracle Analytics error" | OAS down or still starting: `systemctl status oas-full-stack`; test with `venv/bin/python test_oas.py` |
| `Authentication failed` from OAS | `OAS_USER` / `OAS_PASSWORD` in `.env` |
| `/mcp` returns 401 | Wrong or missing Bearer token |
| OPAF: "MCP server URL must use https" | Proxy Settings → Allow Insecure Http Urls = Yes |
| OPAF: "resolves to a private or non-routable network address" | Proxy Settings → Block Private Outbound Urls = No |
| OPAF: "Could not connect to the remote MCP server" | From the OPAF VM: `curl -m 5 http://10.0.1.205:8000/health`; a timeout means NSG or firewall |
| OPAF shows connected but 0 tools | Wrong URL path: it must end with `/mcp` |
| Logical SQL error | Column names must match `describe_subject_area` exactly (`"Table"."Column"`) |

</div>

## From proof of concept to customer deployment

The server works as a proof of concept. Before using it with a customer's OAS, I would change three things:

- **A dedicated read-only OAS user** instead of `admin`. The agent then sees only the subject areas and data that user is allowed to see, enforced by OAS security.
- **HTTPS with a CA-signed certificate**, so Allow Insecure Http Urls can be switched back to No.
- **Block Private Outbound Urls = No stays.** An on-premises OAS is always on a private address from OPAF's point of view, so this setting is a requirement for this pattern, not a shortcut.

The pattern itself carries over unchanged: a thin MCP layer that exposes the semantic model, not the database. The agent asks questions in business terms, and OAS keeps doing what it has always done: joins, aggregations, calculations and security.

If you work with Oracle Analytics Cloud or Autonomous Database instead, both have built-in MCP servers. I used the Autonomous Database one with OPAF in [Chapter 6](https://zigavaupot.blogspot.com/2026/10/chapter-6-adb-built-in-mcp-server.html) and [Chapter 7](https://zigavaupot.blogspot.com/2026/10/chapter-7-opaf-agents-over-mcp.html) of [Select AI Agent meets OPAF](https://zigavaupot.blogspot.com/2026/10/introduction-to-select-ai-agent-meets.html).
