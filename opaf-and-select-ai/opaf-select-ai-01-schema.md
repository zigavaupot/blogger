# Select AI Agent meets OPAF, Chapter 1: Making a star schema Select AI-ready

![Select AI Agent meets OPAF](https://zigavaupot.github.io/blogger/opaf-and-select-ai/images/select-ai-opaf-blog-series.png)

Select AI turns a question into SQL, but it only knows what the data dictionary tells it. My OA Bootcamp schema (`OABOOTCAMP`) is a classic sales star schema with no declared keys and no comments, so out of the box Select AI has nothing to go on except column names.

In this first chapter I prepare the schema: I validate the join keys, collect the literal values the LLM must use, define the business rules, and write table and column comments that act as the semantic layer. Every flow in the later chapters — native OPAF nodes, MCP or routing — reads these comments, which is why they all return the same numbers.

## The schema

I limited the demo to five tables:

- `F_REVENUE` (fact, 279,449 rows)
- `D_TIME` (25,933 rows)
- `D_CUSTOMERS` (10,000 rows)
- `D_GEOGRAPHY` (9,999 rows)
- `D_PRODUCTS` (521 rows)

The schema has no declared PK/FK constraints and no comments, so before writing any comments I validated the join keys.

## Validating the joins

```sql
-- Fact date range and time portion check
SELECT COUNT(*) total,
       COUNT(CASE WHEN TRUNC(time_bill_dt) <> time_bill_dt THEN 1 END) bill_has_time,
       MIN(time_bill_dt) min_bill, MAX(time_bill_dt) max_bill,
       MIN(time_paid_dt) min_paid, MAX(time_paid_dt) max_paid
FROM   f_revenue;

-- Which D_TIME column matches the fact dates
SELECT 'DAY_DT' col, COUNT(*) unmatched FROM f_revenue f
 WHERE NOT EXISTS (SELECT 1 FROM d_time t WHERE t.day_dt  = f.time_bill_dt)
UNION ALL
SELECT 'DATE_ID', COUNT(*) FROM f_revenue f
 WHERE NOT EXISTS (SELECT 1 FROM d_time t WHERE t.date_id = f.time_bill_dt);

-- Duplicate keys in dimensions
SELECT 'D_PRODUCTS' dim, COUNT(*) - COUNT(DISTINCT prod_item_key) dup_keys FROM d_products  UNION ALL
SELECT 'D_GEOGRAPHY',    COUNT(*) - COUNT(DISTINCT addr_key)            FROM d_geography UNION ALL
SELECT 'D_CUSTOMERS',    COUNT(*) - COUNT(DISTINCT cust_number)         FROM d_customers UNION ALL
SELECT 'D_TIME',         COUNT(*) - COUNT(DISTINCT day_dt)              FROM d_time;

-- Orphan fact rows
SELECT 'PROD' k, COUNT(*) orphans FROM f_revenue f WHERE NOT EXISTS (SELECT 1 FROM d_products  d WHERE d.prod_item_key = f.prod_item_key) UNION ALL
SELECT 'ADDR',   COUNT(*)         FROM f_revenue f WHERE NOT EXISTS (SELECT 1 FROM d_geography d WHERE d.addr_key      = f.addr_key)      UNION ALL
SELECT 'CUST',   COUNT(*)         FROM f_revenue f WHERE NOT EXISTS (SELECT 1 FROM d_customers d WHERE d.cust_number   = f.cust_number);
```

What I found:

- Fact dates have no time portion, and both `DAY_DT` and `DATE_ID` match 100%. I use `DAY_DT` as the join column.
- No duplicate dimension keys, no orphan fact rows.
- Bill dates run from 2024-01-01 to 2026-09-30.
- `D_TIME` covers about 71 years, far more than the fact data, so the comments state the actual data range.

The resulting joins:

| Fact column | Dimension column |
|---|---|
| `F_REVENUE.PROD_ITEM_KEY` | `D_PRODUCTS.PROD_ITEM_KEY` |
| `F_REVENUE.ADDR_KEY` | `D_GEOGRAPHY.ADDR_KEY` |
| `F_REVENUE.CUST_NUMBER` | `D_CUSTOMERS.CUST_NUMBER` |
| `F_REVENUE.TIME_BILL_DT` | `D_TIME.DAY_DT` (default sales date) |
| `F_REVENUE.TIME_PAID_DT` | `D_TIME.DAY_DT` (payment questions only) |

## Collecting exact literals

For low-cardinality columns I listed the distinct values:

```sql
SELECT 'ORDER_STATUS' col, LISTAGG(DISTINCT order_status, ' | ') vals FROM f_revenue   UNION ALL
SELECT 'CHANNEL_NAME',     LISTAGG(DISTINCT channel_name, ' | ')      FROM f_revenue   UNION ALL
SELECT 'CUST_SEGMENT',     LISTAGG(DISTINCT cust_segment, ' | ')      FROM d_customers UNION ALL
SELECT 'PROD_LOB',         LISTAGG(DISTINCT prod_lob, ' | ')          FROM d_products  UNION ALL
SELECT 'REGION',           LISTAGG(DISTINCT region, ' | ')            FROM d_geography;
-- (plus CUST_TYPE, CUST_GENDER, CUST_MARITAL_STATUS, PROD_TYPE, PROD_BRAND, AREA)
```

These values go straight into the column comments, so the LLM uses exact literals such as `'6-Cancelled'` instead of guessing `'Cancelled'`.

## Business rules

- `REVENUE` is gross.
- Net revenue = `REVENUE - DISCNT_VALUE`.
- Profit = `REVENUE - COST_FIXED - COST_VARIABLE` (discount not subtracted).
- Profit margin = profit / `REVENUE`.
- "Revenue" or "sales" without "net" means gross `REVENUE`.
- All order statuses are included by default. `ORDER_STATUS` is filtered only when a question explicitly mentions a status (cancelled, on hold, booked, paid ...).

A rule in a comment is guidance, not enforcement. I state each rule positively ("include all statuses") instead of leaving room for the LLM's own assumptions, and I verify the rules with tests.

## Comments as the semantic layer

The rules and joins live in the `F_REVENUE` table comment:

```sql
COMMENT ON TABLE f_revenue IS
'Sales fact table, one row per order line. Covers billing dates 2024-01-01 to 2026-09-30.
Joins: PROD_ITEM_KEY = D_PRODUCTS.PROD_ITEM_KEY; CUST_NUMBER = D_CUSTOMERS.CUST_NUMBER;
ADDR_KEY = D_GEOGRAPHY.ADDR_KEY; TIME_BILL_DT = D_TIME.DAY_DT.
For time-based questions join D_TIME on TIME_BILL_DT unless the question is explicitly about payment.
Business rules: REVENUE is gross. Net revenue = REVENUE - DISCNT_VALUE.
Profit = REVENUE - COST_FIXED - COST_VARIABLE (discount is not subtracted).
Profit margin = profit / REVENUE.
When a question says "revenue" or "sales" without "net", use REVENUE (gross).
Include ALL order statuses by default (do not filter on ORDER_STATUS). Filter on ORDER_STATUS only when the question explicitly mentions a status such as cancelled, on hold, booked or paid.';
```

Column comments carry meaning, synonyms, join hints and allowed values. A representative excerpt:

```sql
COMMENT ON COLUMN f_revenue.time_bill_dt  IS 'Billing date of the order line. Default date for all sales/revenue time analysis. Join to D_TIME.DAY_DT.';
COMMENT ON COLUMN f_revenue.time_paid_dt  IS 'Date the customer paid. Use only for payment-related questions (paid, collected, payment delay). Join to D_TIME.DAY_DT when needed.';
COMMENT ON COLUMN f_revenue.order_key     IS 'Order identifier. One order can have multiple lines; use COUNT(DISTINCT ORDER_KEY) for number of orders.';
COMMENT ON COLUMN f_revenue.revenue       IS 'Gross sales revenue amount (sales, turnover), before discount. Net revenue = REVENUE - DISCNT_VALUE.';
COMMENT ON COLUMN f_revenue.order_status  IS 'Order lifecycle status. Values: 1-Booked, 2-Fulfilled, 3-Shipped, 4-Billed, 5-Paid, 6-Cancelled, 9-On Hold. Use exact values including the number prefix.';
COMMENT ON COLUMN f_revenue.channel_name  IS 'Sales channel. Values: Catalog, Online, Store.';

COMMENT ON COLUMN d_products.prod_lob      IS 'Line of business, top product level. Values: Communication, Digital, Electronics, Games.';
COMMENT ON COLUMN d_customers.cust_birth_dt       IS 'Date of birth. Derive age as TRUNC(MONTHS_BETWEEN(SYSDATE, CUST_BIRTH_DT)/12).';

COMMENT ON TABLE d_time IS
'Calendar dimension, one row per day. Join DAY_DT to F_REVENUE.TIME_BILL_DT (sales date) or F_REVENUE.TIME_PAID_DT (payment date).
For year/quarter/month filters and grouping prefer CAL_YEAR, CAL_QTR, CAL_MONTH. Sales data exists only for 2024-01-01 to 2026-09-30.';

COMMENT ON COLUMN d_time.date_id        IS 'Duplicate of DAY_DT. Do not use for joins; use DAY_DT.';
```

The remaining comments for `D_PRODUCTS`, `D_CUSTOMERS`, `D_GEOGRAPHY` and `D_TIME` follow the same pattern: a table comment with the hierarchy and join key, and column comments with meaning and allowed values. Julian numbers, period start/end keys and first/last-day flags in `D_TIME` are intentionally left uncommented, so the LLM is not tempted to use them.

Select AI reads the comments only when the profile has `"comments": "true"`. Creating that profile, and giving the database access to OCI Generative AI, is the topic of Chapter 2.

---

Back to the [introduction and list of chapters](https://zigavaupot.blogspot.com/2026/10/introduction-to-select-ai-agent-meets.html).
