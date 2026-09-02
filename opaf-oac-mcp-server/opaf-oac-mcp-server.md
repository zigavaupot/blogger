![OPAF and OAC via MCP](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/opaf-oac.png)

### From Standalone Assistant to Analytics-Aware Agent

I've covered this ground before in two earlier post series:

- [Unlocking Oracle Analytics Cloud with AI: MCP for Oracle Analytics](https://zigavaupot.blogspot.com/2025/12/unlocking-oracle-analytics-cloud-with-ai.html), where I introduced the **MCP Server for Oracle Analytics Cloud** and how it lets general-purpose AI assistants like Claude query governed OAC data through a standard, secure protocol
- [Oracle Analytics Meet AI series](https://zigavaupot.blogspot.com/2026/07/oracle-analytics-meet-ai-series.html), which expands on that theme focusing more on tools from within OAC itself.

This time, I want to close the loop on a question I left open: what happens when the AI assistant *is not* a desktop client like Claude Desktop, but a **private, self-hosted agent platform** running entirely inside your own environment?

That's exactly the space **Oracle AI Database Private Agent Factory (OPAF)** occupies — Oracle's private agent platform, deployed and backed by your own database, whether that's air-gapped on-premises or running in a cloud tenancy you control. Either way, the agent, the data, and the identity boundary stay yours. This post covers how to connect OPAF's chat interface to Oracle Analytics Cloud using the same MCP Server introduced last time.

### Why OPAF + OAC via MCP?

OPAF already gives you a private, governed chat agent with its own LLM connections, its own identity domain, and its own data behind it. What it doesn't give you out of the box is a way to reason over **existing OAC subject areas** — the models, hierarchies, and metrics your BI team has already built and governed.

Rather than duplicating that modeling effort inside OPAF, the MCP Server lets OPAF's agent call out to OAC directly:

- No data duplication — queries run live against governed OAC subject areas
- No re-modeling — OPAF reuses the same dimensions, measures, and joins your analysts already trust
- One more MCP client — the same OAC MCP Server that works with Claude Desktop or Cline now also works with a private, internally-hosted agent, regardless of where that agent is deployed

### Architecture Overview

![Architecture diagram](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/opaf-oac-mcp-architecture.png)

The integration sits on top of two separately governed boundaries, connected by a single MCP tool call:

- **Your environment** (dashed boundary) hosts OPAF itself — the chat interface and the agent's tool management — whether that's air-gapped on-premises or a cloud tenancy you control. Nothing about this integration changes where OPAF runs or how it's secured.
- **Oracle Analytics Cloud** (solid boundary) stays exactly as your BI team built it. The OAC MCP Server sits at its edge and exposes governed subject areas to external callers without exposing the underlying data model.
- The **MCP tool call** in the middle is the only thing crossing that boundary. When OPAF's agent decides a question needs analytics data, it calls the MCP server, which translates the request into governed Logical SQL and returns results — no data copied, no schema duplicated on the OPAF side.

At a high level:

- **OPAF Chat** (user-facing) → **OPAF Agent / Model Management** → **MCP tool call** → **OAC MCP Server** → **OAC Subject Area** → **Logical SQL execution**
- No changes required to existing infrastructure or workloads — the MCP connector is additive, not invasive, whether OPAF sits behind a corporate proxy on-premises or a load balancer in the cloud

### Prerequisites

- A running OPAF deployment with Model/Tool Management available (this post assumes OPAF 26.7)
- An Oracle Analytics Cloud instance with subject areas already modeled and governed
- A network path from OPAF's host environment to your OAC instance — reachable directly, via proxy, or through whatever egress your environment requires
- MCP server and connection definitions downloaded from your OAC profile (see previous post)

### Setting it up: Create the integrated application

In your OCI IAM Identity Domain console, go to **Applications → Integrated applications → Add application**, and choose **Confidential Application** as the type — this is what lets the application securely hold a client secret, as opposed to a public/native client that can't.

Give it a descriptive name, e.g. `opaf-oac-mcp-client`. This is just a label used in the console and audit logs — it doesn't need to match any hostname or endpoint.

Once created, the application starts in a **Configuration required** or **Inactive** state until you complete the OAuth configuration in the next step.

### Setting it up: Configure the OAuth client

Open the new application and go to **OAuth configuration → Client configuration**, then select **Configure this application as a client now**.

Under **Allowed grant types**, enable:
- **Authorization code** — required for the interactive OAuth flow OPAF uses
- **Refresh token** — so OPAF doesn't need to re-prompt for consent on every call

**Client credentials** is optional here — only enable it if you also want a separate machine-to-machine path independent of the interactive flow.

Under **Redirect URL**, add the callback URL OPAF generated when you selected OAuth + Authorization code in the "Add MCP server" form (see below). If you're not certain which exact path variant OPAF's frontend uses, it's worth adding it in a couple of plausible forms — a mismatched redirect URL is the most common cause of a failed OAuth handshake.

Set **Client type** to **Confidential** — not Trusted, since you're not using self-signed client assertions.

### Setting it up: Scope the client to your OAC instance

Still in **OAuth configuration**, expand **Client configuration → Token issuance policy**.

Toggle **Add resources** on, then under **Authorized resources** choose **Specific** rather than **All** — this restricts the client to only the Oracle Analytics Cloud instance you explicitly grant it, instead of every resource registered in the domain.

Under **Resources**, search for and select your OAC instance, then add its scope. This is the step that actually ties the OAuth client to *your* OAC environment — everything up to now has just been generic OAuth plumbing.

If you don't want end users to see an OAuth consent screen the first time OPAF calls OAC, you can also enable **Bypass consent** here. For a controlled internal deployment this is usually fine; if your OPAF instance serves a broader or less trusted user base, you may prefer to leave consent enabled so each user explicitly approves the connection once.

### Setting it up: Collect the client credentials

Once submitted, copy the **Client ID** from the application's Details tab, and generate/copy the **Client secret**. These two values go directly into the **OAuth client ID** and **OAuth client secret** fields on OPAF's "Add MCP server" form.

Treat the client secret like any other credential — don't commit it to source control or paste it into shared docs, and rotate it if it's ever exposed.

### Add the MCP server in OPAF

Back in OPAF, open **Model/Tool Management → Add MCP server**. This form does double duty — you'll touch it once early on to generate the redirect callback URL for the identity domain setup above, and once more at the end to finish the connection.

**Server details**

- **Server name** — a short identifier, e.g. `oac-mcp-connect`
- **Server URL** — the endpoint of your OAC MCP Server

**Authentication mode**

Select **OAuth**, then under **OAuth grant type** select **Authorization code**. This is what triggers OPAF to display the **Redirect callback URL** box — copy that value now if you haven't already added it to the integrated application's redirect URLs in the identity domain step above.

**OAuth client details**

- **OAuth client ID** and **OAuth client secret** — paste the values you copied from the integrated application's Details tab
- **Authorization URL** and **Token URL** — your identity domain's `/oauth/authorize` and `/oauth/token` endpoints
- **Refresh URL** — optional; leave blank unless your identity domain exposes a separate refresh endpoint
- **Scopes** — the OAC resource scope you added when scoping the client to your OAC instance

**Test and save**

Click **Test connection** before **Add MCP server**. This runs the actual OAuth handshake — including the redirect through your identity domain — rather than just validating that the form fields are filled in. If it fails, the most common cause is a redirect URL that doesn't exactly match what's registered on the integrated application.

![Adding the MCP server in OPAF, with a successful test connection](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/add-mcp-server.png)

**Complete the authorization**

Saving the MCP server doesn't finish the OAuth handshake on its own — OPAF prompts for one more step: **Authorize MCP Server access**. This is the actual "Request authorization using the OAuth configuration already saved in this MCP source" step, and it's where the identity discussed in the Gotchas and Known Limitation sections below gets fixed in place — whoever clicks **Request Authorisation** here is the identity every future chat session will use to call OAC.

![Authorize MCP Server access dialog](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/authorize-mcp-server-access.png)

Clicking through opens your identity domain's login/consent page in a new window. Once you authorize, you'll see a simple confirmation and can close the window:

![Authorization complete confirmation](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/authorization-complete.png)

With that, the MCP server is fully connected and ready to use in Agent Builder.

### Wire it up in Agent Builder

With the MCP server registered, Agent Builder is where it actually becomes part of a working agent. The canvas is a simple five-node flow: **MCP server → Agent → Type Convert → Chat output**, fed by a **Chat input** node.

![Agent Builder flow connecting OAC via MCP](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/opaf-agent-builder-flow.png)

**MCP server node**

- **MCP server** — select the OAC MCP server you registered in the previous step
- **Timeout (seconds)** — how long to wait on a tool call before giving up; 45 seconds is a reasonable starting point for Logical SQL queries that may take a moment to execute
- **Allowed tools** — defaults to all tools the MCP server exposes, but it's worth narrowing this to just the ones the agent actually needs (e.g. discover, describe, and execute) rather than leaving every available tool on the table
- Its **Tools** output connects into the **Agent** node's **Tools** input

**Agent node**

- **Select LLM to use** — any model you have configured in OPAF works here; there's nothing OAC-specific about the model choice
- **Tools** — receives the MCP server's tool set from the connection above
- **Custom instructions** — this is where you tell the model what it's actually for, e.g. something like: *"You are an analytics assistant with direct access to Oracle Analytics Cloud through MCP tools. Answer questions about the organization's data using live queries — never guess or fabricate numbers."* Being explicit that answers must come from real tool calls, not the model's own assumptions, matters more here than in a general-purpose chat agent
- **Agent description** — a short label for the agent itself
- **Prompt** — receives the incoming user message; this is fed by the **Chat input** node's **Message** output
- **Temperature** — kept low-to-moderate for an analytics assistant, since you want consistent, grounded answers rather than creative variation
- Its **Message** output — the agent's response text — feeds into the next node

**Type Convert node**

The agent's raw output needs to be coerced into the right shape before it can be sent back to the user. This node converts between **Message** (string), **JSON**, and **DataFrame** representations; here only the **Message** branch is used, feeding straight into chat output.

**Chat output node**

Takes the converted **Message** and sends it back to the user in the OPAF chat interface — closing the loop from question to grounded, OAC-backed answer.

### Test it!

The OAC MCP Server exposes more tools than any single agent typically needs — things like content summarization, dashboard/report discovery beyond raw catalog search, and other OAC-specific helpers. For an analytics-answering agent, three are enough to cover the whole discover-describe-query cycle:

![Agent Builder MCP Server step](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/available-mcp-server-tools.png)

**`oracle_analytics-search_catalog`** — searches the OAC catalog to discover available datasets, subject areas, and other analytics content the agent can query

![Chat dialog: Discover](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/chat-dialog-1.png)

**`oracle_analytics-describe_data`** — retrieves column-level metadata for a given dataset or subject area — dimensions, measures, hierarchies, and joins

![Chat dialog: Describe](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/chat-dialog-2.png)

**`oracle_analytics-execute_logical_sql`** — runs a governed SQL query against OAC and returns the result set

![Chat dialog: Execute SQL](https://zigavaupot.github.io/blogger/opaf-oac-mcp-server/images/chat-dialog-3.png)

### Closing Thoughts

None of this required touching OAC's data model, duplicating a single subject area, or building a custom connector from scratch. The heavy lifting — discovering metadata, generating Logical SQL, executing it against governed data — is handled entirely by the OAC MCP Server. What OPAF adds on top is everything specific to running that inside your own environment: its own identity domain fronting the OAuth handshake, its own Agent Builder canvas for wiring the MCP tools into a working assistant, and its own chat interface for the people actually asking the questions.

The parts most likely to trip someone up aren't conceptual — they're the fiddly OAuth mechanics: getting the redirect URL to match exactly between OPAF's generated callback and the identity domain's registered client, and scoping the OAuth client to the right OAC resource rather than leaving it open to the whole domain. Once that handshake succeeds once, the rest — registering tools, wiring the Agent Builder flow, asking questions in chat — is comparatively straightforward, as the walkthrough above shows end to end.

### At the very end, some gotchas & heads-up notes

A few things worth knowing before you start, rather than discovering them mid-setup:

- **The redirect URL is a bit of a chicken-and-egg problem.** OPAF displays the callback URL after you select OAuth in the "Add MCP server" form — but that exact URL needs to be registered on the identity domain's confidential application before the authorization flow will succeed. Expect to move between the two screens once during setup. And "exact" really does mean exact: protocol, hostname, port, and path all need to match. Register the URL OPAF actually shows you, rather than pre-registering several guesses — the extra entries just broaden the OAuth configuration unnecessarily.
- **The OAC identity isn't necessarily the person chatting with the agent.** With the OAuth Authorization Code flow, OAC MCP tools run with the permissions of *whoever performs the authorization step* when the MCP source is set up — OPAF stores that resulting token against the MCP source itself. In practice, that means every chat session using this agent queries OAC as that one authorized identity, not as whoever happens to be logged into OPAF at the time. If your OAC security model relies on per-user permissions or row-level data security, this matters — see the section below on what true per-user propagation would actually require.
- **Scope the OAuth client — don't leave it open.** Setting Authorized resources to *Specific* and explicitly adding the intended OAC resource follows least-privilege. *All* allows the client to request access to any resource within the identity domain, which is far broader than this integration needs.
- **Narrow the Allowed tools list — and treat it as a security boundary, not just a UX nicety.** The OAC MCP Server exposes considerably more than a basic query loop: catalog search, datasource discovery, semantic-model metadata inspection, Logical SQL execution, and catalog-management/export operations are all on the table. For a read-only "talk to your data" agent, deliberately restrict Allowed tools to the discovery-and-query subset (search, describe, execute) and leave the rest unselected — that's what actually keeps the agent from touching things it was never meant to.
- **Be explicit in the agent's instructions about not guessing.** Tell the agent to discover and describe the relevant OAC data source before constructing Logical SQL, execute the query through MCP, and base numerical answers only on returned results — and to say so plainly if it can't retrieve the data, rather than filling the gap with a plausible-sounding number.

A couple of additional things worth knowing:

- **Network connectivity is from OPAF, not your laptop.** MCP requests originate from the Agent Factory application container itself, so the OAC MCP endpoint needs to be reachable from *that* environment — not just from wherever you're testing the connection from your browser. This matters most with private-subnet deployments, restrictive egress rules, or proxies in the path.
- **Timeout behavior is documented, but streaming isn't well-trodden.** OPAF's own troubleshooting docs cover tool-call timeouts (the node's timeout expires, or the MCP server is slow/unreachable) and recommend raising the timeout only after confirming the MCP server actually received the request. What's less established is how that interacts with a Logical SQL call that streams back a large result set — worth a deliberate test with a genuinely long-running query.
- **Expect some version-specific behavior.** The OAC MCP Server is currently documented as Preview, and both OPAF's MCP support and Oracle's MCP implementations are moving quickly. Anything version-specific here is worth re-checking against current docs before you rely on it.

### Known Limitation: One Shared OAC Identity, Not Per-User

It's worth being upfront about a limitation rather than glossing over it: even though OPAF and OAC can sit behind the same SSO identity domain, that doesn't mean OAC sees *who's actually chatting* in OPAF.

OPAF SSO and MCP source authorization are two separate events. SSO authenticates a person into the OPAF chat interface. MCP authorization is a one-time step performed when the MCP source is configured — whoever completes that authorization grants their OAC token, and OPAF stores it against the MCP source itself, not against individual chat sessions. Every subsequent query, from every OPAF user, runs against OAC as that one authorized identity.

For a proof-of-concept, or an internal tool where everyone using the agent is meant to see the same governed subject areas, that's a reasonable trade-off — it's simple, and it works. But if your OAC security model relies on row-level security or per-user catalog permissions, treat this integration as **one shared analytical identity**, not as each user's own OAC access.

Closing that gap would require a delegation / token-exchange layer: OPAF would need to hand the authenticated chat user's identity to something capable of exchanging it for an OAC-scoped access token on each call, so OAC could enforce that specific user's roles and row-level security rather than the stored source identity's. That's a well-understood "on-behalf-of" pattern in enterprise identity architecture generally, but as of OPAF 26.7, OPAF doesn't document exposing the authenticated user's identity to an MCP tool invocation — so there's currently no hook for a proxy or intermediary to build that exchange on top of.

I checked whether any of OPAF's other three authentication modes get around this, and none do — they all reduce to the same shape, one configured identity shared by every chat user:

- **Direct / no auth** — no credential at all beyond network trust; same access for everyone
- **Bearer token** — a single static token, configured once
- **Client credentials** — an OAuth flow authenticating the *application itself*, with no human user involved at any point, not even at setup
- **Auth Request** — despite the name, this isn't per-request user authorization. It's a service-account credential pair (token endpoint URL, username, password) that Agent Factory exchanges for a bearer token behind the scenes — same static-identity pattern, just a different exchange mechanism than OAuth

Every mode OPAF currently offers for an MCP server results in one identity, configured once, reused for every chat user. None of them carry the individual OPAF chat user's identity through to the downstream MCP server.

This feels like a natural direction for OPAF's MCP support to grow into, given how much of the groundwork — a shared identity domain, SSO on both sides — is already in place. Until then, choose deliberately who performs the MCP source authorization, since that person's OAC permissions effectively become the permissions the whole integration runs with.

---

*Related: [Unlocking Oracle Analytics Cloud with AI: MCP for Oracle Analytics](https://zigavaupot.blogspot.com/2025/12/unlocking-oracle-analytics-cloud-with-ai.html) · [Oracle Analytics Meet AI series](https://zigavaupot.blogspot.com/2026/07/oracle-analytics-meet-ai-series.html)*
