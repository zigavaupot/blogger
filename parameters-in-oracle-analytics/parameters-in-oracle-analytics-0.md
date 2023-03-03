# Parameters in Oracle Analytics

The use of parameters in OBIEE (the predecessor of Oracle Analytics Cloud) is a feature that made it possible to add session personalization to the user experience. This feature has been missing in Data Visualisation workbooks until now. The March 2023 Oracle Analytics Cloud  update has a few product updates but the most prominent new feature of this update  is undoubtedly the introduction of parameters to Data Visualisation workbooks.

### About Variables in Oracle Business Intelligence (OBIEE)

We’ll start things off by taking a look at what functionality existed in OBIEE. There are several variable types that could be used to pass static or dynamic values.

* Session Variables are assigned a value when the user signs in to Oracle Analytics and their values persist for the duration of the user session.. There are 2 types of Session Variables:
    * System Session Variables - These are used by the Oracle BI Server and the Oracle BI PresentationServices for internal purposes.
    *  Non-System Session Variables - These can be created in the semantic model
* Presentation Variables - These variables are typically defined in the “front end”.
* Repository Variables - these are also available in the semantic model and can only have a single value at any given time.
    * Static - The static value is defined and doesn’t change
    * Dynamic - These derive their value at runtime from the results of a SQL query defined in a construct called an initialisation block.
* Request Variable - This variable enables the value of a session variable to be overridden.
* Global Variables - Similar to the Presentation Variable in that this variable is created in the “front end” and can be used to store the results of an intermediate calculation step for example.

# Using Parameters in Oracle Analytics

Let’s start off with a look back at the equivalent OBIEE feature. The parameters functionality that has been incorporated into Oracle Analytics Cloud matches with the Presentation Variables functionality described above that have been available in OBIEE.

There is now a new tab in the workbook editor in which you can find the parameters. Repository variables are also accessible in the new parameters tab in addition to parameters created in the workbook screen..

The syntax used to reference a parameter is:

```code
@parameter("parameter name")(default value)
```

If the parameter has a text data type then the default value should be within single quotes. The name of the parameter (parameter name) should always be within double quotes.