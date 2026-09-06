# My Presentation @ Oracle Technology Roundtable, 26th August 2026

![Oracle Analytics & AI presentation at Oracle Technology Roundtable — Oracle Analytics Server, MCP and Oracle Private Agent Factory](https://zigavaupot.github.io/blogger/oracle-tech-roundtable-aug-2026/images/oracle-tech-roundtable-aug-2026.png)

On 26 August 2026 in Ljubljana, I took part in the **Oracle Technology
Roundtable**, where I presented together with my SmartQ colleagues
**Mojca Gros** and **Grega Dvoršak**.

For the event, we prepared a joint presentation titled **"Oracle
Analytics & AI"**, with the subtitle **"Oracle Private Agent Factory in
Oracle Analytics Server."** The session brought together three closely
related topics: the latest Oracle Analytics Server platform, the use of
Model Context Protocol with OAS, and Oracle AI Database Private Agent
Factory.

**[Download the presentation (PDF)](https://zigavaupot.github.io/blogger/oracle-tech-roundtable-aug-2026/slides/SmartQ%20OPAF%2BOAS.pdf)**

## Oracle Analytics & AI

Our presentation was divided into three main parts.

### 1. Oracle Analytics Server (OAS)

The first part focused on **Oracle Analytics Server**, the on-premises
counterpart of Oracle Analytics Cloud. We looked at Oracle Analytics
Server 2026 and discussed the role of business intelligence and data
warehousing as more than just an IT project: BI provides the visible
analytical layer, while the data warehouse provides the trusted data
foundation needed for consistent KPIs, faster analysis and
better-informed decisions.

This part also included a demonstration of **Oracle Analytics Server
2026**.

### 2. Model Context Protocol (MCP) in OAS

The second part moved from traditional analytics toward AI-assisted
analytics and introduced the **Model Context Protocol (MCP)**.

We explained how MCP provides a standard way for AI agents and large
language models to connect to external tools, data and services. In our
OAS example, we showed an **MCP Server Bridge for Oracle Analytics
Server**, allowing AI clients such as Claude, Codex or other LLM-based
applications to discover analytical content, inspect metadata and
execute Logical SQL against OAS.

Because this capability was not available natively in OAS, we
demonstrated an MCP bridge that connected an AI client with Oracle
Analytics Server through its services and semantic layer. The session
included a live demonstration of querying OAS data conversationally
through the MCP server.

### 3. Oracle AI Database Private Agent Factory (OPAF)

My part of the presentation focused on **Oracle AI Database Private
Agent Factory (OPAF)** and on how Oracle was bringing AI-agent
development closer to enterprise data and applications.

I started by introducing OPAF as a **no-code platform for developing,
testing, managing and running AI agents**. We also looked at its
deployment model: because of its container-based architecture, OPAF
could be deployed in the cloud, for example in OCI, or locally inside an
organization's own environment, including isolated or air-gapped
environments. OPAF was provided as an extension around Oracle Database
and required Oracle Database 26ai for capabilities such as Vector
Search.

## A Closer Look at OPAF

After the introduction, I walked through the main building blocks of the
OPAF architecture.

At the center was the **Agent Factory container**, which provided the
no-code user interface, pre-built agents, SQLcl MCP support, Open Agent
Specification, SELECT AI, the Visual Agent Builder and the agent
runtime. The platform could work with different storage and data
services and connect to either local AI services or cloud-based
Generative AI services for LLM and embedding capabilities. Oracle
Database 26ai provided the Agent Factory schema and vector store
underneath the solution.

I also showed the two main ways in which OPAF could be obtained and
deployed: through **Oracle Marketplace** for deployment in OCI, or
through **Oracle Software Delivery Cloud** for a local installation.

### Knowledge Agent

The first practical use case was the **Knowledge Agent**.

I showed how a Knowledge Agent could combine an LLM with enterprise
information to provide contextual answers based on approved knowledge
sources. The underlying process followed the familiar RAG pattern:
documents were loaded and transformed, embeddings were generated and
stored in a vector database, and similarity search was used to retrieve
relevant information before the LLM generated its response.

The important point was that the agent did not have to rely only on the
general knowledge of the LLM. It could retrieve information from
enterprise knowledge bases, documents and other sources, producing
responses that were grounded in the organization's own content and
traceable back to those sources.

### Data Analysis Agent

The second example was the pre-built **Data Analysis Agent**.

This agent was designed to interact directly with databases, understand
schema structures and use LLM capabilities to generate semantic
insights. We looked at how it could analyze the available tables and
views, enrich a user's question, generate SQL, execute it against an
Oracle Database and automatically explore the resulting data.

The example also demonstrated capabilities such as variation analysis,
LLM-supported explanations and automatic generation of visualizations.
It illustrated a different kind of AI interaction: instead of retrieving
knowledge from documents, the agent could reason over structured
enterprise data and help users explore it conversationally.

### Building Custom Agents with Agent Builder

Finally, I moved from the pre-built agents to **Agent Builder**, OPAF's
visual environment for creating custom agents and workflows.

I showed how workflows could combine different components, including
LLMs, agents, MCP servers, REST APIs, conversational memory, chat and
text inputs, file uploads, CSV files, SQL queries and different output
nodes. OPAF also supported multiple LLM options, including local and
cloud-based providers.

The visual approach made it possible to go beyond a single chatbot and
orchestrate more complex, multi-step AI processes by connecting
specialized agents and tools into a workflow. The platform was also
extensible, with the possibility of creating additional custom nodes for
Agent Builder.

I concluded my part of the session with a **live OPAF demonstration**,
showing the platform and a more complex agent workflow built visually in
Agent Builder.

## From Analytics to AI Agents

Taken together, the three parts of our presentation showed a progression
from established enterprise analytics toward agent-based interaction
with enterprise information.

We started with **Oracle Analytics Server** as the governed analytics
platform, extended it through **MCP** so that AI clients could discover
and query analytical data, and then moved to **OPAF**, where AI agents
could work with knowledge, databases, tools and custom workflows in a
controlled enterprise environment.

It was a practical look at how Oracle Analytics, open integration
standards such as MCP, and Oracle's emerging agent platform could come
together to create a new way of interacting with enterprise data.
