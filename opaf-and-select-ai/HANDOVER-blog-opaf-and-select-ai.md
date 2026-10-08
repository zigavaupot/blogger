# Handover: blog post "OPAF + Select AI Agent"

Author: Žiga Vaupot (zigavaupot.blogspot.com)
Purpose of this session: write the blog post from the finished runbook and save it into the working folder.

---

## 1. Files and folders

| What | Path |
|---|---|
| Working folder | `Github/Blogger/opaf-and-select-ai/` |
| Screenshots | `Github/Blogger/opaf-and-select-ai/images/` |
| Source content (authoritative) | `Github/Blogger/opaf-and-select-ai/opaf-and-select-ai-runbook.md` |
| HTML generation rules (mandatory) | `/BLOGGER/blogger/prompt/blogger-html-generation-instructions.md` |
| Blog stylesheet (reference only, never embed) | `/BLOGGER/blogger/blogger-post-new.css` |

**Read the runbook and both `/BLOGGER/...` files before writing anything.**

Deliverables to write into the working folder:

1. `opaf-and-select-ai.md` — the blog post in Markdown (source of truth for the HTML)
2. `opaf-and-select-ai.html` — Blogger-ready HTML generated from the Markdown, following `blogger-html-generation-instructions.md` exactly

---

## 2. Workflow

1. Read the runbook (sections 0–14 + Lessons learned).
2. Draft `opaf-and-select-ai.md` **section by section**, showing each section for review before moving on (the author prefers iterative drafting over one big rewrite).
3. When the Markdown is approved, generate `opaf-and-select-ai.html` from it.
4. Run the validation checklist from section 21 of the HTML instructions before saving.

---

## 3. Writing rules

- First person singular: "I", never "we".
- Audience: Oracle practitioners (DBAs, analytics and AI developers). Technical, practical, no marketing tone.
- Avoid repetition — the author flags it. Say things once; refer back instead of restating.
- The runbook contains only working steps. Keep it that way: no trial-and-error narratives. Known limitations are stated as findings (e.g. "the Show SQL bridge did not return SQL in this OPAF release").
- Keep code exactly as in the runbook (SQL, PL/SQL, JSON, shell). Don't reformat.
- Mask secrets: no passwords, tokens. The ADW OCID and compartment OCID in the runbook are already written as `<adw-ocid>` / placeholders — keep it so.
- The full comment script and all instruction texts are long; include them where they teach something, otherwise show a representative excerpt and say the rest follows the same pattern.

## 4. HTML rules (summary — the instructions file is authoritative)

- Exactly one `<article class="zv-blog-post">` wrapper.
- Featured image → `<div class="post-intro">` (60–180 words) → `<!--more-->` → body starting at `<h2>`.
- No `<style>`, no inline `style="..."`, no `<h1>`, no html/head/body.
- Tables with `<thead>`/`<tbody>`; code as `<pre><code>` with `&`, `<`, `>` escaped.
- No Blogger labels in the HTML. Suggested labels for the author to set manually: `Posts, Hero, OPAF, Select AI, MCP, Autonomous Database`.
- Note: an older rule about inline styles and Oracle red `#cc0000` accents is **obsolete** — do not use it.

---

## 5. Agreed post structure (demo storyline)

Working title: **Select AI Agent meets Oracle Private Agent Factory: six ways to put an in-database agent in front of your data**

0. **Featured image + post-intro** — the question (how do Select AI Agent and OPAF fit together), the OABOOTCAMP sales schema, one sales analyst built six ways, same numbers everywhere.
1. **Architecture overview** — table of the six flows (C1, C2, C3, A, B, D): how OPAF reaches the database and who plans the analysis. Environment: ADW 26ai 23.26.4 (public endpoint, mTLS), OCI GenAI Frankfurt `openai.gpt-oss-120b`, OPAF 26.7 in a private subnet.
2. **Foundation** (runbook 1–8) — schema scoping and join validation, business rules, table/column comments (the semantic layer), IAM (dynamic group + policy, resource principal, ACL), Select AI profile with `temperature 0` and `enforce_object_list`, smoke tests incl. `SELECT AI` in notebook vs `DBMS_CLOUD_AI.GENERATE` in SQL Worksheet.
3. **Plain Select AI in OPAF — C1** (runbook 12a–12b) — DB connection with wallet, Select AI node with Narrate; fast but one SQL, rounded numbers, guardrail via `enforce_object_list`.
4. **Select AI Agent** — concepts first (profile, tool, agent, task, team, conversation; the "analytics department" analogy and the "where the rules live" table), then:
   - the team in PL/SQL (runbook 9) incl. ground-truth verification and making it repeatable,
   - C2: In-Database Team node (12c),
   - C3: the same team built visually on the canvas, no PL/SQL (14).
5. **MCP: the database agent for any client — Flows A and B** (runbook 10–11) — enabling the ADB MCP server with a tag, bearer token test with curl, wrapper tool for the team, custom NL2SQL tool (why: OPAF rejects null schema descriptions), OPAF registration with Auth Request, Flow B then Flow A, scope rule placement.
6. **Native routing — Flow D** (runbook 13) — Select AI Bridge (Run SQL + Team), routing instructions, "Answered with" line, why there is no Show SQL bridge.
7. **Comparison and lessons learned** — merge runbook 11d and 12d into one table covering all six flows (connection, LLM in OPAF, planning, multi-step, exact numbers, SQL visibility, guardrail, typical time); key takeaway: business definitions live in the database, so every path returns the same numbers; then the lessons learned list.

If the post becomes too long after section 4, ask the author whether to split it into Part 1 (foundation + native nodes) and Part 2 (MCP + routing + comparison).

---

## 6. Ground truth (for checking any numbers in the text)

Profit = REVENUE − COST_FIXED − COST_VARIABLE, all order statuses, by billing date:

| Channel | 2024 | 2025 | Δ |
|---|---:|---:|---:|
| Catalog | 699,472.58 | 1,360,396.31 | +660,923.73 |
| Online | 1,438,821.21 | 2,099,559.05 | +660,737.84 |
| Store | 2,223,219.07 | 3,498,467.01 | +1,275,247.94 |

Store has the highest 2025 profit and the largest improvement.

---

## 7. Images

The runbook references these placeholder files. The author's actual screenshots in `images/` may have different names — match them by content (look at the images), propose a mapping table to the author, and only rename files after approval.

| Placeholder | Content |
|---|---|
| 01-genai-playground-models.png | OCI GenAI Playground model list, Frankfurt |
| 02-dynamic-group.png | Dynamic group matching rules |
| 03-policy.png | Policy statements |
| 04-adw-network.png | ADW network settings (public endpoint, mTLS) |
| 05-adw-mcp-tag.png | `adb$feature` MCP tag on ADW |
| 06-mcp-curl.png | Terminal: MCP tools/list and tools/call |
| 07-opaf-add-mcp-server.png | OPAF Add MCP server (Auth Request) |
| 08-opaf-mcp-tools.png | MCP server node listing ASK_SALES_ANALYST / OABOOTCAMP_SALES_SQL |
| 09-opaf-flow-b-canvas.png | Flow B canvas |
| 10-opaf-flow-b-chat.png | Flow B chat tests |
| 11-opaf-flow-a-canvas.png | Flow A canvas |
| 12-opaf-flow-a-chat.png | Flow A chat tests |
| 13-opaf-select-ai-nodes.png | Select AI node palette in OPAF |
| 14-opaf-flow-c1-canvas.png | C1 canvas (Select AI node) |
| 15-opaf-flow-c1-chat.png | C1 chat tests |
| 16-opaf-flow-c2-canvas.png | C2 canvas (In-Database Team node) |
| 17-opaf-flow-c2-chat.png | C2 chat tests |
| 18-opaf-flow-d-canvas.png | Flow D canvas (two Select AI Bridges + Agent) |
| 19-opaf-flow-d-chat.png | Flow D chat tests |
| 20-opaf-flow-c3-canvas.png | C3 canvas (Tool → Task → Agent → Team, Create new) |
| 21-opaf-flow-c3-chat.png | C3 chat tests |

In the Markdown, reference images as `images/<file>.png`. In the HTML, keep the same relative `src` values unless the author supplies Blogger image URLs (he uploads images to Blogger himself and replaces the URLs). Pick one strong image as the featured image (suggestion: the Flow D or C3 canvas) — and don't repeat it later in the body.

---

## 8. Side note for the author

`blogger-post-new.css`, line 22, contains a stray fragment:
`--zv-bronze: #b4703c;zv-blog-post .zv-series-card`
It should be `--zv-bronze: #b4703c;` — the fragment likely invalidates `--zv-bronze-dim` on the next line (link colour and hover states).
