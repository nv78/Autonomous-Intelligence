# Use Case: Event Coordination

Coordinate and manage an event by assigning specialized tasks to different Agents.

```python
from anote_agents import Agent, Crew, Task
from anote_agents.tools import SerperDevTool, ScrapeWebsiteTool

search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()

venue_coordinator = Agent(
    role="Venue Coordinator",
    goal="Find and book a venue that meets event requirements",
    tools=[search_tool, scrape_tool],
    verbose=True
)

logistics_manager = Agent(
    role="Logistics Manager",
    goal="Handle catering, equipment, and attendee logistics",
    tools=[],
    verbose=True
)

marketing_agent = Agent(
    role="Marketing Agent",
    goal="Promote the event to potential attendees",
    tools=[search_tool],
    verbose=True
)

venue_task = Task(
    description="Find a venue in {event_city} for {expected_participants} participants.",
    expected_output="Venue details including cost, location, capacity.",
    agent=venue_coordinator
)

logistics_task = Task(
    description="Organize catering and equipment for {expected_participants} participants.",
    expected_output="Menu options, equipment list, and cost breakdown.",
    agent=logistics_manager
)

marketing_task = Task(
    description="Generate marketing strategy to attract {expected_participants} participants for the {event_topic}.",
    expected_output="A concise marketing plan including channels, budget, and timeline.",
    agent=marketing_agent
)

event_crew = Crew(
    agents=[venue_coordinator, logistics_manager, marketing_agent],
    tasks=[venue_task, logistics_task, marketing_task],
    verbose=True
)

event_details = {
    "event_city": "Los Angeles",
    "event_topic": "AI Conference",
    "expected_participants": 300
}

result = event_crew.kickoff(inputs=event_details)
print(result)
Overview

Each Agent handles a unique segment of event planning.
The tasks can be executed in parallel or sequentially, depending on the workflow configuration.