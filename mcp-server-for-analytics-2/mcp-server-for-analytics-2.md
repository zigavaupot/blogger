**A new paradigm** is reshaping business analytics. Instead of the traditional *build a dashboard, then interpret it* approach, organizations are moving toward interactive narrative analytics; a model where users begin with natural-language questions, the system retrieves governed and trusted facts through retrieval-augmented generation (RAG), and large language models (LLMs) synthesize explanations that users can probe, refine, and challenge. The experience evolves from static charts and filters into a continuous analytical dialogue: what happened, why it happened, what may happen next, and what actions to take—all anchored in a shared semantic layer and consistent metric definitions.

In this shift, LLMs redefine the **user interface**, RAG redefines **trust**, and MCP servers redefine **integration**. RAG constrains generative models to validated enterprise sources—datasets, KPIs, subject areas, and documentation—ensuring transparency and traceability of insights. MCP (Model Context Protocol) then provides a standardized, secure way for AI agents to invoke analytics tools and services. Together, these technologies transform analytics from something users passively consume into something AI agents can actively operate, enabling richer, more exploratory, and story-driven insights that dynamically generate explanations, visuals, anomaly summaries, and follow-up questions on demand—without the need to constantly redesign dashboards.

**Oracle Analytics Cloud** (OAC) is actively aligning with this shift by introducing an **OAC MCP server**, which acts as a standardized bridge between MCP-compatible AI clients and OAC’s governed analytics assets. Through natural-language interactions, AI clients can securely query and explore enterprise analytics content or invoke OAC tools and APIs. Crucially, this is done while preserving enterprise-grade controls such as OAuth-based authentication and full adherence to user-level permissions, ensuring that every response remains consistent with OAC’s security and governance model.

In practical terms, this allows OAC to become part of the narrative analytics workflow beyond the boundaries of its native UI. By registering the OAC MCP server with AI clients—such as conversational assistants or developer tooling—organizations enable AI agents to retrieve governed metrics, summarize workbook insights, and answer contextual questions like *what does this KPI represent and why did it change?*. All of this happens while staying anchored to OAC’s semantic layer, metric definitions, and access rights, effectively extending trusted analytics into conversational and agent-driven experiences.

How? Let's take a look at one simple example.

Let's start our analysis with simple request `use sales data` which is entered chat box in Claude.

![Use Sales Data](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/use-sales-data.png)

Data analysis will begin with discovery and description of the data. Request to obtain available datasets in an Oracle Analytics instance is issued:

![Discover Data](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/oracle-analytics-discoverer-data.png)

Response is in a form of JSON file (note: the list of datasets is much longer, here i'm showing only *Sales Data*):

{% raw %}
```json
{"Datasets":[{{"displayName":"Sales Data","name":"'ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA'","description":"Uploaded from SAMPLE_SALES_DATA.xlsx.","model":"custom","type":"datasets"}]}
```
{% endraw %}

Dataset has been successfully identified and found, hence next step to describe it automatically begins:

![Discover Data](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/oracle-analytics-describe-data.png)

Response is as follows:

{% raw %}
```json
{
  "subjectArea": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA')",
  "tables": [
    {
      "tableName": "SAMPLE_SALES_DATA",
      "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\"",
      "columns": {
        "attributes": [
          {
            "name": "Order Key",
            "displayName": "Order Key",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Order Key\""
          },
          {
            "name": "Order Status",
            "displayName": "Order Status",
            "dataType": "VARCHAR",
            "length": 17,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Order Status\""
          },
          {
            "name": "Time Bill Dt",
            "displayName": "Time Bill Dt",
            "dataType": "TIMESTAMP",
            "precision": 23,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\""
          },
          {
            "name": "Time Paid Dt",
            "displayName": "Time Paid Dt",
            "dataType": "TIMESTAMP",
            "precision": 23,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Paid Dt\""
          },
          {
            "name": "Prod Item Key",
            "displayName": "Prod Item Key",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Prod Item Key\""
          },
          {
            "name": "Cust Number",
            "displayName": "Cust Number",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cust Number\""
          },
          {
            "name": "Cust Name",
            "displayName": "Cust Name",
            "dataType": "VARCHAR",
            "length": 30,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cust Name\""
          },
          {
            "name": "Cust Birth Dt",
            "displayName": "Cust Birth Dt",
            "dataType": "TIMESTAMP",
            "precision": 23,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cust Birth Dt\""
          },
          {
            "name": "Cust Crdt Rate",
            "displayName": "Cust Crdt Rate",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cust Crdt Rate\""
          },
          {
            "name": "Cust Gender",
            "displayName": "Cust Gender",
            "dataType": "VARCHAR",
            "length": 2,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cust Gender\""
          },
          {
            "name": "Cust Segment",
            "displayName": "Cust Segment",
            "dataType": "VARCHAR",
            "length": 21,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cust Segment\""
          },
          {
            "name": "Cust Marital Status",
            "displayName": "Cust Marital Status",
            "dataType": "VARCHAR",
            "length": 12,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cust Marital Status\""
          },
          {
            "name": "Cust Type",
            "displayName": "Cust Type",
            "dataType": "VARCHAR",
            "length": 9,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cust Type\""
          },
          {
            "name": "Addr Key",
            "displayName": "Addr Key",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Addr Key\""
          },
          {
            "name": "Address1",
            "displayName": "Address1",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Address1\""
          },
          {
            "name": "Address2",
            "displayName": "Address2",
            "dataType": "VARCHAR",
            "length": 45,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Address2\""
          },
          {
            "name": "Postal Code",
            "displayName": "Postal Code",
            "dataType": "VARCHAR",
            "length": 12,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Postal Code\""
          },
          {
            "name": "City",
            "displayName": "City",
            "dataType": "VARCHAR",
            "length": 32,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"City\""
          },
          {
            "name": "State Prov",
            "displayName": "State Prov",
            "dataType": "VARCHAR",
            "length": 21,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"State Prov\""
          },
          {
            "name": "Region",
            "displayName": "Region",
            "dataType": "VARCHAR",
            "length": 12,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Region\""
          },
          {
            "name": "Country Code",
            "displayName": "Country Code",
            "dataType": "VARCHAR",
            "length": 5,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Country Code\""
          },
          {
            "name": "Country Name",
            "displayName": "Country Name",
            "dataType": "VARCHAR",
            "length": 59,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Country Name\""
          },
          {
            "name": "Area",
            "displayName": "Area",
            "dataType": "VARCHAR",
            "length": 20,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Area\""
          },
          {
            "name": "Channel Name",
            "displayName": "Channel Name",
            "dataType": "VARCHAR",
            "length": 12,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Channel Name\""
          },
          {
            "name": "Prod Brand",
            "displayName": "Prod Brand",
            "dataType": "VARCHAR",
            "length": 12,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Prod Brand\""
          },
          {
            "name": "Prod Lob",
            "displayName": "Prod Lob",
            "dataType": "VARCHAR",
            "length": 20,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Prod Lob\""
          },
          {
            "name": "Prod Type",
            "displayName": "Prod Type",
            "dataType": "VARCHAR",
            "length": 18,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Prod Type\""
          },
          {
            "name": "Product",
            "displayName": "Product",
            "dataType": "VARCHAR",
            "length": 39,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Product\""
          },
          {
            "name": "Prod Item Dsc",
            "displayName": "Prod Item Dsc",
            "dataType": "VARCHAR",
            "length": 84,
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Prod Item Dsc\""
          }
        ],
        "measures": [
          {
            "name": "Units",
            "displayName": "Units",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Units\""
          },
          {
            "name": "Discnt Value",
            "displayName": "Discnt Value",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Discnt Value\""
          },
          {
            "name": "Cost Fixed",
            "displayName": "Cost Fixed",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cost Fixed\""
          },
          {
            "name": "Cost Variable",
            "displayName": "Cost Variable",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Cost Variable\""
          },
          {
            "name": "Revenue",
            "displayName": "Revenue",
            "dataType": "NUMERIC",
            "nullable": true,
            "fullyQualifiedName": "XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Revenue\""
          }
        ]
      }
    }
  ]
}
```
{% endraw %}

Based on this response, chat formulates final response:

Measures

* Revenue, Units, Discount Value, Cost Fixed, Cost Variable

Product Dimensions

* Product, Prod Brand, Prod Lob (Line of Business), Prod Type

Customer Dimensions

* Cust Name, Cust Segment, Cust Type, Cust Gender, Cust Marital Status, Cust Credit Rate

Geography

* City, State Prov, Region, Country Name, Area

Time

* Time Bill Dt, Time Paid Dt

Channel

* Channel Name

Order Info

* Order Key, Order Status

Since we are chatting with our sales data, here are some options suggested by chat:

* Revenue by product brand or region
* Top customers by revenue
* Sales performance by channel
* Customer segment analysis
* Time-based trends

We will continue with more general question and request to analyze revenue:

![Analyze Revenue](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/analyze-revenue.png)

Now, MCP server begins more detailed analysis of my data. It basically creates an *analysis* plan to analyze data provided - a bit like **Auto Insights** in Oracle Analytics.

![Analyze Revenue Steps](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/analyze-revenue-steps.png)

Let's examine the 1st couple of the steps above. 

In the 1st step, *Orchestrated multidimensional revenue analysis accross product, region and channel*, MCP Server simply explains it **Thought process** as:

*The user wants to analyze revenue from the Sales Data dataset. Let me run a few queries to provide a comprehensive revenue analysis - by different dimensions like product, region, customer segment, channel, etc.*

In the next, it starts generating requests and gathering responses to support this process. For example, in the first *oracle_analytics_execute_logical_sql* request, MCP Server generates the following **Request**:

{% raw %}
```
{
  `query`: `SELECT 
    XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Prod Brand\" AS llm_0,
    SUM(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Revenue\") AS llm_1
FROM XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA')
GROUP BY XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Prod Brand\"
ORDER BY llm_1 DESC
FETCH FIRST 20 ROWS ONLY`
}
```
{% endraw %}

and Oracle Analytics would respond with this **Response**:

{% raw %}
```json
{
  "metadata": {
    "requestId": "5db5d3d4-7a98-4c89-a5a1-c9da0ff44f57",
    "batchSize": 1000,
    "startTime": 1766162116326
  },
  "batches": [
    {
      "complete": true,
      "cursorId": "1ffcb9df-acc0-4020-9f18-51f3aa6eabf1",
      "batchNumber": 1,
      "data": [
        {
          "llm_0": "FunPod",
          "llm_1": 2047226.99
        },
        {
          "llm_0": "BizTech",
          "llm_1": 2032292.78
        },
        {
          "llm_0": "HomeView",
          "llm_1": 1013841.4
        }
      ],
      "hasMore": false,
      "totalRecordsStreamed": 3,
      "isComplete": true,
      "recordsInBatch": 3,
      "timestamp": 1766162116329
    }
  ],
  "status": {
    "result": "success",
    "error": false,
    "message": "Streaming completed successfully"
  },
  "summary": {
    "completed": true,
    "totalBatches": 1,
    "totalRecords": 3,
    "endTime": 1766162116331,
    "durationMs": 5
  }
}
```
{% endraw %}

In the 3rd step, **Thought Process** continues with statement:

*Good, I have revenue by brand. Let me get more dimensions for a comprehensive analysis.*

And so on till the last, 13th step in the *Thought process*. The result of this simplest *analyze data* request is as follows:

## Revenue Analysis

### Overall Performance

| Metric | Value |
|--------|-------|
| **Total Revenue** | $5,093,361 |
| **Total Units Sold** | 54,941 |
| **Total Orders** | 5,248 |
| **Avg Revenue/Order** | $970 |
| **Total Costs** | $5,101,604 (Fixed: $1.37M + Variable: $3.73M) |
| **Total Discounts** | $127,519 |

---

### By Brand
| Brand | Revenue | Share |
|-------|---------|-------|
| **FunPod** | $2,047,227 | 40.2% |
| **BizTech** | $2,032,293 | 39.9% |
| **HomeView** | $1,013,841 | 19.9% |

FunPod and BizTech are neck-and-neck, together accounting for 80% of revenue.

---

### By Region
| Region | Revenue | Share |
|--------|---------|-------|
| **EMEA** | $2,031,918 | 39.9% |
| **Americas** | $2,020,962 | 39.7% |
| **APAC** | $1,040,480 | 20.4% |

Very balanced between EMEA and Americas; APAC presents a growth opportunity.

---

### By Channel
| Channel | Revenue | Units | Avg/Unit |
|---------|---------|-------|----------|
| **Store** | $2,867,342 | 31,408 | $91 |
| **Online** | $1,025,136 | 10,945 | $94 |
| **Reseller** | $728,994 | 7,517 | $97 |
| **Catalog** | $471,890 | 5,071 | $93 |

Store dominates with 56% of revenue. Reseller has the highest average price per unit.

---

### By Customer Segment
| Segment | Revenue | Customers | Avg/Customer |
|---------|---------|-----------|--------------|
| **Active Singles** | $1,447,862 | 1,033 | $1,402 |
| **Baby Boomers** | $857,779 | 731 | $1,174 |
| **Rural based** | $767,315 | 642 | $1,195 |
| **Students** | $751,100 | 604 | $1,244 |
| **Urban based** | $681,543 | 578 | $1,179 |
| **Others** | $421,959 | 335 | $1,260 |
| **Seniors** | $165,803 | 144 | $1,151 |

Active Singles are the most valuable segment both in total and per-customer spend.

---

### By Product Type
| Product Type | Revenue |
|--------------|---------|
| **Camera** | $1,023,235 |
| **Portable** | $806,644 |
| **Phones** | $780,632 |
| **Audio** | $740,477 |
| **Plasma** | $500,511 |
| **LCD** | $388,826 |
| **Smart Phones** | $363,872 |

Cameras lead product revenue, followed by portable devices and phones.

---

### Top 10 Customers
| Customer | Revenue |
|----------|---------|
| Christopher Brown | $12,793 |
| Adam Dohrmann | $11,643 |
| Brennan Dwyer | $11,121 |
| Rahmat Zae | $10,648 |
| Alexis Robinson | $10,076 |

---

### Key Insights

1. **Profitability concern** — Total costs ($5.1M) nearly equal revenue ($5.09M), suggesting very thin margins
2. **Brand balance** — FunPod and BizTech are equally strong; HomeView could use attention
3. **Channel opportunity** — Online (20%) has room to grow vs Store (56%)
4. **Geographic gap** — APAC at only 20% suggests expansion potential
5. **High-value segment** — Active Singles should be priority for marketing efforts

Would you like me to drill deeper into any of these areas—profitability by product, regional trends, or customer behavior?

This is really totally different from what we've been used to. By the way, I can also issue request to *Visualize these reports* which would result in a html report `sales_dashboard.html`:

![Sales Revenue Dasbhoard](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/sales-revenue-dashboard.png)

Click here to open: [Sales Revenue Dasbhoard](https://https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/files/sales_dashboard.html)

And we can follow suggestion provided *Would you like me to drill deeper into any of these areas—profitability by product, regional trends, or customer behavior?*

![Drill Deeper](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/drill-deeper.png)

Based on this, **Thought Process** prepares and executes a new plan:

![Thought Process for Customer profitability](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/thought-process-customer-profitability.png)

And here is detailed *Customer Profitability Analysis* dashboard:

![Customer profitability analysis](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/customer-profitability-analysis.png)

Click here to open: [Customer profitability analysis](https://https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/files/sales_dashboard.html)

How cool is that? The tool now generates reports for us and provides explanations, reasoning, and there is no coding required. Just data. Pure data. 

Key to success is, data is well organized in our data warehouse, and there is a comprehensive data model across those data, so we don't get any halucinations and similar anomalies that are usually present in similar scenarios. **Oracle Analytics Semantic Model is the key ingridient.**




