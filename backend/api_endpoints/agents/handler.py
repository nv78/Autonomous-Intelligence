from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google_auth_oauthlib.flow import Flow
from flask import session
from googleapiclient.discovery import build
import os
import pickle
import webbrowser
import requests
import os
from dotenv import load_dotenv
import re
from google.oauth2.credentials import Credentials


load_dotenv()
SCOPES = ["https://www.googleapis.com/auth/calendar"]
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def execute_task(agent, task_description, start_time, location, company_symbol, duration_hours=1, time_zone="UTC"):
    """
    Routes the task to the correct agent based on its function.
    """
    if "calendar" in agent["task"].lower():
        return CalendarAgent().schedule_event(task_description, start_time, duration_hours, time_zone)

    if "weather" in agent["task"].lower():
        return WeatherAgent().fetch_weather(location)

    if "stock" in agent["task"].lower():
        return StockMarketAgent().fetch_stock_price(company_symbol)

    return {"error": "Task type not recognized"}

def extract_meeting_details(text):
    """
    Extracts meeting details from structured meeting notes.
    """
    meetings = []
    meeting_pattern = re.compile(r"(?P<title>[\w\s]+)\s*-\s*(?P<time>\d{1,2}:\d{2} (AM|PM) on \w+ \d{1,2}, \d{4})", re.IGNORECASE)

    matches = meeting_pattern.findall(text)
    for match in matches:
        title = match[0].strip()
        time_str = match[1]

        # Convert to ISO 8601 format
        start_time = datetime.strptime(time_str, "%I:%M %p on %B %d, %Y").isoformat()

        meetings.append({
            "title": title,
            "start_time": start_time
        })

    return meetings

# class CalendarAgent:
#     def __init__(self):
#         """Initialize the Google Calendar API Client."""
#         self.service = None
#         self.load_credentials()

#     def load_credentials(self):
#         """Loads credentials from session (for authenticated users)."""
#         credentials = session.get("google_credentials")
#         if credentials:
#             self.service = build("calendar", "v3", credentials=credentials)

#     def schedule_event(self, task_description, start_time, duration_hours, time_zone):
#         """Schedules an event in the authenticated user's Google Calendar."""
#         if not self.service:
#             return {"error": "User is not authenticated. Please login first."}

#         try:
#             end_time = (datetime.fromisoformat(start_time) + timedelta(hours=duration_hours)).isoformat()
#             event_details = {
#                 "summary": task_description,
#                 "start": {"dateTime": start_time, "timeZone": time_zone},
#                 "end": {"dateTime": end_time, "timeZone": time_zone},
#             }
#             event = self.service.events().insert(calendarId="primary", body=event_details).execute()
#             return {"message": f"Scheduled event: {task_description}", "eventDetails": event}
#         except Exception as e:
#             return {"error": f"Failed to schedule event: {str(e)}"}
# class CalendarAgent:
#     def __init__(self):
#         """Initialize the Google Calendar API Client."""
#         self.service = None
#         self.load_credentials()

#     # def load_credentials(self):
#     #     """Loads credentials from session (for authenticated users)."""
#     #     credentials_dict = session.get("google_credentials")
#     #     if credentials_dict:
#     #         creds = Credentials.from_authorized_user_info(credentials_dict)
#     #         self.service = build("calendar", "v3", credentials=creds)
#     def load_credentials(self):
    
#         credentials_dict = session.get("google_credentials")
        
#         # Debugging: Check if credentials exist
#         print("🔍 Stored session credentials:", credentials_dict)
        
#         if credentials_dict:
#             creds = Credentials.from_authorized_user_info(credentials_dict)
#             self.service = build("calendar", "v3", credentials=creds)

#     def schedule_event(self, task_description, start_time, duration_hours, time_zone):
#         """Schedules an event in the authenticated user's Google Calendar."""
#         if not self.service:
#             return {"error": "User is not authenticated. Please login first."}

#         try:
#             end_time = (datetime.fromisoformat(start_time) + timedelta(hours=duration_hours)).isoformat()
#             event_details = {
#                 "summary": task_description,
#                 "start": {"dateTime": start_time, "timeZone": time_zone},
#                 "end": {"dateTime": end_time, "timeZone": time_zone},
#             }
#             event = self.service.events().insert(calendarId="primary", body=event_details).execute()
#             return {"message": f"Scheduled event: {task_description}", "eventDetails": event}
#         except Exception as e:
#             return {"error": f"Failed to schedule event: {str(e)}"}

class CalendarAgent:
    def __init__(self, credentials=None):
        """Initialize the Google Calendar API Client."""
        if credentials:
            self.credentials = credentials
        else:
            self.credentials = None  # Will be assigned later
        
        self.service = self.load_credentials()

    def load_credentials(self):
        """Loads credentials (either from session or stored instance)."""
        if self.credentials:
            return build("calendar", "v3", credentials=self.credentials)
        else:
            print("⚠️ No credentials found!")
            return None

    def schedule_event(self, task_description, start_time, duration_hours, time_zone):
        """Schedules an event in the authenticated user's Google Calendar."""
        if not self.service:
            return {"error": "User is not authenticated. Please login first."}

        try:
            end_time = (datetime.fromisoformat(start_time) + timedelta(hours=duration_hours)).isoformat()
            event_details = {
                "summary": task_description,
                "start": {"dateTime": start_time, "timeZone": time_zone},
                "end": {"dateTime": end_time, "timeZone": time_zone},
            }
            event = self.service.events().insert(calendarId="primary", body=event_details).execute()
            return {"message": f"Scheduled event: {task_description}", "eventDetails": event}
        except Exception as e:
            return {"error": f"Failed to schedule event: {str(e)}"}

# class CalendarAgent:
#     SCOPES = ['https://www.googleapis.com/auth/calendar']

#     def __init__(self, credentials_file='client_secret_new.json', token_file='token.json'):
#         """
#         Initializes the CalendarAgent and authenticates with Google Calendar API.
#         """
#         base_dir = os.path.dirname(os.path.abspath(__file__))
#         self.credentials_file = os.path.join(base_dir, credentials_file)
#         self.token_file = os.path.join(base_dir, token_file)
#         self.credentials = self.authenticate()
#         self.service = build("calendar", "v3", credentials=self.credentials)

#     def authenticate(self):
#         """
#         Handles authentication with Google Calendar API.
#         - If token.json exists and is valid, uses it.
#         - Otherwise, triggers the OAuth flow to generate a new token.json.
#         """
#         creds = None

#         # Load existing token if available
#         if os.path.exists(self.token_file):
#             with open(self.token_file, 'rb') as token:
#                 creds = pickle.load(token)

#         # If there are no (valid) credentials, ask the user to authenticate
#         if not creds or not creds.valid:
#             if creds and creds.expired and creds.refresh_token:
#                 creds.refresh(Request())
#             else:
#                 webbrowser.register('chrome', None, webbrowser.BackgroundBrowser('/usr/bin/google-chrome'))
#                 flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
#                 creds = flow.run_local_server(port=0)

#             # Save the credentials for future use
#             with open(self.token_file, 'wb') as token:
#                 pickle.dump(creds, token)

#         return creds

#     def schedule_event(self, task_description, start_time, duration_hours, time_zone):
#         """
#         Schedules an event in Google Calendar.

#         Args:
#         - task_description (str): Description of the event.
#         - start_time (str): ISO 8601 start time (e.g., "2025-03-12T09:00:00").
#         - duration_hours (int): Duration of the event in hours.
#         - time_zone (str): Time zone of the event.

#         Returns:
#         - dict: Confirmation message and event ID.
#         """
#         try:
#             end_time = (datetime.fromisoformat(start_time) + timedelta(hours=duration_hours)).isoformat()
#             event_details = {
#                 "summary": task_description,
#                 "start": {"dateTime": start_time, "timeZone": time_zone},
#                 "end": {"dateTime": end_time, "timeZone": time_zone},
#             }

#             # Call Google Calendar API
#             event = self.service.events().insert(calendarId="primary", body=event_details).execute()
#             print(f"Google Calendar API called with: {event_details}")
#             return {"message": f"Scheduled event: {task_description}", "eventDetails": event_details}
#         except Exception as e:
#             return {"error": f"Failed to schedule event: {str(e)}"}

# class WeatherAgent:
#     def __init__(self):
#         # Get the API key from environment variables (recommended)
#         self.api_key = os.getenv("WEATHER_API_KEY")  # Replace with actual key if needed
#         self.base_url = "https://api.openweathermap.org/data/2.5/weather"

#     def fetch_weather(self, location):
#         """
#         Fetches real-time weather information for a location using OpenWeatherMap API.
#         """
#         #print("lol", self.api_key)
#         if not self.api_key:
#             return {"error": "Weather API key is missing. Please set WEATHER_API_KEY."}

        
#         url = f"{self.base_url}?q={location}&appid={self.api_key}&units=metric"
#         try:
#             response = requests.get(url)
#             data = response.json()

#             if response.status_code != 200:
#                 return {"error": data.get("message", "Failed to fetch weather data.")}

#             weather_info = {
#                 "location": data["name"],
#                 "temperature": f"{data['main']['temp']}°C",
#                 "condition": data["weather"][0]["description"].capitalize()
#             }

#             return weather_info

#         except requests.RequestException as e:
#             return {"error": f"Request failed: {str(e)}"}

class WeatherAgent:
    def __init__(self):
        """Initialize the Weather Agent."""
        self.api_key = os.getenv("WEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5/forecast"  # ✅ Forecast API
        self.default_location = "New York"  # ✅ Hardcoded location

    def fetch_weather(self, date):
        """
        Fetches the weather forecast for the hardcoded location (New York) and date.
        """
        if not self.api_key:
            return {"error": "Weather API key is missing. Please set WEATHER_API_KEY."}

        url = f"{self.base_url}?q={self.default_location}&appid={self.api_key}&units=metric"

        try:
            response = requests.get(url)
            data = response.json()

            if response.status_code != 200:
                return {"error": data.get("message", "Failed to fetch weather data.")}

            # Convert date to YYYY-MM-DD
            target_date = datetime.strptime(date, "%Y-%m-%d").date()

            # Find the closest weather forecast for that date
            forecast_data = data.get("list", [])
            closest_forecast = None
            for forecast in forecast_data:
                forecast_date = datetime.fromtimestamp(forecast["dt"]).date()
                if forecast_date == target_date:
                    closest_forecast = forecast
                    break

            if not closest_forecast:
                return {"error": "No forecast data available for this date."}

            # Extract weather details
            weather_condition = closest_forecast["weather"][0]["description"].capitalize()
            temperature = closest_forecast["main"]["temp"]

            return {
                "location": self.default_location,
                "date": date,
                "temperature": f"{temperature}°C",
                "condition": weather_condition
            }

        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}


class StockMarketAgent:
    def __init__(self):
        # Get the API key from environment variables
        self.api_key = os.getenv("STOCK_API_KEY")
        self.base_url = "http://api.marketstack.com/v1/eod"  # Correct endpoint for latest stock price

    def fetch_stock_price(self, company_symbol):
        """
        Fetches stock price for a given company using MarketStack API.
        """
        if not self.api_key:
            return {"error": "Stock API key is missing. Please set STOCK_API_KEY."}

        # ✅ Ensure company symbol is uppercase
        company_symbol = company_symbol.upper()

        # ✅ Correct GET request format for MarketStack
        url = f"{self.base_url}?access_key={self.api_key}&symbols={company_symbol}"

        try:
            response = requests.get(url)
            data = response.json()

            # ✅ Handle API errors gracefully
            if "data" not in data or not data["data"]:
                return {"error": "Invalid stock symbol or API limit reached."}

            # ✅ Extract stock price
            stock_data = data["data"][0]
            stock_price = stock_data["close"]
            last_updated = stock_data["date"]

            return {
                "company": company_symbol,
                "stock_price": f"${stock_price}",
                "last_updated": last_updated
            }

        except requests.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}