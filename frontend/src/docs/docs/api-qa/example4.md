# Example 4: Giving Agents Tools

Equip Agents with Tools to expand their capabilities.

```python
from anote_agents import Agent
from anote_agents.tools import SerperDevTool, ScrapeWebsiteTool

search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()

marketing_agent = Agent(
    name="MarketingAgent",
    role="Marketing Research",
    goal="Research market trends and compile a summary",
    tools=[search_tool],
    verbose=True
)

# Adding a second tool
marketing_agent.tools.append(scrape_tool)
```