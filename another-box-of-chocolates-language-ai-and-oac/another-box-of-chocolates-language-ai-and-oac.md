![OCI Language AI and Oracle Analytics](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/language-ai-and-oac.png)

I have been writing about [OCI Vision services](https://zigavaupot.blogspot.com/2022/08/oracle-ai-vision-just-like-box-of.html) and [integration between OCI Vision to Oracle Analytics](https://zigavaupot.blogspot.com/2022/09/using-ai-vision-model-for-image.html)in previous blog posts and how these services can integrate and be used with Oracle Analytics Cloud. In the meantime Oracle has released the Oracle Analytics January 2023 release, which comes with an option to integrate OAC with another OCI AI service, Language.

In this blog post I am focusing on the integration between OAC and OCI Language service. This means, I am not focusing on the training of a custom model, but I am using pre-trained model available within OCI Language service.
Assuming that model already exists, connecting OAC instance to OCI Language has to follow the following steps:

* OCI Language requires storage to store temporary results. This is why, a staging bucket is created in Object Storage.
* In order to access OCI Language service and to access staging bucket OAC users require few policies that needs to be set.
* When all policies are set, connection between OAC and OCI Resource, in this case OCI Language, can be established.
* If connection is valid, register OCI Language model (in this case the generic one) with OAC.
* Data Flow is then used to apply OCI Language model to perform, for example sentiment analysis, on the textual dataset. A new dataset with prediction data is created as a result of running data flow.
* Finally, a new dataset can be used in visualizations.

Before you begin using OCI Language with OAC, you need to find proper dataset with textual data. I am using a subset of 15k rows from Madrid_reviews.csv dataset which is part of [Six TripAdvisor Datasets for NLP Tasks on Kaggle](https://www.kaggle.com/datasets/inigolopezrioboo/a-tripadvisor-dataset-for-nlp-tasks).

But let's talk about OCI Language first.

## OCI Language

OCI Language is one of OCI AI services accessible using Console, REST API, SDK and CLI. Users have an opportunity to use pre-trained model as well as their own, custom model to process unstructured textual data and extract insights. All that the same way as they are able to do using OCI Vision, without any machine learning experience and knowledge. Practically self-service.

In this blog, I am focusing on pre-trained models, which are frequently retrained by Oracle. Using pre-trained model, users can access the following capabilities:

* language detection,
* text classification,
* named entity recognition,
* key phrase extraction,
* sentiment analysis,
* text translation.

![OCI Language AI services](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/oci-language-ai-service.png)

When working with all models (not just pre-trained, but custom also) you have to understand that the best results are achieved when using English. There is no auto-correction for misspelling.You might also find some other rules and constraints, which are described in more details in OCI Language documentation.

Let’s take a look at an example of a hotel review. For example, we would like to analyze the following restaurant review:

*The menu of Yakuza is a bit of a lottery, some plates are really good (like most of the sushi rolls) and instead some others are terrible ( the pizza sushi and most of the fried starters). Taking this in consideration, it´s a great option if you feel like sushi and can avoid ordering from the rest of the menu. We even ordered for delivery more than once and the packaging they use is great., Dec 10, 2019.*

If you navigate to **text analytics** in **Language** console, simply copy the text from above in text box field.

![Analyze text](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/analyze-text-in-console.png)

On **Analyze**, text analysis in a generic language model is performed automatically and results are displayed.

![Results of text analysis](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/results-of-text-analysis-1.png)

**Sentiment analysis** is performed on document, on aspect (word) and on sentence level. Sentiment (positive, neutral, mixed, negative) is easily detectable using color coding.

![Results of text analysis](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/results-of-text-analysis-2.png)

In the last results section, **Personal identifiable information** (PII) is displayed. For any PII, users can configure masking. In text example above, there aren't any PII, hence text has not been affected.

![Results of text analysis](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/results-of-text-analysis-3.png)

In our example little further on this blog post, generic language model is used to integrate it with Oracle Analytics where bulk sentiment analysis is performed.

## Bringing Language and Analytics together

### Setting some prerequisites

Before you can use AI Language service, users require some policies to be set for them. For example, the following policy needs to be set:

```text
allow group <group-name> to use ai-service-language-family in tenancy
```

![Policy to allow user group to use AI Language Service](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/allow-user-group-use-ai-language.png)

And there is another prerequisite: Language requires a staging bucket for storing temporary results. This bucket needs to be created and policies for managing it have to granted to the user group which is using Language service.

![Staging bucket for AI Language Service](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/staging-bucket-for-language.png)

```text
allow group <group_in_tenancy> to read objectstorage-namespaces in compartment <compartment>
allow group <group_in_tenancy> to read buckets in compartment <compartment>
allow group <group_in_tenancy> to manage objects in compartment <compartment> where target.bucket.name='<staging_bucket_name>'
```

![Policy to allow user group to use and manage staging bucket](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/policies-for-staging-bucket.png)

### Establishing a connection to Language from Analytics

Connecting from Analytics to Language is same as for Vision. When defining a new connection, **OCI Resource** connection type is available in Analytics. What is needed is some parameters from OCI environment and information for the user connecting to OCI resource.

![Creating connection to OCI Resource](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/oci-resource-connection.png)

Based on valid connection generic language model can be registered with Analytics.

![Register Language Model](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/register-language-model-menu.png)

And then, users can choose between several pre-trained models. For example, sentiment analysis.

![Select pre-trained sentiment analysis model](https://zigavaupot.github.io/blogger/images/another-box-of-chocolates-language-ai-and-oac/select-sentiment-analysis.png)

### Deploying model for Sentiment Analysis

When the model is registered with Analytics, pre-trained sentiment analysis (in the case described) language model can be used for sentiment analysis in Data Flows.

Data flow itself is pretty straight forward. As any other activity within Analytics, it is designed to be used by any slightly advanced user, as it is easy to use, quite intuitive and consists of only 3 steps:

* Read restaurant review dataset.
* Apply language model on provided dataset.
* Store results into a new dataset.

![Apply Language model for Sentiment Analysis](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/apply-ai-model.png)

Based on the selection in the 2nd, Apply AI Model, sentiment analysis is performed on different sentiment levels:

* Aspect (individual word),
* Sentence,
* Both, Aspect and Sentence

![Sentiment Analysis Levels](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/sentiment-analysis-levels.png).

Based on this selection, result of different granularity are generated. In any case, sentiment analysis for the document level (in our case, restaurant review) is performed.

Results of the sentiment analysis are already visible, like a preview, in a data flow, where Sentiment is calculated, based on Positive Score, Negative Score, Neutral Score and Mixed Score metrics. Depending on which of the score metrics is the highest, sentiment is determined.

### Visualizing Sentiment Analysis

Once a new sentiment analysis dataset is created, it can be instantly used in a new Analytics workbook.

For example, number of reviews by sentiment by restaurant can lead to detailed analysis of each given review.

![Sentiment Analysis Workbook](https://zigavaupot.github.io/blogger/another-box-of-chocolates-language-ai-and-oac/images/trip-advisor-sentiment-analysis-workbook.png).

## Conclusion

In this short example, we can see (again) how easy is to use machine learning services within Oracle Cloud Infrastructure. Just like Vision, Language service is really easy to use as a stand-alone service. To analyze text, users don't have to be data scientist. What they need is just a couple of clicks and of course basic understanding of AI service they are using.

And on top of it, this short example also demonstrates how easy is to connect Analytics to Language service. The only technical stuff is to set policies and create connection between the two OCI services. But once these are done (usually by OCI administrator), then users can take it from there and deploy their data and visualize it in Analytics. Just like any other dataset they might use in their analyses. Or as the title suggest: Just another box of chocolates.