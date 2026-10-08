# Select AI Agent meets OPAF, Part 3: Building a Select AI Agent team in PL/SQL

![](FEATURED-IMAGE-URL)

A single `SELECT AI` call answers one question with one SQL statement. Ask it to compare profit between two years by channel and pick the winner, and it has no step in which to plan that. Select AI Agent adds exactly that step: an agent can break a question into tool calls, run them and combine the results — all inside the database.

In this part I build an in-database sales analyst with `DBMS_CLOUD_AI_AGENT` on top of the Select AI profile from Part 2: one SQL tool, one agent, one task and one team. I run it, check its numbers against hand-written SQL, and show what made its answers repeatable. This team is the one OPAF calls in the rest of the series.

## The building blocks

I think of Select AI Agent as a small analytics department:

- **Profile** — which LLM the department uses and which data it may see (Part 2).
- **Tool** — a skill, here NL2SQL over the sales tables through the profile.
- **Agent** — the analyst: a role and an LLM profile.
- **Task** — the assignment brief: what to accomplish, with a `{query}` placeholder for the user's question, and which tools are allowed.
- **Team** — the department that pairs agents with tasks and is what I actually run.
- **Conversation** — the case file that keeps context for one run.

Each piece carries different knowledge, so it helps to decide up front where each rule lives:

| What | Where it lives |
|---|---|
| Joins, metric definitions, allowed values, default order status rule | Table and column comments (Part 1) |
| LLM, allowed tables, temperature | Select AI profile (Part 2) |
| When to use NL2SQL | Tool instruction |
| Persona, data-only scope, business rules restated | Agent role |
| How to answer: one grouped query, only returned numbers, format | Task instruction |
| Which agent does which task, process | Team |

All blocks below run as `OABOOTCAMP`. I use `q'[...]'` quoting so single quotes inside instructions need no escaping.

## Tool

A built-in tool of type `SQL`, bound to the `OABOOTCAMP_AI` profile:

```sql
BEGIN
  DBMS_CLOUD_AI_AGENT.CREATE_TOOL(
    tool_name  => 'OABOOTCAMP_SALES_SQL',
    attributes => q'[{
      "tool_type": "SQL",
      "tool_params": {"profile_name": "OABOOTCAMP_AI"},
      "instruction": "Use this tool for any question about sales, revenue, profit, discounts, units, orders, customers, products, geography or time periods. Use runsql to answer questions with data, showsql when the user asks to see the query, and explainsql when the user asks how the query works."
    }]',
    description => 'NL2SQL over OABOOTCAMP sales star schema'
  );
END;
/
```

## Agent

```sql
BEGIN
  DBMS_CLOUD_AI_AGENT.CREATE_AGENT(
    agent_name => 'SALES_ANALYST_AGENT',
    attributes => q'[{
      "profile_name": "OABOOTCAMP_AI",
      "role": "You are a sales analyst for a consumer electronics company. You answer business questions using data from the sales database only, never from general knowledge. Revenue is gross unless the user asks for net revenue (revenue minus discount). Profit is revenue minus fixed and variable cost. Include all order statuses unless the user explicitly asks about a specific status. Sales data covers January 2024 to September 2026.",
      "enable_human_tool": "false"
    }]',
    description => 'Sales analyst over OABOOTCAMP data'
  );
END;
/
```

`enable_human_tool` is false because OPAF will call the agent non-interactively; the agent must make reasonable assumptions instead of pausing for clarification.

## Task

```sql
BEGIN
  DBMS_CLOUD_AI_AGENT.CREATE_TASK(
    task_name  => 'SALES_ANALYSIS_TASK',
    attributes => q'[{
      "instruction": "Answer the following business question: {query}. Use the OABOOTCAMP_SALES_SQL tool with the runsql action to retrieve data. Prefer a single query that returns all needed numbers at once (for example grouped by year and channel) instead of several separate queries. Report only numbers exactly as returned by the tool; never estimate or invent values. You may compute simple differences between returned numbers. Return a concise answer with the key numbers formatted with thousand separators, followed by one or two sentences of interpretation. State any assumption about time period or metric definition.",
      "tools": ["OABOOTCAMP_SALES_SQL"],
      "enable_human_tool": "false"
    }]',
    description => 'Answer sales questions with data'
  );
END;
/
```

Two instructions keep answers repeatable: one grouped query instead of several separate ones, and reporting only numbers returned by the tool.

## Team

```sql
BEGIN
  DBMS_CLOUD_AI_AGENT.CREATE_TEAM(
    team_name  => 'OABOOTCAMP_SALES_TEAM',
    attributes => q'[{
      "agents": [{"name": "SALES_ANALYST_AGENT", "task": "SALES_ANALYSIS_TASK"}],
      "process": "sequential"
    }]',
    description => 'In-database sales analyst team'
  );
END;
/
```

All four objects should show `ENABLED`:

```sql
SELECT 'TOOL'  AS type, tool_name  AS name, status FROM user_ai_agent_tools
UNION ALL
SELECT 'AGENT', agent_name, status FROM user_ai_agents
UNION ALL
SELECT 'TASK',  task_name,  status FROM user_ai_agent_tasks
UNION ALL
SELECT 'TEAM',  agent_team_name, status FROM user_ai_agent_teams;
```

## Running the team

`RUN_TEAM` needs a real conversation ID from `DBMS_CLOUD_AI.CREATE_CONVERSATION`. To check that answers are repeatable, I run the same question three times, each in a fresh conversation:

```sql
SET SERVEROUTPUT ON
DECLARE
  l_conv   VARCHAR2(100);
  l_answer CLOB;
BEGIN
  FOR i IN 1 .. 3 LOOP
    l_conv := DBMS_CLOUD_AI.CREATE_CONVERSATION();

    l_answer := DBMS_CLOUD_AI_AGENT.RUN_TEAM(
      team_name   => 'OABOOTCAMP_SALES_TEAM',
      user_prompt => 'Compare profit in 2025 vs 2024 by sales channel and tell me which channel improved the most',
      params      => '{"conversation_id": "' || l_conv || '"}'
    );

    DBMS_OUTPUT.PUT_LINE('===== RUN ' || i || ' =====');
    DBMS_OUTPUT.PUT_LINE(DBMS_LOB.SUBSTR(l_answer, 4000, 1));
  END LOOP;
END;
/
```

All three runs returned the same numbers. One of them:

> - **Online:** 2024 = $1,438,821.21, 2025 = $2,099,559.05, Increase = $660,738
> - **Store:** 2024 = $2,223,219.07, 2025 = $3,498,467.01, Increase = $1,275,248
> - **Catalog:** 2024 = $699,472.58, 2025 = $1,360,396.31, Increase = $660,924
>
> All channels saw higher profit in 2025, but the **Store channel improved the most**, with an increase of about **$1.28 million**. (Profit is calculated as revenue − fixed cost − variable cost, including all order statuses.)

The agent planned the comparison, retrieved profit for both years per channel, computed the deltas and picked the winner — the kind of question a single `SELECT AI` call struggles with.

## Checking against ground truth

Before I trust an agent in a demo, I compare its answer with hand-written SQL that involves no LLM:

```sql
SELECT f.channel_name,
       t.cal_year,
       ROUND(SUM(f.revenue))                                  AS revenue,
       ROUND(SUM(f.cost_fixed))                               AS cost_fixed,
       ROUND(SUM(f.cost_variable))                            AS cost_variable,
       ROUND(SUM(f.revenue - f.cost_fixed - f.cost_variable)) AS profit
FROM   f_revenue f
JOIN   d_time t ON f.time_bill_dt = t.day_dt
WHERE  t.cal_year IN (2024, 2025)
GROUP  BY f.channel_name, t.cal_year
ORDER  BY f.channel_name, t.cal_year;
```

| Channel | Year | Revenue | Fixed cost | Variable cost | Profit |
|---|---|---:|---:|---:|---:|
| Catalog | 2024 | 14,690,302 | 3,146,801 | 10,844,028 | 699,473 |
| Catalog | 2025 | 16,223,837 | 3,284,646 | 11,578,796 | 1,360,396 |
| Online | 2024 | 25,447,573 | 5,311,055 | 18,697,697 | 1,438,821 |
| Online | 2025 | 28,325,626 | 5,752,537 | 20,473,530 | 2,099,559 |
| Store | 2024 | 39,442,126 | 8,300,655 | 28,918,252 | 2,223,219 |
| Store | 2025 | 48,870,537 | 9,861,679 | 35,510,391 | 3,498,467 |

The agent's answers match exactly. These numbers are the ground truth for every flow in the rest of the series.

## What made it repeatable

A business rule that lives only in comments and role text may be applied in one run and skipped in the next. Three things made the team return the same answer every time:

- rules stated explicitly and positively ("include all order statuses"),
- `temperature` 0 in the profile,
- a task instruction asking for one grouped query and only numbers returned by the tool.

The team works in the database. In Part 4 I put it, and plain Select AI, in front of users with OPAF's native Select AI nodes.

---

This post is part of my [Select AI Agent meets OPAF series](SERIES-URL).
