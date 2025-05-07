![Oracle Analytics Bootcamp](https://zigavaupot.github.io/blogger/semantic-modeler-series/images/oabootcamp-logo.png)

In Oracle Analytics Semantic Modeler, variables play a critical role in customizing and controlling Analytics behavior at runtime. There are three main types of variables:

- Session Variables
- Global Variables
- Static Variables

A global or session variable's initialization block contains a default initialization query that is run to initialize or refresh the variables defined in the initialization block. The initialization query references the data source's tables that supply the variable values. A query can populate values into several variables, with one variable for each column in the query result.

A static variable's initialization block doesn't contain an initialization query. To define a static variable, you specify the variable name and value directly.

### Session Variables

**Session Variables** are dynamic variables set per user session, typically at login or when a report is run. They help personalize content, enforce security, or pass contextual information into your semantic model or reports. Using session variables reduces the need for redundant report development, as the same report can dynamically adapt to different users or contexts.

Session variables are ideal in the following use cases:

- Row-level data security
- Personalized filtering (e.g., region, department)
- Current user context
- Time-based logic (e.g., user's timezone)

When using **Session Variables** in formulas, they are referenced using the following notation:

```sql
VALUEOF(NQ_SESSION."VARIABLE_NAME")
```

Oracle Analytics provides several built-in session variables, for example:

- `USER`: The logged-in username
- `GROUP`: The user's assigned groups
- `PORTALPATH`: The path of the current dashboard
- `LANGUAGE`: Language preference
- `AUTHENTICATED_USER`: Authenticated username
- `TIMEZONE`: User's timezone setting

In **Semantic Modeler**, navigate to the **Variables** tab in the top-left navigation panel.

![Variables in Navigation Panel](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/variables-navigation.png)

To create a new session variable, click the **plus** next to the **Search** field. This will open a menu with one option: **Create Initialization Block**.

![Create Initialization Block menu](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/create-initialization-block-menu.png)

Upon selection, the **Create Initialization Block** dialog opens.

![Create Initialization Block dialog](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/create-initialization-block-session-dialog.png)

We will create a new **session** variable called *USERS_REGION*, which will use the system session variable *USER* to assign a region to the users. This region can later be used for implicit data filtering, enabling the implementation of row-level security. Pay attention to the **Type**, which is set to *Session*.

All variables are created using an **Initialization Block**. We have created one. Under the **General** tab in the screenshot below, you can see that variables can be refreshed periodically. In our case this is not required, but you might have variables that require frequent refreshing.

Note: Initialization blocks can also be sequenced if dependencies exist between variables. For example, if one variable depends on the value of another, you can order the initialization blocks accordingly.

![Initialization Block - General](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/initialization-block-session-general.png)

The main part of the **Initialization Block** is the **Variables** tab, where we need to provide the SQL statement that will initialize the session variable we want to create.

First, we have created a table called *row-level-security-table* with the following content:

![row-level-security-table](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/row-level-security-table.png)

We want to limit access of a user to a specific region. In the **Variables** tab, we'll provide a SQL query that will use this table to identify which region the current user is entitled to:

```sql
SELECT region_name 
FROM user_regions 
WHERE user_name = 'VALUEOF(NQ_SESSION.USER)'
```

Next, we have to be careful with the **Connection Pool**. It is a best practice to have a separate **Connection Pool** for variables. This helps avoid locking or overloading transactional connection pools, ensuring that variable initialization queries do not interfere with regular reporting queries.

![Connection Pool for variables](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/variables-dedicated-connection-pool.png)

In our case, a second connection pool was created and used:

![Initialization Block - Variables](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/initialization-block-session-variables.png)

Click **Test Query** to test the query:

![Query preview](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/query-preview.png)

We can see that the value *AMERICAS* has been retrieved. We also notice that there is no **Variable Name** defined yet.

To add a new variable, simply click on the **plus** next to the **Search Variables** field:

![Add variable](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/add-variable.png)

... and then define the details for the new variable:

![Variable details](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/variable-details.png)

We have now created a **new session variable** based on another (system) session variable, *USER*, which will help us implement *row-level security* in our analyses and dashboards. We will test this a bit later.

### Global Variables

**Global variables** refer to repository variables that are shared across all users and sessions — effectively acting as dynamically updated global values in your Semantic Model.

Creating **Global variables** follows the same process as we've seen with **Session variables**. We start by **Creating Initialization Block**, but this time we leave **Type** set to *Global*.

![Create initialization block - Global](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/create-initialization-block-global.png)

For example, suppose we need to know and store as a global variable the *First day of business*, which is, let's assume, equal to *MIN(time_bill_dt)* in the *F_REVENUE* table.

```sql
SELECT DISTINCT MIN(time_bill_dt) 
FROM oabootcamp.f_revenue
```

![Create initialization block - Global Variable](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/create-initialization-block-global-variable.png)

### Static Variables

**Static Variables** are, as the name suggests, **constants**. You should use a static variable when you need a variable with a fixed value.

Basically, static variables are a type of global (repository) variable that hold a fixed value — one that doesn’t change unless manually updated by a model developer.

For example, we could define COMPANY_EXCHANGE_RATE_USD_TO_EUR for converting all values in USD to EUR at a fixed company rate defined by the company's finance department.

It is appropriate to use Static Variables when you need to store company-wide constants or values that rarely change, such as fiscal year start dates, standard rates, or other reference values.

We start creating a new **static variable** the same way as any other variable in Semantic Modeler.

![Create initialization block - Static](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/create-initialization-block-static.png)

However, since the value is a constant, there isn't much to define:

![Static variable](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/static-variable.png)

### Using variables in analyses and reports

We have created three variables, each of a different type: **Session**, **Global**, and **Static**.

![Initialization blocks and variables](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/initialization-block-and-variables.png)

Before testing the variables, it is mandatory to **save** your model, **run a consistency check**, and **deploy** it. These steps ensure that your changes are applied and validated in the environment, and that the variables are available for use in analyses and reports.

Let's begin with the following scatter chart that shows countries grouped by region (color) with metrics applied: *Revenue*, *Profit*, and *Profit Margin %*.

![Session Variable Test - 1](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/session-variables-test-1.png)

We can then apply an **Expression Filter** that filters data based on the **Session Variable** value.

![Session Variable Test - 2](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/session-variables-test-2.png)

And finally, only countries from the region defined by the **Session Variable** are shown on the chart.

![Session Variable Test - 3](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/session-variables-test-3.png)

Note: The **Session Variable** is dynamically populated depending on the user logged in. We can now extend this into proper *row-level security* that is not applied at the report level, but at the semantic model level. We will take a look at this a bit later.

Let's check the two other variables that we've created.

We can easily test the **Static Variable** by reshaping the current report into something like this:

![Static Variable Test - 1](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/static-variables-test-1.png)

Then, let's create the following calculation — we want to convert values in USD into EUR using the company exchange rate.

![Static Variable Test - 2](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/static-variables-test-2.png)

![Static Variable Test - 3](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/static-variables-test-3.png)

Now, we have another example to test: the **Global Variable** we created earlier.

We need a simple report to start with:

![Global Variable Test - 1](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/global-variables-test-1.png)

Then we introduce a new expression filter, which filters on date:

![Global Variable Test - 2](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/global-variables-test-2.png)

The active filter results in the following output.

![Global Variable Test - 3](https://zigavaupot.github.io/blogger/semantic-modeler-series/variables/images/global-variables-test-3.png)

This last example doesn't have much business value, however, it demonstrates how we can use session, global (dynamic), and static variables in analyses.

Before we conclude our session on **Variables**, let's take a look at a practical example of how we could use **session variables** in **row-level security** settings in the Semantic Model.

### Summary

We have reviewed the different types of **variables** that can be set in **Semantic Modeler** and used in analyses and reports. These variables are extremely important, especially for enabling row-level security in reports. Without variables, it is not uncommon to see users generate hundreds of duplicated reports just to separate information for specific users. Using session variables allows users to implicitly define and execute data filters in queries, providing a very elegant way of developing a single report for all users.

Additional benefits of using session variables and dynamic filters include:

- **Improved maintenance**: Centralized filters and logic reduce the need for repetitive changes across multiple reports.
- **Better scalability**: As new users, roles, or business rules are introduced, adapting security and personalization is much easier.
- **Enhanced security compliance**: Model-level security ensures consistent enforcement of data access policies and reduces the risk of accidental data leaks.

By leveraging variables and dynamic filtering, Oracle Analytics Semantic Modeler empowers you to build robust, secure, and efficient analytics solutions that scale with your organization’s needs.