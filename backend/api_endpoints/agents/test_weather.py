import handler as handler
if __name__ == "__main__":
    weather_agent = handler.WeatherAgent()
    result = weather_agent.fetch_weather("Ithaca")
    print(result)