![Oracle Analytics AI Assistant and AI Agents](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-assistant-and-agents.png)

## Oracle Analytics Meets AI: From Workbook Assistant to AI Agents

In my previous blog post, I was discussing the use of Ask BI in Oracle Analytics. Ask BI brings a conversational experience to search. The next step is to bring that experience closer to the analytical work itself - inside a workbook, and eventually as a reusable, purpose-built assistant.

Oracle Analytics offers both an **AI Assistant** and **AI Agents**. They share the same basic goal: help users ask questions of governed data in natural language. The difference is in where they live and how much context they can carry.

The AI Assistant is embedded in a workbook. An AI Agent is a standalone object that can be configured with data, instructions, and knowledge documents. That distinction is useful because not every analytical conversation needs the same level of specialization.

### The AI Assistant: conversational analysis in a workbook

The AI Assistant is embedded directly in a workbook, which makes it feel like an extension of the normal analysis experience rather than a separate tool. It gives users a chat interface for asking questions and talking to the data that is already available in the workbook. The underlying data can be any dataset, including a Subject Area, so the conversation stays tied to the analytical context already in use.

Before using it, there is one configuration point worth mentioning. At the moment, the Assistant uses the internal Oracle Analytics GenAI service. The expectation is that other LLM options will become available over time, but in the current experience this is not something the workbook author selects while building the analysis.

To start working with the Assistant, open a workbook and click the **Auto Insights** icon. From there, select **Assistant**. This opens the chat experience where you can ask a question in natural language and receive an analytical response based on the workbook data.

![AI Assistant embedded in a workbook](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-assistant-in-workbook.png)

In **Visualize (Edit) mode**, the process is quite practical:

1. Ask the Assistant a question about the workbook data.
2. Review the visualization it generates.
3. Insert the generated visualization onto any canvas in the workbook.
4. Continue refining it with the normal workbook authoring tools.

The useful part is that the output does not have to stay in the chat. Any visualization produced by the Assistant can be inserted onto a workbook canvas. From that point onward, it becomes part of the normal workbook design process.

![Insert an AI Assistant visualization into the workbook canvas](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-assistant-insert-visualization.png)

The generated visualization can then be adjusted with simple authoring tools. You can change the visualization type, switch the axis assignment, and add or remove attributes. This is an important design principle: AI accelerates the first draft, while the analyst retains control over the final analytical product.

![Refining an AI-generated visualization](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-assistant-edit-visualization.png)

### Making the Assistant available in Present mode

There is one detail that is easy to miss: the AI Assistant is not enabled by default in **Present mode**. To make it available to workbook consumers, switch to Present mode and turn on the Insights panel. The Auto Insights icon then becomes available and users can work with the Assistant even if they do not have Edit privileges.

![Enable the Insights panel in Present mode](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-assistant-present-mode-insights-panel.png)

This makes a workbook more than a curated collection of pages and filters. Users can still consume the designed experience, but they can also ask a question that the original author did not anticipate. It is a practical way to combine governed, reusable reporting with a degree of self-service exploration.

![AI Assistant active in workbook Present mode](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-assistant-present-mode-active.png)

### AI Agents: add focused context to the conversation

AI Agents have similar analytical capabilities, but they are not embedded in one workbook. They are standalone objects designed for a more specific domain or task.

When creating an Agent, first add the data it should use. This can be a dataset; Oracle recommends using Local Subject Areas rather than Subject Areas where possible. The key difference is that an Agent can also be given two additional forms of context:

- **Supplemental instructions** tell the Agent how to behave, which definitions to follow, and how to structure its answers.
- **Knowledge documents** provide information that may not be contained in the analytical model: business definitions, policies, process descriptions, or supporting documentation.

![Add data and configure an AI Agent](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-agent-add-data.png)

Supplemental instructions are where a generic assistant can become a useful business assistant. For example, an HR analytics Agent could be instructed to explain attrition metrics in business terms, use the organization’s agreed definition of voluntary attrition, and always call out the population and time period used in an answer.

![Supplemental instructions for an AI Agent](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-agent-supplemental-instructions.png)

The first message is another small but thoughtful touch. It gives the Agent an appropriate opening prompt, helping users understand what it is for and how to begin the conversation.

![Set the AI Agent first message](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-agent-first-message.png)

Knowledge documents complete the picture. A data model may tell the Agent that a measure is called `Attrition Rate`; a policy document can explain the official definition, exclusions, and the actions a manager should consider. Combining both types of context makes the Agent’s responses more useful and better aligned with the organization.

![Attach knowledge documents to an AI Agent](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-agent-knowledge-documents.png)

### Use an Agent in a workbook when accuracy needs more context

Agents can also be used from a workbook in Present mode. In that situation, the workbook assistant can use either the indexed dataset or an attached AI Agent.

Why choose the Agent? A plain Assistant can answer a question from the data that is available to it, but it may lack the context needed to interpret that answer correctly. An attached Agent brings its instructions and knowledge documents into the interaction, so it can produce an answer that follows the organization’s definitions and expectations more closely.

![AI Assistant answer in a workbook](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-agent-workbook-assistant-answer.png)

![AI Agent providing a more contextual answer in Present mode](https://zigavaupot.github.io/blogger/oracle-analytics-meets-ai/ai-agents/images/ai-agent-workbook-present-mode.png)

This should not be read as an argument to create an Agent for every dataset. The Assistant is ideal for quick, in-context exploration. An Agent is the better fit when the subject needs durable guidance, non-data documentation, or a consistent style of response across many users and workbooks.

### Choosing the right tool

Use the **AI Assistant** when the goal is to explore a workbook quickly, create a first visualization, or let consumers ask follow-up questions about the content they are viewing. Use an **AI Agent** when the conversation needs a defined role, additional business guidance, or supporting knowledge beyond the model itself.

Together, they offer a useful progression. Start with a workbook conversation when the question is immediate. Build an Agent when the same kind of conversation needs to become a reusable, governed capability for a wider audience. In both cases, the quality of the experience still depends on the foundations: understandable data, reliable definitions, and carefully chosen context.
