# Select AI Agent meets OPAF Series

![Select AI Agent meets OPAF blog series](https://zigavaupot.github.io/blogger/opaf-and-select-ai/images/select-ai-opaf-blog-series.png)

This is the overview of my Select AI Agent meets OPAF series. It answers one question: how do Select AI Agent in Autonomous Database 26ai and Oracle Private Agent Factory (OPAF) fit together? I take one sales analyst over my OA Bootcamp sales schema (`OABOOTCAMP`) and build it six ways in OPAF — plain Select AI, the in-database agent team called natively, the same team built visually without PL/SQL, two flows through the Autonomous Database built-in MCP server, and a native routing flow. Every flow returns the same numbers, because the business definitions live in the database, not in the agent.

When I started, I only wanted to try out how Select AI Agent works with OPAF. It turned into quite an exploratory journey: each experiment opened another way to connect the two, and I ended up with six scenarios. I doubt these are all — there are most likely alternatives I haven't explored yet.

## What the series covers

- **Preparing the data:** validating joins, collecting exact literals, business rules and table and column comments as the semantic layer.
- **Connecting to the LLM:** IAM, resource principal and the Select AI profile on OCI Generative AI.
- **Select AI Agent:** tool, agent, task and team in PL/SQL, verified against hand-written SQL.
- **Native OPAF nodes:** the Select AI and In-Database Team nodes, and the same team built on the canvas with no PL/SQL.
- **MCP:** the Autonomous Database built-in MCP server and two OPAF flows on top of it.
- **Routing:** one OPAF agent choosing between fast NL2SQL and the in-database team with Select AI Bridge.

## Architecture: one database, six front ends

In all six flows, natural language is turned into SQL inside the database by Select AI. OPAF is always the front end. What changes from flow to flow is how OPAF reaches the database and who plans the analysis.

<div class="zv-table-compact" markdown="1">

| Flow | OPAF building blocks | How OPAF reaches the database | Who plans the analysis |
|---|---|---|---|
| C1 | Select AI node | Database connection (wallet) | Nobody — one question, one SQL statement |
| C2 | In-Database Team node, existing team | Database connection (wallet) | Select AI Agent in ADB |
| C3 | In-Database Tool, Task, Agent and Team nodes, created on the canvas | Database connection (wallet) | Select AI Agent in ADB |
| A | Agent node + MCP server node (`SALES_NL2SQL`) | ADB built-in MCP server | OPAF agent |
| B | Agent node + MCP server node (`ASK_SALES_ANALYST`) | ADB built-in MCP server | Select AI Agent in ADB |
| D | Agent node + two Select AI Bridges (Run SQL, Team) | Database connection (wallet) | OPAF agent routes; the in-database team plans analytical questions |

</div>

My environment:

- Autonomous AI Database (ADW) 26ai, version `23.26.4.1.0`, public endpoint ("Allow secure access from everywhere") with mTLS required for SQL*Net connections
- OCI Generative AI in Germany Central (Frankfurt), model `openai.gpt-oss-120b` — used both by the Select AI profile in the database and by the Agent nodes in OPAF
- OPAF 26.7 on OCI, in a private subnet

## Posts in the series

1. [Part 1: Making a star schema Select AI-ready](PART1-URL) — join validation, exact literals, business rules and comments as the semantic layer.
2. [Part 2: Connecting Autonomous Database to OCI Generative AI](PART2-URL) — dynamic group, policy, resource principal, the Select AI profile and smoke tests.
3. [Part 3: Building a Select AI Agent team in PL/SQL](PART3-URL) — tool, agent, task and team, checked against ground truth.
4. [Part 4: Select AI and the in-database team as native OPAF nodes](PART4-URL) — flows C1 and C2.
5. [Part 5: No-code Select AI Agent](PART5-URL) — flow C3.
6. [Part 6: The Autonomous Database built-in MCP server](PART6-URL) — enabling it with a tag, testing with curl, wrapping the team as a tool.
7. [Part 7: OPAF over MCP — database orchestrates vs OPAF orchestrates](PART7-URL) — flows B and A.
8. [Part 8: Native routing with Select AI Bridge](PART8-URL) — flow D.

## All six flows compared

In the table, *DB* means a database connection with the wallet, and *ADB team* means the Select AI Agent team running in the database.

<div class="zv-table-compact" markdown="1">

| | C1 | C2 | C3 | A | B | D |
|---|---|---|---|---|---|---|
| Connection | DB | DB | DB | MCP | MCP | DB |
| LLM in OPAF | none | none | none | plans, calls tools | routes only | routes between bridges |
| Planning | none (one SQL) | ADB team | ADB team | OPAF agent | ADB team | ADB team for analytical questions |
| Multi-step | partial (winner only) | full | full | full | full | full |
| Exact numbers | rounded (Narrate) | yes | yes | yes | yes | yes (team rounds to whole dollars) |
| Shows SQL | yes (Show SQL) | no | no | yes (`showsql`) | no | no (declines) |
| Guardrail | `enforce_object_list` (raw ORA error) | agent role | agent role | OPAF scope rule | OPAF scope rule | OPAF scope rule |
| Typical time | 4–9 s | 9–19 s | 11–18 s | 12–20 s | 23–25 s | 7–19 s |

</div>

All flows that answer return the same numbers: the business definitions live in the database, so every path — native node, MCP or routing — gets the same semantics.

## Key takeaways

- Most of the effort is in the data: a schema with no constraints and no comments gives Select AI nothing to work with.
- Rules in comments and role text are guidance, not enforcement. Stating them positively, `temperature` 0 and one grouped query made the agent repeatable; I check agent answers against hand-written SQL before every demo.
- The native Select AI nodes are the fastest way to run a database agent from OPAF; MCP opens the same agent to any MCP client.
- In OPAF agent instructions, the scope rule goes first.
- An OPAF agent that cannot get SQL from a tool may invent a plausible query, so I give it an explicit rule to decline instead.
