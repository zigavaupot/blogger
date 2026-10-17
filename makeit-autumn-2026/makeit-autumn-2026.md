# No slides, just agents: Oracle Private Agent Factory at MakeIT 2026

![No slides, just agents: building an AI agent with Oracle Private Agent Factory, MakeIT, Ljubljana, 13 October 2026](https://zigavaupot.github.io/blogger/makeit-autumn-2026/images/makeit-autumn-2026.png)

On 13 October 2026 I presented at the MakeIT conference in Ljubljana. The session was called **No slides, just agents** (in Slovenian: *Sestavimo agenta AI z Oracle Private Agent Factory*), and the title was meant literally: a few slides to set the scene, then live agents built and run in Oracle Private Agent Factory (OPAF).

In this post I summarise what I showed: what OPAF is, where to get it, and five demos, from the pre-built Knowledge Agent through Select AI RAG and six Select AI Agent scenarios to the OAS MCP server. The slides are available for download at the end.

## What is Oracle Private Agent Factory?

I described OPAF with three words:

- **No-code.** OPAF is a no-code platform for building, testing, managing and running AI agents.
- **Free.** It is a free extension of the Oracle Database, which is the foundation of the solution. It does require Oracle AI Database 26ai (for example, for Vector Search).
- **Open / air-gapped.** Because of its container-based architecture OPAF is portable. It can run in the cloud (for example, on OCI) or completely locally, inside your own isolated (air-gapped) network.

## Where to get it

There are two options:

- <a href="https://marketplace.oracle.com/app/agentfactory" target="_blank" rel="noopener">Oracle Marketplace</a>, a one-click installation in OCI.
- <a href="https://www.oracle.com/database/technologies/private-agent-factory-downloads.html" target="_blank" rel="noopener">Oracle Software Delivery Cloud</a>, for a local installation.

## The demos

![Demos in the session: Prebuilt Knowledge Agent, Custom Flow: Select AI RAG, Custom Flow: Select AI Agent (several scenarios), OAS MCP Server and a complex custom flow example](https://zigavaupot.github.io/blogger/makeit-autumn-2026/images/opaf-scenarios.png)

The rest of the session was live:

1. Pre-built Knowledge Agent
2. Custom flow: Select AI RAG
3. Custom flow: Select AI Agent (several scenarios)
4. OAS MCP Server
5. Complex custom flow example

### RAG agents in OPAF

For the RAG part I used a well-known Slovenian children's book about Piki Jakob, the teddy bear, and asked four test questions:

- How many penalty points did Piki Jakob collect on his driving test?
- What role does the family cat play in the book? List all the stories it appears in and what happens.
- When does Piki Jakob take words or instructions literally? What comes of it?
- Write Piki Jakob's CV: all the roles he takes on throughout the book and how each one ends.

I compared four approaches:

| Approach | Cat | Literally | CV | Time |
|---|---|---|---|---|
| Knowledge Agent | 3/8 | 0/3 | 5/15 | ~10 s |
| Deep Data Research Agent | 6/8 | 2/3 | 8–10/15 | ~3 min |
| Flow: Agent + DDRA | ~2/8 | 2/3 | 5/15 | 20–40 s |
| Select AI RAG in OPAF | 8/8 | 3/3 | 15/15 | 12–40 s |

The pre-built Knowledge Agent is the fastest to set up and to answer, but it missed most of what the questions asked for. Select AI RAG, used in an OPAF custom flow, answered all three questions completely.

### Select AI Agents: six scenarios

The second part used the same four test questions on a sales star schema in Autonomous Database:

- Which sales channel had the highest profit in 2025?
- Show me the SQL for profit by channel in 2025.
- Compare profit in 2025 vs 2024 by sales channel and tell me which channel improved the most.
- What is the capital of France?

The last question is the guardrail test. I ran the questions through six flows:

| Flow | OPAF building blocks | How OPAF reaches the database | Who plans the analysis |
|---|---|---|---|
| C1 | Select AI node | Database connection (wallet) | Nobody (one question, one SQL statement) |
| C2 | In-Database Team node, existing team | Database connection (wallet) | Select AI Agent in ADB |
| C3 | In-Database Tool, Task, Agent and Team nodes, created on the canvas | Database connection (wallet) | Select AI Agent in ADB |
| A | Agent node + MCP server node (`SALES_NL2SQL`) | ADB built-in MCP server | OPAF agent |
| B | Agent node + MCP server node (`ASK_SALES_ANALYST`) | ADB built-in MCP server | Select AI Agent in ADB |
| D | Agent node + two Select AI Bridges (Run SQL, Team) | Database connection (wallet) | OPAF agent routes; the in-database team plans analytical questions |

And the results:

| | C1 | C2 | C3 | A | B | D |
|---|---|---|---|---|---|---|
| Connection | DB | DB | DB | MCP | MCP | DB |
| LLM in OPAF | none | none | none | plans, calls tools | routes only | routes between bridges |
| Planning | none (one SQL) | ADB team | ADB team | OPAF agent | ADB team | ADB team for analytical questions |
| Multi-step | partial (winner only) | full | full | full | full | full |
| Exact numbers | rounded (Narrate) | yes | yes | yes | yes | yes (team rounds to whole dollars) |
| Shows SQL | yes (Show SQL) | no | no | yes (`showsql`) | no | no (declines) |
| Guardrail | `enforce_object_list` (raw ORA error) | agent role | agent role | OPAF scope rule | OPAF scope rule | OPAF scope rule |

Each scenario is described step by step in the blog series <a href="https://zigavaupot.blogspot.com/2026/10/introduction-to-select-ai-agent-meets.html" target="_blank" rel="noopener">Select AI Agent meets OPAF</a>.

### OPAF and the OAS MCP server

The last integration demo connected an OPAF agent to Oracle Analytics Server through a custom MCP server, so the agent queries subject areas with Logical SQL and uses the semantic model instead of raw tables. The full setup is in <a href="https://zigavaupot.blogspot.com/2026/10/oas-mcp-server-and-opaf.html" target="_blank" rel="noopener">Oracle Analytics Server MCP & Use cases</a>.

## Slides

Download the slides (in Slovenian) <a href="https://zigavaupot.github.io/blogger/makeit-autumn-2026/files/ZigaVaupot%20-%20OPAF.pptx" target="_blank" rel="noopener">here</a>.
