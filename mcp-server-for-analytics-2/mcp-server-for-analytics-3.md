But let's not stop there. One of the key learnings when using Oracle Analytics MCP Server is that is supports also functions that **Oracle Analytics' AI Assistant** is not aware of at all. For example, *TRENDLINE* function is something I wasn't able to produce while using AI Assistant, MCP Server is more than capable of using it. 

Let's check it out.

First I asked MCP Server to **analyze sales revenue for the last 2 years (of available data)** (my dataset is quite old, so to avoid missunderstandings I have specifically asked to review the last 2 years of *available data*).

Here is the analysis

Click here to open: [Customer profitability analysis](https://https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/files/yoy_sales_analysis.html)

But now, lets ask MCP Server to *display last year of sales revenue by months on the chart*:

![2013 Monthly Sales Revenue](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/customer-profitability-analysis.png)

Ok, great. Now ask it to calculate and draw trend line on this same chart by *Add trend line to this chart*

MCP Server now thinks a bit, makes a plan and produces result, which is most likely correct. However, there is no evidence that Oracle Analytics' `TRENLINE` function was actually used - most likely it was not. 

That is why I am adding specific instruction *add trend line to this chart, use Oracle Analytics to calculate*. 

MCP Server now knows to use `TRENDLINE` function:

![Calculating Trendline](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/calculating-trendline.png)

and chart is also produced:

![Linear Trendline](https://zigavaupot.github.io/blogger/mcp-server-for-analytics-2/images/linear-trendline.png)


... NEXT STEPS: change LINEAR to POLINOMIAL model
... TRY CLUSTERS 