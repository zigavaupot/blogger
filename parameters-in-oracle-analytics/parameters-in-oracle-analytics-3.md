### Example #3: Using parameters in Expression Filters and passing values using Data Actions

Let's investigate how to use parameters in Oracle Analytics in Expression Filters and how to pass selected parameters values to other analyses using Data Actions.

But before going into details, let's take a look at the following example. Shipping Costs Analysis by Customer Segment begins with initial analysis.

![Initial analysis](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-03-001.png?raw=true)

Filter on parameter P_CustomerSegment has selected value *Home Office*. More about filters used in this analysis a little bit later. We can see all visualization in the canvas are filtered on selected value. Right-mouse click on any visualizations open a menu where Action Link *To Customer Segment Details* can be selected.

![Use Data Actions to open 2nd Workbook](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-03-002.png?raw=true)

This opens the 2nd workbook with additional details about shipping cost by customer segment. We can now see that selected customer segment parameter from the initial workbook has been passed to the 2nd workbook as parameter where it is applied to filter data.

![Filter the 2nd Workbook based on selected parameter](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-03-003.png?raw=true)

I am aware, that for this example, parameters might not be required, however it shows how parameters can be used to pass values between workbooks.

So what is required?

In the first, initial workbook, we have created:

![Filter bar with parameter selection and expression filter](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-03-004.png?raw=true)

* Parameter with the customer segments list of values (retrieved by using logical SQL query). This parameter is used in Filter bar.

    ![Customer Segments Parameter](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-03-005.png?raw=true)

* Expression filter is added to filter all visualizations in the canvas using selected parameter.

    ![Expression filter](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-03-006.png?raw=true)

There is also requirement to create a new Action Link which will open the 2nd workbook and pass to it selected parameter value.

In the second workbook, a new parameter has to be created (I created identical parameter as I did in the 1st workbook). I also created another expression filter in order to capture passed parameter and filter data based on it. Actually, this filter's definition is also like the one we used in the first workbook:

![Customer Segments Parameter](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-03-007.png?raw=true)

![Expression filter](https://github.com/zigavaupot/blogger/blob/main/parameters-in-oracle-analytics/images/par-03-008.png?raw=true)