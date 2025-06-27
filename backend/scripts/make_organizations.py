# import csv
# from database.db import get_db_connection

# # Function to insert organization into the database
# def add_organization_to_db(name, organization_type, website_url):
#     conn, cursor = get_db_connection()
#     try:
#         cursor.execute(
#             'INSERT INTO organizations (name, organization_type, website_url) VALUES (%s, %s, %s)',
#             (name, organization_type, website_url))
#         conn.commit()
#         organization_id = cursor.lastrowid
#         print(f"Added organization: {name}, ID: {organization_id}")
#         return organization_id
#     finally:
#         conn.close()

# # Function to read CSV and insert organizations
# def load_organizations_from_csv(csv_file_path):
#     with open(csv_file_path, newline='') as csvfile:
#         reader = csv.DictReader(csvfile)
#         for row in reader:
#             name = row['name']
#             website_url = row['website_url']
#             add_organization_to_db(name, 'enterprise', website_url)

# Path to the CSV file
# csv_file_path = 'organizations.csv'

# Insert organizations
# load_organizations_from_csv(csv_file_path)

# import pandas as pd

# df = pd.read_csv("/Users/natanvidra/Workspace/FinanceGPT/backend/scripts/smaller_enterprise_list_with_websites.csv")
# print(df.head())

# import pandas as pd

# # Load the CSV file
# df = pd.read_csv("/Users/natanvidra/Workspace/FinanceGPT/backend/scripts/smaller_enterprise_list_with_websites.csv")

# # Drop specified columns
# df = df.drop(columns=["New Column", "Find Domain from Company Name"])

# # Drop rows with missing values
# df_cleaned = df.dropna()

# # Display the first few rows of the cleaned DataFrame
# print(df_cleaned.head())
# # remove first two characters from domain column
# df_cleaned['domain'] = df_cleaned['domain'].str[2:]
# df_cleaned.to_csv("/Users/natanvidra/Workspace/FinanceGPT/backend/scripts/cleaned_enterprise_list.csv", index=False)

import pandas as pd
import requests
from bs4 import BeautifulSoup

df = pd.read_csv("/Users/natanvidra/Workspace/FinanceGPT/backend/scripts/cleaned_enterprise_list.csv")


# Helper function to scrape sub-URLs from the main website
def get_links(initial_url: str):
    # Send a GET request to the website's URL
    # add www to the initial_url
    initial_url = "https://www." + initial_url
    response = requests.get(initial_url)
    # Parse the HTML code with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    # Find all <a> tags and extract the href attribute (the hyperlink)
    links = []
    links_text = []
    for link in soup.find_all('a'):
        if type(link.get('href')) == str:
            if link.get('href')[0] == "/":
                web_url = initial_url.rstrip("/") + link.get('href')  # Full URL
                # web_text = get_text_from_url(web_url)
                # if len(web_text) > 0:
                links.append(web_url)
                # links_text.append(web_text)
    return links
    # return links, links_text

# # Helper function to extract text from a URL
# def get_text_from_url(web_url):
#     response = requests.get(web_url)
#     result = p.from_buffer(response.content)
#     text = result.get("content", "").strip()
#     return text.replace("\n", "").replace("\t", "")

# call get_links for each row in the dataframe
for index, row in df.iterrows():
    try:
        links = get_links(row['domain'])
        # save new csv with links, company name and domain for each company
        df_links = pd.DataFrame({'links': links, 'company_name': row['Company Name'], 'domain': row['domain']})
        df_links.to_csv(f"/Users/natanvidra/Workspace/FinanceGPT/backend/scripts/subdomains/{row['Company Name']}.csv", index=False)
    except:
        continue