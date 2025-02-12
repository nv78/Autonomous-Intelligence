import handler as handler
if __name__ == "__main__":
    # Initialize the CalendarAgent
    calendar_agent = handler.CalendarAgent()

    # Schedule an event
    result = calendar_agent.schedule_event(
        task_description="Project Kickoff Meeting",
        start_time="2025-03-12T08:00:00",
        duration_hours=2,
        time_zone="America/New_York"
    )
    print(result)