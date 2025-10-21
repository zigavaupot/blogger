---
layout: none
title: Graphs and GraphRAGs
---

# Graphs and GraphRAGs

## WORKSHOP: Graphs – the bridge between data and generative artificial

### Starting with Graphs

We have two tables, **BANK_ACCOUNTS** and **BANK_TRANSFERS**.

* stores information about customers’ bank accounts, such as account
numbers, account holders and balances.

* stores records of money transfers between bank accounts, including
details like source account, destination account, transaction description
and amount.

```oracle
SELECT * FROM BANK_ACCOUNTS FETCH FIRST 10 ROWS ONLY;
```

```oracle
SELECT * FROM BANK_TRANSFERS FETCH FIRST 10 ROWS ONLY;
```

We’ll now create an SQL Property Graph using these two tables.


An SQL Property Graph lets you represent data as nodes (vertices) and
relationships (edges), both of which can have properties (key–value
pairs). This makes it possible to explore and query data in a graph-like
way—for example, finding how different accounts are connected through
transfers—while still working inside a traditional SQL database.


You don’t need to set up a separate Graph Server to do this; the graph can
be created and queried directly within SQL.

```oracle
CREATE PROPERTY GRAPH bank_transfers_sql_graph
  VERTEX TABLES (
    BANK_ACCOUNTS
      KEY ( id )
      LABEL accounts
      PROPERTIES ( id, name )
    )
    EDGE TABLES (
      BANK_TRANSFERS
        SOURCE KEY ( src_acct_id ) REFERENCES BANK_ACCOUNTS(id)
          DESTINATION KEY ( dst_acct_id ) REFERENCES BANK_ACCOUNTS(id)
        LABEL transfers
        PROPERTIES ( amount, description, src_acct_id, dst_acct_id, txn_id )
    );
```

The command above creates a property graph named
**bank_transfers_sql_graph** using the relational tables **BANK_ACCOUNTS**
and **BANK_TRANSFERS**.


It defines how rows in those tables map to graph elements — vertices
(nodes) and edges (relationships) — so you can run graph queries (like
finding connections or paths) directly on your relational data.


The CREATE statement builds a graph where:

* Nodes = Bank accounts (from BANK_ACCOUNTS)

* Edges = Money transfers (from BANK_TRANSFERS)

* Each transfer connects one account (the sender) to another (the
receiver) and carries details like amount, description, and transaction
ID.


**VERTEX TABLES (BANK_ACCOUNTS)**: Defines which table(s) represent nodes
in the graph.


* KEY (id) → The column id uniquely identifies each vertex.

* LABEL accounts → Each vertex from this table will be labeled accounts.

* PROPERTIES (id, name) → The vertex will store these columns as its
properties.


**EDGE TABLES (BANK_TRANSFERS)**: Defines which table(s) represents edges
(connections) between nodes.


* SOURCE KEY (src_acct_id) → The source of the edge comes from the
src_acct_id column.

* DESTINATION KEY (dst_acct_id) → The destination of the edge comes from
the dst_acct_id column.

* Both reference the id column in the BANK_ACCOUNTS table — meaning edges
connect accounts.

* LABEL transfers → Each edge is labeled transfers.

* PROPERTIES (amount, description, src_acct_id, dst_acct_id, txn_id) →
These columns are stored as properties on the edge.


Let's play with this grpah. We will run queries and review results within
this notebook, and will visualize results using SQL Developer Graph
Visualiztion fro VS Code Extension (run from SQL Worksheet).

The simplest graph query is to display nodes and edges that connect these.

```oracle
-- List all transfers with sender and receiver details

SELECT * FROM GRAPH_TABLE (bank_transfers_sql_graph
  MATCH
    (src) -[t]- (dst)
  COLUMNS (src.id AS sender_id, t.txn_id AS transaction_id, dst.id AS receiver_id)
);
```

As you can see, the SQL statements look almost the same as regular SQL —

```oracle
-- Find top 10 accounts by number of sent transfers


SELECT sender_id, count(*) FROM GRAPH_TABLE (bank_transfers_sql_graph
  MATCH
    (src) -[t]- (dst)
  COLUMNS (src.id AS sender_id, t.txn_id AS transaction_id, dst.id AS receiver_id)
) GROUP BY sender_id
  ORDER BY count(*) DESC
  FETCH FIRST 10 ROWS ONLY;
```

The MATCH clause can be further specified by adding labels and property

```oracle
-- Find top 10 accounts by number of sent transfers (with vertex labels)


SELECT sender_id, count(*) FROM GRAPH_TABLE (bank_transfers_sql_graph
  MATCH
    (src IS accounts) -[t IS transfers]- (dst IS accounts)
  COLUMNS (src.id AS sender_id, t.txn_id AS transaction_id, dst.id AS receiver_id)
) GROUP BY sender_id
  ORDER BY count(*) DESC
  FETCH FIRST 10 ROWS ONLY;
```

```oracle
-- Find all transfers from account 534 to any other account


SELECT * FROM GRAPH_TABLE (bank_transfers_sql_graph
  MATCH
  (src IS accounts WHERE src.id = 534) -[e IS transfers]-> (dst IS accounts)
  COLUMNS (src.id AS src_acct_id, e.amount AS amount, dst.id AS dst_acct_id)
);
```

```oracle
-- Find the 10 accounts that have received the most transfers

SELECT acct_id, COUNT(*) AS Num_Transfers 
FROM graph_table ( bank_sql_graph 
    MATCH (src) - [IS transfers] -> (dst) 
    COLUMNS ( dst.id AS acct_id )
) GROUP BY acct_id ORDER BY Num_Transfers DESC FETCH FIRST 10 ROWS ONLY; 
```

```oracle
-- Find the 10 accounts that are most often in the middle of a transfer
chain


SELECT acct_id, COUNT(*) AS Num_In_Middle 

FROM graph_table ( bank_sql_graph 
    MATCH (src) - [IS transfers] -> (via) - [IS transfers] -> (dst) 
    COLUMNS ( via.id AS acct_id )
) GROUP BY acct_id ORDER BY Num_In_Middle DESC FETCH FIRST 10 ROWS ONLY;
```

```oracle
-- Find all transfer chains that go through account 387


SELECT * FROM GRAPH_TABLE (bank_transfers_sql_graph
  MATCH (src) - [e1 IS transfers] -> (via IS accounts WHERE via.id = 387) - [e2 IS transfers] -> (dst) 
  COLUMNS (src.id AS src_acct_id, e1.txn_id AS e1_id, e1.amount AS e1_amount, via.id AS via_acct_id, e2.txn_id AS e2_id, e2.amount AS e2_amount, dst.id AS dst_acct_id)
);
```

```oracle
-- Find all transfer chains that end at account 387


SELECT * FROM GRAPH_TABLE (bank_transfers_sql_graph
  MATCH (src IS accounts) -[e1 IS transfers]-> (via IS accounts) -[e2 IS transfers]-> (dst IS accounts WHERE dst.id = 387)
  COLUMNS (src.id AS src_acct_id, e1.txn_id AS e1_id, e1.amount AS e1_amount, via.id AS via_acct_id, e2.txn_id AS e2_id, e2.amount AS e2_amount, dst.id AS dst_acct_id)
);
```

```oracle
-- Find all transfer chains of length 1 to 3 that start from account 534

SELECT * FROM GRAPH_TABLE ( bank_transfers_sql_graph
MATCH (s IS accounts) -[e IS transfers]->{1,3} (d IS accounts)
WHERE s.id = 534
ONE ROW PER STEP (src, t, dst)
COLUMNS (src.id AS src_acct_id,
        t.txn_id AS txn_id,
        dst.id AS dst_acct_id
    )
);
```

```oracle
-- Find all transfer chains of length 2 to 3 that start and end at the
same account


SELECT * FROM GRAPH_TABLE ( bank_transfers_sql_graph

MATCH (s IS accounts) -[e IS transfers]->{2,3} (d IS accounts)

WHERE s.id = d.id

ONE ROW PER STEP (src, t, dst)

COLUMNS (MATCHNUM() AS match_num,
        src.id AS src_acct_id,
        t.txn_id AS txn_id,
        dst.id AS dst_acct_id
    )
);
```

```oracle
-- Find the 10 accounts that are part of the most transfer cycles of
length 3 to 5


SELECT DISTINCT(account_id), COUNT(1) AS Num_Cycles 

FROM GRAPH_TABLE(bank_transfers_sql_graph
   MATCH (src)-[t IS transfers]->{3,5}(src)
    COLUMNS (src.id AS account_id)  
) GROUP BY account_id ORDER BY Num_Cycles DESC

FETCH FIRST 10 ROWS ONLY;
```

```oracle
-- Find all transfer chains of length 1 to 5 that start and end at account
135


SELECT matchnum, count(*) count

FROM GRAPH_TABLE(bank_transfers_sql_graph
   MATCH (s)-[e IS transfers]->{1,5}(d)
   WHERE s.id = 135
   AND s.id = d.id
   ONE ROW PER STEP (src, t, dst)
    COLUMNS (MATCHNUM() AS matchnum,
            src.id AS account_id,
            ELEMENT_NUMBER(src) AS elementNumber_src,
            t.txn_id AS txn_id,
            t.amount AS amount,
            ELEMENT_NUMBER(t) AS elementNumber_t,
            dst.id AS dst_account_id,
            ELEMENT_NUMBER(dst) AS elementNumber_dst,
            VERTEX_ID(src) AS vertex_id_src,
            EDGE_ID(t) AS edge_id_t,
            VERTEX_ID(dst) AS vertex_id_dst
    )  
) group by matchnum;
```

Now that we understand PGQL queries, we’ll explore how SQL Property

The following PL/SQL block we will set the active Generative AI profile to
GENAI_GRAPH_PROFILE_OCI using the DBMS_CLOUD_AI.SET_PROFILE procedure.


In practice, this means Oracle will use the OCI-based Generative AI model
(defined in that profile) for any subsequent AI-assisted operations, such
as natural language processing, SQL generation, or graph analysis within
the database session.

```oracle
BEGIN
    DBMS_CLOUD_AI.SET_PROFILE(
        profile_name => 'GENAI_GRAPH_PROFILE_OCI'
    );
END;
```

The procedure below retrieves all transfer relationships connected to a

```oracle
CREATE OR REPLACE PROCEDURE GRAPH_RAG_ACCOUNT_TRANSFERS (
    debugPrompt        IN  NUMBER   DEFAULT 0,
    entityname         IN  VARCHAR2,
    promptBegin        IN  VARCHAR2,
    resp               OUT VARCHAR2,        
    PropertyGraphRag   OUT VARCHAR2
) IS
  query VARCHAR2(4000);
BEGIN
  
  query := q'[
    WITH cteGraphData AS ( 
      SELECT
        src_id,
        src_name,
        trx_amount,
        dst_id,
        dst_name,
        src_id || '(' || src_name || '), transfered ' || trx_amount || ' to ' ||
        dst_id || '(' || dst_name || ')' AS information
      FROM GRAPH_TABLE(
        bank_transfers_sql_graph
        MATCH (src IS ACCOUNTS)-[trx IS TRANSFERS]->(dst IS ACCOUNTS)
        WHERE src.id = :a
        COLUMNS (
          src.id     AS src_id,
          src.name   AS src_name,
          trx.amount AS trx_amount,
          dst.id     AS dst_id,
          dst.name   AS dst_name
        )
      )
      ORDER BY trx_amount DESC
    )
    SELECT JSON_ARRAYAGG(
             information
             RETURNING CLOB
           ) AS result
    FROM cteGraphData
  ]';

  -- Get CLOB JSON into OUT param
  EXECUTE IMMEDIATE query INTO PropertyGraphRag USING entityname;

  -- Send prompt + info to LLM (make the concatenation a CLOB)
  SELECT DBMS_CLOUD_AI.GENERATE(
           prompt       =>  TO_CLOB(promptBegin) || '  with the following INFORMATION  ' || PropertyGraphRag,
           profile_name => 'GENAI_GRAPH_PROFILE_OCI',
           action       => 'chat'
         )
  INTO resp
  FROM dual;
END;

/
```

Let's ask now some smart questions!

```oracle
DECLARE
  v_resp VARCHAR2(8000);
  v_rag  VARCHAR2(8000);
BEGIN
  GRAPH_RAG_ACCOUNT_TRANSFERS(
    debugPrompt  => 1,
    entityname   => '387',             
    promptBegin  => 'which accounts received transfers and which amount from source account, show top 5 ordered by amount',
    resp         => v_resp,
    PropertyGraphRag => v_rag
  );

  DBMS_OUTPUT.PUT_LINE(SUBSTR(v_resp, 1, 32767));
END;
```

```oracle
DECLARE
  v_resp VARCHAR2(8000);
  v_rag  VARCHAR2(8000);
BEGIN
  GRAPH_RAG_ACCOUNT_TRANSFERS(
    debugPrompt  => 1,
    entityname   => '387',             
    promptBegin  => 'how many accounts received transfers from source account and what is total amount transfered',
    resp         => v_resp,
    PropertyGraphRag => v_rag
  );

  -- print safely (chunking optional; here we just show first 32767)
  -- DBMS_OUTPUT.PUT_LINE(SUBSTR(v_rag, 1, 32767));
  DBMS_OUTPUT.PUT_LINE(SUBSTR(v_resp, 1, 32767));
END;
```
