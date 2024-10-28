# Using SELECT AI with RAG

In my two previous blog posts [Talking to Oracle Database in plain English](https://zigavaupot.blogspot.com/2023/12/talking-to-oracle-database.html) and [Talking to Oracle Database, this time in plain Slovenian](https://zigavaupot.blogspot.com/2023/12/talking-to-oracle-database-slovenian.html) I have been playing with **Select AI** in **Oracle 23ai** database.

In these two blog posts I tested how **Oracle 23ai** feature called **Select AI** provides SQL access to generative AI using Large Language Models to generate SQL query which is then executed in database.

In this blog post I am testing an option to use **Select AI** for **Retrieval-Augmented Generation** (RAG).

Select AI with RAG augments natural language prompt by retrieving data (documents) from **vector store** (stored in **Oracle 23ai**). With this additional content, hallucinations can be reduced and much more accurate answers could be retrieved.

**Select AI** is using **Oracle 23ai AI Vector Search** for similarity search using vector embeddings.

To set the environment for **Select AI with RAG** two main tasks needs to be performed:
* Set up **Vector Store** in **Object Storage** and
* Create **Vector Index**.

### Set up Vector Store

I have set my Vector store in OCI Object Storage. For this I am using *rag-mini-wikipedia* dataset I found on [Hugging Face datasets](https://huggingface.co/datasets/rag-datasets/rag-mini-wikipedia) page.

Dataset consist of 100+ text files which I uploaded to my Object Storage.

![Upload data files to Object Storage](https://github.com/zigavaupot/blogger/blob/main/select-ai-and-rag/images/object-storage.png?raw=true)

In my example, I am using OpenAI for my LLM. Oracle allows other LLMs as well, and process for setting them up is practically identical.

First, we need to make sure that database allows HTTP connection to OpenAI API endpoint. For example, I am using database user OML_USER to access api.open.com.

Database administrator (ADMIN) needs to run the following code (i.e. SQL Developer):

```console
DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
        host => 'api.openai.com',
        ace  => xs$ace_type(privilege_list => xs$name_list('http'),
        principal_name => 'OML_USER',
        principal_type => xs_acl.ptype_db)
    );
END;
```

We also need to create credentials to connect to OpenAI. All next steps are executed in Zeppelin notebook (included with Oracle 23ai):

![Create credential](https://github.com/zigavaupot/blogger/blob/main/select-ai-and-rag/images/create-credential.png?raw=true)

```console
%script

begin
    dbms_cloud.create_credential (
        credential_name  => 'OPENAI_CRED35',
        username         => 'OPENAI',
        password         => '******************'
        );
exception
    when others then
        dbms_output.put_line(sqlerrm);
end;
```

Then creadential to connect to OCI Object Storage needs to be set:

![Create OCI credential](https://github.com/zigavaupot/blogger/blob/main/select-ai-and-rag/images/create-oci-credential.png?raw=true)

```console
%script

 BEGIN

    DBMS_CLOUD.DROP_CREDENTIAL('OCI_CRED');

    DBMS_CLOUD.CREATE_CREDENTIAL(
        credential_name => 'OCI_CRED',
        username => '**********************',
        password => '*************'
    );
END;
```

Make sure that username includes also identity domain as prefix: `identity_domain/username`.

In the next step, a new AI profile needs to be created:

![Create profile with Vector index](https://github.com/zigavaupot/blogger/blob/main/select-ai-and-rag/images/create-profile.png?raw=true)

With *create profile* vector index is specified:

```console
%script

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
end;
```

We can now create a new vector index using files stored in OCI Object Storage.

![Create a new vector index](https://github.com/zigavaupot/blogger/blob/main/select-ai-and-rag/images/create-vector-index.png?raw=true)

```console
%script

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
```

After a new vector index is created, the last step - set the new profile active.

![Set profile](https://github.com/zigavaupot/blogger/blob/main/select-ai-and-rag/images/set-profile.png?raw=true)

Let's test:

