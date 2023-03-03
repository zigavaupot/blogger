### Example #2: Using parameters in column filters

Another example of using parameters is with column filters.

For example, let's say that we need to present a sales table by product groups, but we are interested only in profit by specific customer segments. And we would like to calculate what is the share of that profit in total profit.

Again, we need to:

* create parameter which will be used for selection (in Filter tab) and
* calculation that would contain, column filter formula.

Additionally, one more calculation is needed to calculate profit % of total profit for selected customer segments.

Initial table shows Profit by Product Category.

![Profit by Product Category](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-02-001.png?raw=true)

Now, we need parameter that will be used for column filtering. This parameter is based on the list of values that is populated by using a logical SQL query. This query can be easily obtained if you run a query that displays all values for Customer Segment column and switch to **Developer** mode. Logical SQL query can be found under **Logical SQL** tab.

![Obtaining logical SQL query](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-02-002.png?raw=true)

Logical SQL query needs to be copied into parameter definition. In this example, Initial Value can also be obtained by using same Logical SQL query.

![Create Parameter](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-02-003.png?raw=true)

A new parameter is copied into Filters tab, where selections can be made.

![Parameter in Filter tab](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-02-004.png?raw=true)

To be able to use newly created parameter, a new calculation is created.

![New calculation using column filter](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-02-005.png?raw=true)

And finally, test the results. In the first example, all values (default) are selected, and in the second example, only one customer segment is selected.

![Using parameter in column filters - default](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-02-006.png?raw=true)

![Using parameter in column filters - one customer segment selected](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-02-007.png?raw=true)