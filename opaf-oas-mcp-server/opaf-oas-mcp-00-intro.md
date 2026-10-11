# Oracle Analytics Server MCP & Use cases

<!-- IMAGE (featured, shared by all posts): architecture diagram. OPAF agent in subnet-opaf-private -> HTTP /mcp (Bearer token, NSG nsg-oas-mcp) -> oas-mcp Python service on oas001 -> SOAP /analytics-ws -> OAS bi_server1 :9502. -->
![Oracle Analytics Server MCP & Use cases: OPAF agent querying Oracle Analytics Server through a custom MCP server](https://zigavaupot.github.io/blogger/opaf-oas-mcp-server/images/oas-mcp-architecture.png)

Oracle Analytics Cloud has an MCP server built in. Oracle Analytics Server does not. Many customers run OAS on premises or on their own compute, and their semantic models hold years of curated business logic that AI agents should be able to use instead of rebuilding it from raw tables.

In three short posts I build a small MCP server for OAS in Python, run it as a service next to OAS on an OCI compute instance and connect AI agents to it, starting with Oracle Private Agent Factory (OPAF). The server exposes four read-only tools on top of the OAS SOAP web services, which have been part of the product since OBIEE.

## Why go through the semantic model

Working through the semantic layer has a practical benefit. The agent writes Logical SQL against subject areas, so joins, aggregation rules, calculated measures and data security defined in the OAS semantic model all apply. The agent never sees physical tables.

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

## Posts

1. [Setting up the OAS MCP server](https://zigavaupot.blogspot.com/2026/10/setting-up-oas-mcp-server.html): the code, installation as a systemd service, tests with `curl` and the network rules.
2. [Using the OAS MCP server in OPAF](https://zigavaupot.blogspot.com/2026/10/using-oas-mcp-server-in-opaf.html): proxy settings, registration, the agent flow and tests.
3. Using the OAS MCP server from Claude (coming soon).

## Useful links and documentation

- [Model Context Protocol](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Oracle AI Database Private Agent Factory documentation](https://docs.oracle.com/en/database/oracle/agent-factory)
- [Select AI Agent meets OPAF](https://zigavaupot.blogspot.com/2026/10/introduction-to-select-ai-agent-meets.html), where I used the Autonomous Database built-in MCP server with OPAF
