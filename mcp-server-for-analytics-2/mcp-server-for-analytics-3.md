![Going deep dive](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/going-deep-dive.png)

When I first tried the Oracle Analytics AI Assistant, I was genuinely surprised by what it could do. Most queries ran very well—even in Slovenian, a language not officially supported in Oracle Analytics ☹️, and I was able to truly talk to my data.

However, when I tried to push the AI Assistant toward more advanced analytics, such as applying functions like TRENDLINE or CLUSTERS, both of which are one-click advanced analytics features, it simply didn’t understand what I was asking.

When the Oracle Analytics Cloud MCP Server became available, I decided to see whether it could handle these advanced analytics functions. And it did.

## TRENDLINE

First, I asked the MCP Server to **analyze sales revenue for the last two years of available data**. Since my dataset is fairly old, I wanted to avoid any misunderstandings, so I explicitly specified that the analysis should focus on the last two years of available data.

So, here’s how it all went:

Click here to open: [Customer profitability analysis](https://https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/files/yoy_sales_analysis.html)

As you can see, analysis produced is already quite comprehensive and deep, but our focus is on **displaying the last year of sales revenue by months on the chart**:

![2013 Monthly Sales Revenue](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/monthly-sales-revenue.png)

This chart is our baseline for calculating a trend line, so we can request to **Add trend line to this chart**.

MCP Server thought a bit, prepared a plan and produced a result, which was very likely correct. However, there was no evidence that Oracle Analytics' `TRENLINE` function was actually used - it was not. All trends were calculated outside of Oracle Analytcs.  

That is why I added specific instruction **add trend line to this chart, use Oracle Analytics to calculate**. We can see now in the console that MCP Server actually generated the following logical SQL in its thought process:

```console
{
  `query`: `SELECT 
    MONTH(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\") AS llm_0,
    SUM(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Revenue\") AS llm_1,
    TRENDLINE(SUM(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Revenue\"), (MONTH(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\")) BY (), 'LINEAR', 'VALUE') AS llm_2
FROM XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA')
WHERE YEAR(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\") = 2013
GROUP BY MONTH(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\")
ORDER BY llm_0
FETCH FIRST 12 ROWS ONLY`
}
```

From the MCP Server output, we can see that it understands Oracle Analytics functions and knows how specifically to use `TRENDLINE` function:

![Calculating Trendline](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/calculating-trendline.png)

Based on the results, our monthly sales chart includes linear trend line:

![Linear Trendline](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/linear-trendline.png)


To confirm that MCP Server really understands what we are talking about, the following request can be asked **apply polynomial model instead of linear**. And MCP server executes:

![Thought process for polynomial trend](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/thought-process-for-polynomial-trend.png)

The 1st step of the process generates a logical SQL query:

```console
{
  `query`: `SELECT 
    MONTH(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\") AS llm_0,
    SUM(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Revenue\") AS llm_1,
    TRENDLINE(SUM(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Revenue\"), (MONTH(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\")) BY (), 'POLYNOMIAL', 'VALUE') AS llm_2
FROM XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA')
WHERE YEAR(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\") = 2013
GROUP BY MONTH(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\")
ORDER BY llm_0
FETCH FIRST 12 ROWS ONLY`
}

```

We can see that POLYNOMIAL model has bee applied:

```console
TRENDLINE(SUM(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Revenue\"), (MONTH(XSA('ziga.vaupot@smartq.si'.'SAMPLE_SALES_DATA').\"SAMPLE_SALES_DATA\".\"Time Bill Dt\")) BY (), POLYNOMIAL', 'VALUE') AS llm_2
```
And the final output shows sales by month with polynomial trend line which much better fits than linear:

![Polynomial Trendline](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/polynomial-trendline.png)

Based on this, we can definitely conclude, OAC MCP Server is more capable than OAC AI Assistant.

## CLUSTERS

With CLUSTERS, I have experienced some problems, so my CLUSTERS were not applied on XSA (Extended Subject Area) datasets - i.e. uploaded Sales Data excel. Therefore I set my OABOOTCAMP semantic model and retried to *force* clusters on that subject area.

My request was simple: **segment customers into 5 clusters**.

In the first step, I got the following response:

```console
I'll cluster customers based on their purchasing behavior - Revenue, Units, and Profit. Let me build the query.

The available measures for clustering:

- Revenue
- Units
- Discount Value
- Profit
- Total Costs

And customer attributes:

- Customer Nr.
- Customer
- Age
- Credit Rate

Let me create a clustering query that segments customers into 5 clusters based on Revenue, Units, and Profit.
```

Based on this, we can see that MCP Server figured out that it needs to cluster customers into 5 segments using their purchasing behavior (Revenue, Units, and Profit). And here is the request to retrieve data:

```console
{
  `query`: `SELECT 
    \"OA Boocamp Subject Area\".\"D Customers\".\"Customer\" AS llm_0,
    \"OA Boocamp Subject Area\".\"Revenue Metrics\".\"Revenue\" AS llm_1,
    \"OA Boocamp Subject Area\".\"Revenue Metrics\".\"Units\" AS llm_2,
    \"OA Boocamp Subject Area\".\"Profit Metrics\".\"Profit\" AS llm_3,
    CLUSTER((\"OA Boocamp Subject Area\".\"D Customers\".\"Customer\"), 
            (\"OA Boocamp Subject Area\".\"Revenue Metrics\".\"Revenue\", 
             \"OA Boocamp Subject Area\".\"Revenue Metrics\".\"Units\",
             \"OA Boocamp Subject Area\".\"Profit Metrics\".\"Profit\"), 
            'ClusterName', 'algorithm=k-means;numClusters=5') AS llm_4
FROM \"OA Boocamp Subject Area\"
ORDER BY llm_4, llm_1 DESC
FETCH FIRST 500 ROWS ONLY`,
  `maxRows`: 500
}
```

Note that there is a `CLUSTER` function applied using `algorithm=k-means` and `numCluster=5` as parameters. Additionally MCP Server ran additional query to summarize cluster's characteristics.

Here's the customer segmentation into 5 clusters based on **Revenue**, **Units**, and **Profit**:

| Cluster | Customers | Total Revenue | Total Units | Total Profit | Profile |
|---------|-----------|--------------|-------------|--------------|---------|
| **Cluster 5** | 3,316 | $65.97M | 896K | **$13.21M** | 🌟 **Premium Customers** — High volume, highly profitable |
| **Cluster 3** | 3,778 | $40.57M | 605K | **$7.23M** | 💼 **Core Business** — Largest segment, solid profitability |
| **Cluster 4** | 783 | $29.58M | 369K | **$2.86M** | 📈 **Growth Potential** — High revenue per customer, moderate profit |
| **Cluster 2** | 1,545 | $24.53M | 345K | **-$4.69M** | ⚠️ **At Risk** — Unprofitable, needs cost review |
| **Cluster 1** | 578 | $12.35M | 158K | **-$7.29M** | 🔴 **Loss Leaders** — Smallest & most unprofitable segment |

Finally, i have requested visualization of the data:

![Clusters](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/customer-segmentation-analysis.png)

## Key takeaways

* **Natural language works—but precision matters**. Oracle Analytics AI Assistant handles general analysis well, but struggles when advanced analytics functions (like TRENDLINE and CLUSTER) are requested implicitly rather than explicitly.
* **MCP Server understands OAC semantics**. Unlike the AI Assistant, the Oracle Analytics Cloud MCP Server can correctly generate and execute OAC-specific functions in logical SQL when given clear instructions.
* **Advanced analytics require explicit intent**. Phrases like *use Oracle Analytics to calculate* make a crucial difference—prompt clarity determines whether calculations are executed inside OAC or externally.
* **TRENDLINE support goes beyond basics**. MCP Server not only applies linear trendlines, but also understands and correctly executes alternative models such as polynomial, using native OAC functions.
* **CLUSTER works reliably on semantic models**. Clustering on XSA (uploaded datasets) may be limited, but MCP Server performs well when working against a proper OAC semantic model (e.g. OA Bootcamp).
* **End-to-end analytical reasoning is visible**. MCP Server exposes its thought process through generated logical SQL, making it easier to validate correctness and build trust in the results.
* **MCP Server is a step forward for power users**. For advanced analytics scenarios, MCP Server is clearly more capable than the current OAC AI Assistant and better suited for analysts who need precise, reproducible results.