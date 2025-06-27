# Use Case: Financial Analysis

Use the SDK to gather real-time market data, analyze stock trends, and provide human-readable summaries.

```python
from anote_agents import Agent, Crew
from anote_agents.tools import DuckDuckGo, YFinanceTools

# Web research Agent
web_agent = Agent(
    name="WebAgent",
    role="Search Market News",
    tools=[DuckDuckGo()],
    instructions=["Always cite your sources"]
)

# Finance data Agent
finance_agent = Agent(
    name="FinanceAgent",
    role="Analyze Stock Data",
    tools=[YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True)],
    instructions=["Use tables where possible"]
)

analysis_crew = Crew(
    agents=[web_agent, finance_agent],
    tasks=[],
    verbose=True
)

# Hypothetical user input
user_input = {
    "query": "Please analyze NVDA stock performance and summarize latest news."
}

result = analysis_crew.kickoff(inputs=user_input)
print("Analysis result:", result)
Example Flow

WebAgent retrieves relevant news articles (via DuckDuckGo).
FinanceAgent fetches real-time stock data (via YFinanceTools).
The Crew compiles the final summarized report.