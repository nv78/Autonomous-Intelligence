
# Tools

Tools extend the capabilities of an Agent, allowing it to perform specialized actions—like web searches, website scraping, or data lookups.

::: fsdk.anote-sdk.Tools
    <!-- options:
        show_source: false -->

### Tools Fields
- **tool_name**: Identifier for the Tool (e.g., `"ScrapeWebsiteTool"`).
- **config**: Configuration details (e.g., API keys, search parameters) (optional).

Example:

``` python
from anote_agents import Agent

# Agent referencing two tools by name
agent_with_tools = Agent(
    name="ResearchAgent",
    model="gpt3.5turbo",
    system_prompt="You are skilled at finding online resources.",
    tools=["SerperDevTool", "ScrapeWebsiteTool"],
    verbose=False
)
```

Tools They act as plugins or external functions the Agent can call.

Example 2:
```python
from anote_agents.tools import SerperDevTool

search_tool = SerperDevTool()
# Provides web search functionality
# Typically requires an API key or developer token
```

1.2 ScrapeWebsiteTool
```python

from anote_agents.tools import ScrapeWebsiteTool

scrape_tool = ScrapeWebsiteTool()
# Allows Agents to fetch and parse HTML from websites
# Assigning Tools to Agents

venue_coordinator.tools = [search_tool, scrape_tool]
```

#### Building Custom Tools
You can implement custom Tools (e.g., database queries, Slack bot actions) by extending a base Tool class and overriding a run() method. This approach unifies external integrations under a single interface.