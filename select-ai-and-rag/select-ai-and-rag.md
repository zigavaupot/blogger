# Using SELECT AI with RAG

In my two previous blog posts, [Talking to Oracle Database in plain English](https://zigavaupot.blogspot.com/2023/12/talking-to-oracle-database.html) and [Talking to Oracle Database, this time in plain Slovenian](https://zigavaupot.blogspot.com/2023/12/talking-to-oracle-database-slovenian.html), I explored **Select AI** within the **Oracle 23ai** database.

In those posts, I tested how the **Oracle 23ai** feature called **Select AI** enables SQL access to generative AI by using Large Language Models (LLMs) to generate SQL queries that are then executed in the database.

In this post, I will focus on using **Select AI** for **Retrieval-Augmented Generation** (RAG), a powerful approach that enhances natural language prompts by retrieving relevant documents from a **vector store** maintained within **Oracle 23ai**. This augmentation helps reduce hallucinations and provides more accurate, evidence-backed answers.

---

## What is Select AI with RAG?

Select AI with RAG combines the power of generative AI with vector search capabilities. It uses **Oracle 23ai AI Vector Search** to perform similarity searches based on vector embeddings, retrieving relevant documents that enrich the prompt before generating a response.

To set up **Select AI with RAG**, two main tasks are required:

- Setting up a **Vector Store** in **OCI Object Storage**
- Creating a **Vector Index** in the database

---

## Setting Up the Vector Store

For my example, I used the *rag-mini-wikipedia* dataset from [Hugging Face datasets](https://huggingface.co/datasets/rag-datasets/rag-mini-wikipedia). This dataset consists of over 100 text files, which I uploaded to my OCI Object Storage bucket.

![Upload data files to Object Storage](https://zigavaupot.github.io/blogger/select-ai-and-rag/images/object-storage.png)

---

## Configuring Access to OpenAI API and OCI Object Storage

In this example, I use OpenAI as my LLM provider. Oracle 23ai supports other LLMs as well, and the setup process is very similar.

First, ensure that the database user (e.g., `OML_USER`) has HTTP access to the OpenAI API endpoint (`api.openai.com`). A database administrator (ADMIN) needs to run the following code in SQL Developer:

```script
DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
        host => 'api.openai.com',
        ace  => xs$ace_type(privilege_list => xs$name_list('http'),
        principal_name => 'OML_USER',
        principal_type => xs_acl.ptype_db)
    );
```

Next, create credentials to connect to OpenAI and OCI Object Storage. These steps are performed in a Zeppelin notebook included with Oracle 23ai:

![Create credential](https://zigavaupot.github.io/blogger/select-ai-and-rag/images/create-credential.png)

Then, create the credential for OCI Object Storage access:

![Create OCI credential](https://zigavaupot.github.io/blogger/select-ai-and-rag/images/create-oci-credential.png)

**Note:** Make sure the username includes the identity domain as a prefix, for example: `identity_domain/username`.

---

## Creating an AI Profile and Vector Index

After setting up credentials, create a new AI profile that specifies the vector index to be used:

![Create profile with Vector index](https://zigavaupot.github.io/blogger/select-ai-and-rag/images/create-profile.png)

Next, create the vector index using the files stored in OCI Object Storage:

![Create a new vector index](https://zigavaupot.github.io/blogger/select-ai-and-rag/images/create-vector-index.png)

Finally, activate the new profile:

![Set profile](https://zigavaupot.github.io/blogger/select-ai-and-rag/images/set-profile.png)

---

## Testing with Real Queries

One of the text files I uploaded contains information about kangaroos. Let's ask: *How long does a kangaroo live?*

![How long does kangaroo live?](https://zigavaupot.github.io/blogger/select-ai-and-rag/images/question-kangaroo.png)

The response includes two parts:

- The generated answer: *The average life expectancy of a kangaroo is about 4-6 years. However, in captivity, kangaroos may live as long as 20 years.*
- A reference to the source file containing the information: *Sources: - files/S08_set1_a1.txt.txt (https://swiftobjectstorage.eu-frankfurt-1.oraclecloud.com/v1/frllu0v1kplh/select-ai-rag-data/files/S08_set1_a1.txt.txt)*

Another example is a question about Gustav Klimt, the famous Austrian painter:

![Gustav Klimt?](https://zigavaupot.github.io/blogger/select-ai-and-rag/images/question-klimt.png)

This response is more complex. The embedding model identified **more than one** relevant document (five in total) to augment the prompt *tell me about Gustav Klimt*.

The image below shows the same response in a table format, including the generated answer, source files used for prompt augmentation, and their respective similarity scores. The higher the score, the greater the influence of that document on the response.

![Gustav Klimt?](https://zigavaupot.github.io/blogger/select-ai-and-rag/images/question-klimt-table.png)

---

## Conclusion

This example demonstrates how straightforward it is to set up an object store and enable Retrieval-Augmented Generation using vector indexes in Oracle 23ai. By integrating a vector store with Select AI, you can enrich your PL/SQL database with GenAI capabilities, allowing it to provide accurate, context-aware answers supported by relevant source documents.

With just a few steps, you can leverage popular Large Language Models, register them with Oracle 23ai, and create powerful AI-driven applications that go beyond simple question answering. In future posts, I will explore how these techniques perform with non-English texts and more complex datasets.

---

## Notebook Script

```script
%script

BEGIN
    DBMS_CLOUD.CREATE_CREDENTIAL(
        credential_name  => 'OPENAI_CRED35',
        username         => 'OPENAI',
        password         => '******************'
        );
EXCEPTION
    WHEN others THEN
        DBMS_OUTPUT.PUL_LINE(sqlerrm);
END;

BEGIN
    DBMS_CLOUD.DROP_CREDENTIAL('OCI_CRED');
    DBMS_CLOUD.CREATE_CREDENTIAL(
        credential_name => 'OCI_CRED',
        username => '**********************',
        password => '*************'
    );
END;

BEGIN
    DBMS_CLOUD_AI.DROP_PROFILE('OPENAI_ORACLE');
    DBMS_CLOUD_AI.CREATE_PROFILE(
        profile_name =>'OPENAI_ORACLE',
        attributes   =>'{"provider": "openai",
        "credential_name": "OPENAI_CRED",
        "vector_index_name": "RAG_DEMO_IDX",
        "temperature": 0.2,
        "max_tokens": 4096,
        "model": "gpt-3.5-turbo-1106"
    }');
END;

BEGIN
    DBMS_CLOUD_AI.CREATE_VECTOR_INDEX(
         index_name  => 'RAG_DEMO_IDX',
         attributes  => '{"vector_db_provider": "oracle",
                          "location": "https://swiftobjectstorage.eu-frankfurt-1.oraclecloud.com/v1/<namespace>/select-ai-rag-data",
                          "object_storage_credential_name": "OCI_CRED",
                          "profile_name": "OPENAI_ORACLE",
                          "vector_dimension": 1536,
                          "vector_distance_metric": "cosine",
                          "chunk_overlap":128,
                          "chunk_size":1024
    }');
END;

BEGIN
    DBMS_CLOUD_AI.SET_PROFILE(
        profile_name => 'OPENAI_ORACLE'
    );
END;
```
