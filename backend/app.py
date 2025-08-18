from flask import Flask, request, jsonify, abort, redirect, send_file, Blueprint
from werkzeug.utils import secure_filename
from flask_cors import CORS, cross_origin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import boto3
from api_endpoints.login.handler import LoginHandler, SignUpHandler, ForgotPasswordHandler, ResetPasswordHandler
import os
import pathlib
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import google.auth.transport.requests
from flask.wrappers import Response
import json
import jwt
import requests
from database.db_auth import api_key_access_invalid
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, decode_token, JWTManager, get_jwt_identity
from flask_mail import Mail
from jwt import InvalidTokenError
from urllib.parse import urlparse
from database.db import create_user_if_does_not_exist
from constants.global_constants import kSessionTokenExpirationTime
from database.db_auth import extractUserEmailFromRequest, is_session_token_valid, is_api_key_valid, user_id_for_email, verifyAuthForPaymentsTrustedTesters, verifyAuthForCheckoutSession, verifyAuthForPortalSession
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request
from api_endpoints.payments.handler import CreateCheckoutSessionHandler, CreatePortalSessionHandler, StripeWebhookHandler
from api_endpoints.refresh_credits.handler import RefreshCreditsHandler
from api_endpoints.user.handler import ViewUserHandler
from api_endpoints.generate_api_key.handler import GenerateAPIKeyHandler
from api_endpoints.delete_api_key.handler import DeleteAPIKeyHandler
from api_endpoints.get_api_keys.handler import GetAPIKeysHandler
from enum import Enum
import stripe
from dotenv import load_dotenv
import ray
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from flask_socketio import SocketIO, emit, disconnect
from database.db_auth import user_email_for_session_token
from flask.cli import with_appcontext
import click
import threading
import time
import csv
from fpdf import FPDF
import openai
import shutil
from io import BytesIO
import io
from tika import parser as p
import anthropic
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from datasets import Dataset, load_dataset
import re
import ragas
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from bs4 import BeautifulSoup
from flask_mysql_connector import MySQL
import MySQLdb.cursors
from nltk.translate.bleu_score import sentence_bleu
import nltk
# Download required NLTK data for BLEU calculation
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

#WESLEY
from api_endpoints.financeGPT.chatbot_endpoints import create_chat_shareable_url, access_sharable_chat

from database.db import get_db_connection

from api_endpoints.financeGPT.chatbot_endpoints import add_prompt_to_workflow_db, add_workflow_to_db, \
    add_chat_to_db, add_message_to_db, chunk_document, get_text_from_single_file, add_document_to_db, get_relevant_chunks,  \
    remove_prompt_from_workflow_db, remove_ticker_from_workflow_db, reset_uploaded_docs_for_workflow, retrieve_chats_from_db, \
    delete_chat_from_db, retrieve_message_from_db, retrieve_docs_from_db, add_sources_to_db, delete_doc_from_db, reset_chat_db, change_chat_mode_db, update_chat_name_db, \
    add_ticker_to_chat_db, download_10K_url_ticker, download_filing_as_pdf, reset_uploaded_docs, check_valid_api, add_model_key_to_db, get_text_pages_from_single_file, \
    add_ticker_to_workflow_db, add_chat_to_db, add_message_to_db, chunk_document, get_text_from_single_file, add_document_to_db, get_relevant_chunks, process_ticker_info_wf, \
    retrieve_chats_from_db, delete_chat_from_db, retrieve_message_from_db, retrieve_docs_from_db, add_sources_to_db, delete_doc_from_db, reset_chat_db, \
    change_chat_mode_db, update_chat_name_db, find_most_recent_chat_from_db, process_prompt_answer, \
    ensure_SDK_user_exists, get_chat_info, ensure_demo_user_exists, get_message_info, get_text_from_url, \
    add_organization_to_db, get_organization_from_db, update_workflow_name_db, retrieve_messages_from_share_uuid

from datetime import datetime

from database.db_auth import get_db_connection

from api_endpoints.gpt4_gtm.handler import gpt4_blueprint
from api_endpoints.languages.chinese import chinese_blueprint
from api_endpoints.languages.japanese import japanese_blueprint
from api_endpoints.languages.korean import korean_blueprint
from api_endpoints.languages.spanish import spanish_blueprint
from api_endpoints.languages.arabic import arabic_blueprint
from datetime import datetime
from flask import current_app




load_dotenv(override=True)

app = Flask(__name__)
app.register_blueprint(gpt4_blueprint)
app.register_blueprint(chinese_blueprint)
app.register_blueprint(japanese_blueprint)
app.register_blueprint(korean_blueprint)
app.register_blueprint(spanish_blueprint)
app.register_blueprint(arabic_blueprint)

#if ray.is_initialized() == False:
   #ray.init(logging_level="INFO", log_to_driver=True)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def ensure_ray_started():
    if not ray.is_initialized():
        try:
            ray.init(
                logging_level="INFO",
                log_to_driver=True,
                ignore_reinit_error=True  # Helpful when running in dev
            )
        except Exception as e:
            print(f"Ray init failed: {e}")

# TODO: Replace with your URLs.
config = {
  'ORIGINS': [
    'http://localhost:3000',  # React
    'http://localhost:3001',  # React (alternative port)
    'http://localhost:5000',
    'http://localhost:8000',
    'http://localhost:5050',
    'http://dashboard.localhost:3000',  # React
    'https://anote.ai', # Frontend prod URL,
    'https://privatechatbot.ai', # Frontend prod URL,
    'https://dashboard.privatechatbot.ai', # Frontend prod URL,
  ],
}
CORS(app, resources={ r'/*': {'origins': config['ORIGINS']}}, supports_credentials=True)

app.secret_key = '6cac159dd02c902f822635ee0a6c3078'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_HTTPONLY'] = False
app.config["JWT_SECRET_KEY"] = "6cac159dd02c902f822635ee0a6c3078"
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = kSessionTokenExpirationTime
app.config["JWT_TOKEN_LOCATION"] = "headers"
app.config.from_object(__name__)

jwt_manager = JWTManager(app)
app.jwt_manager = jwt_manager

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vidranatan@gmail.com'
app.config['MAIL_PASSWORD'] = 'fhytlgpsjyzutlnm'
app.config['MAIL_DEFAULT_SENDER'] = 'vidranatan@gmail.com'
mail = Mail(app)


#MySQL config -- could put these in a backend .env if there are different users
app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DATABASE'] = 'agents'


#debug
print("MySQL config:", {
    "host": app.config['MYSQL_HOST'],
    "user": app.config['MYSQL_USER'],
    "password": app.config['MYSQL_PASSWORD'],
    "database": app.config['MYSQL_DATABASE']
})

mysql = MySQL(app)


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def valid_api_key_required(fn):
  @wraps(fn)
  def wrapper(*args, **kwargs):
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        splits = auth_header.split(' ')
        if len(splits) > 1:
          api_key = auth_header.split(' ')[1]
          if is_api_key_valid(api_key):
            # If api key is valid, return the decorated function
            return fn(*args, **kwargs)
    # If API key is not present or valid, return an error message or handle it as needed
    return "Unauthorized", 401
  return wrapper

def jwt_or_session_token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
      return fn(*args, **kwargs)
    return wrapper


class ProtectedDatabaseTable(Enum):
    # PROFILE_LISTS = 1
    # PROFILES_MULTI = 2
    API_KEYS = 1

# Example of auth function.  This would be called like
# verifyAuthForIDs(ProtectedDatabaseTable.PROFILE_LISTS, request.json["id"])
# in your flask endpoints before calling business logic.  This needs to
# be modified to fit your schema.
def verifyAuthForIDs(table, non_user_id):
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401

  access_denied = False
  user_id = user_id_for_email(user_email)
  if table == ProtectedDatabaseTable.API_KEYS:
    access_denied = api_key_access_invalid(user_id, non_user_id)
  if access_denied:
    abort(401)

#WESLEY
@app.route('/generate-playbook/<int:chat_id>', methods = ["GET"])
@jwt_or_session_token_required
def create_shareable_playbook(chat_id):
    url = create_chat_shareable_url(chat_id)
    return jsonify({
            "url": url,
            "success": True,
            "message": "Shareable URL generated successfully"
        }), 200

@app.route('/playbook/<string:playbook_url>', methods=["POST"])
@cross_origin(supports_credentials=True)
def import_shared_chat(playbook_url):
    return access_sharable_chat(playbook_url) 

@app.route('/health', methods=['GET'])
def health_check():
    return "Healthy", 200

# Auth
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  #this is to set our environment to https because OAuth 2.0 only supports https environments

GOOGLE_CLIENT_ID = "261908856206-fff63nag7j793tkbapd3hugthbcp8kfn.apps.googleusercontent.com"  #enter your client id you got from Google console
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")  #set the path to where the .json file you got Google console is

flow = Flow.from_client_secrets_file(  #Flow is OAuth 2.0 a class that stores all the information on how we want to authorize our users
    client_secrets_file=client_secrets_file,
    # scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/gmail.send", "openid"],  #here we are specifing what do we get after the authorization
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],  #here we are specifing what do we get after the authorization
    # redirect_uri="http://localhost:5000/callback"  #and the redirect URI is the point where the user will end up after the authorization
    # redirect_uri="http://127.0.0.1:3000"  #and the redirect URI is the point where the user will end up after the authorization
)
# postmessage

@app.route("/login")  #the page where the user can login
@cross_origin(supports_credentials=True)
def login():
    if request.args.get('email') and len(request.args.get('email')) > 0:
      return LoginHandler(request)
    else:
      o = urlparse(request.base_url)
      netloc = o.netloc
      scheme = "https"
      if "localhost" in netloc:
        scheme = "http"
    
      flow.redirect_uri = f'{scheme}://{netloc}/callback'
    #   flow.redirect_uri = f'https://upreachapi.upreach.ai/callback'

      state_dict = {
        "redirect_uri": flow.redirect_uri
      }

      if request.args.get('product_hash'):
        print("during checking product hash")
        state_dict["product_hash"] = request.args.get('product_hash')
      if request.args.get('free_trial_code'):
        print("during checking free_trial_code")
        state_dict["free_trial_code"] = request.args.get('free_trial_code')

      state = jwt.encode(state_dict, app.config["JWT_SECRET_KEY"], algorithm="HS256")

      # Generate the authorization URL and use the JWT as the state value
      authorization_url, _ = flow.authorization_url(state=state)

      response = Response(
          response=json.dumps({'auth_url':authorization_url}),
          status=200,
          mimetype='application/json'
      )
      response.headers.add('Access-Control-Allow-Headers',
                          'Origin, Content-Type, Accept')
      
      return response



@app.route("/callback")  #this is the page that will handle the callback process meaning process after the authorization
@cross_origin(supports_credentials=True)
def callback():
    try:
        decrypted_token = jwt.decode(request.args["state"], app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        product_hash = decrypted_token.get('product_hash', None)
        free_trial_code = decrypted_token.get('free_trial_code', None)
    except jwt.exceptions.InvalidSignatureError:
        abort(500)
    flow.redirect_uri = decrypted_token["redirect_uri"]
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    # TODO: COMMENT OUT WHEN DEPLOY TO PROD
    default_referrer = "http://dashboard.localhost:3000"
    # default_referrer = "https://dashboard.privatechatbot.ai"
    user_id = create_user_if_does_not_exist(id_info.get("email"), id_info.get("sub"), id_info.get("name"), id_info.get("picture"))

    access_token = create_access_token(identity=id_info.get("email"))
    refresh_token = create_refresh_token(identity=id_info.get("email"))
    productGetParam = ""
    if product_hash is not None:
      productGetParam = "&" + "product_hash=" + product_hash
    freeTrialCodeGetParam = ""
    if free_trial_code is not None:
      freeTrialCodeGetParam = "&" + "free_trial_code=" + free_trial_code

    print("request.referrer")
    print(request.referrer)
    # response = redirect(
    #   (request.referrer or default_referrer) +
    #   "?accessToken=" + access_token + "&"
    #   "refreshToken=" + refresh_token
    # )
    response = redirect(
      (default_referrer) +
      "?accessToken=" + access_token + "&"
      "refreshToken=" + refresh_token + productGetParam + freeTrialCodeGetParam
    )
    return response

# This route is used to refresh the JWT
@app.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    # Get the JWT refresh token from the Authorization header
    authorization_header = request.headers["Authorization"]
    authorization_header_parts = authorization_header.split(" ")

    if len(authorization_header_parts) >= 2:
      jwt_token = authorization_header_parts[1]

      try:
          # Try to decode the JWT
          decoded_jwt = decode_token(jwt_token)

          # If the JWT is valid, generate a new JWT with a refreshed expiration time
          access_token = create_access_token(identity=decoded_jwt["sub"])

          # Return the new JWT in the response
          return jsonify({"accessToken": access_token}), 200
      except InvalidTokenError:
          # If the JWT is invalid, return an error
          return jsonify({"error": "Invalid JWT"}), 401
    else:
      # If the Authorization header does not have enough elements, return an error
        return jsonify({"error": "Invalid Authorization header"}), 401

@app.route("/signUp", methods=["POST"])
@cross_origin(supports_credentials=True)
def signUp():
  return SignUpHandler(request)

@app.route("/forgotPassword", methods=["POST"])
@cross_origin(supports_credentials=True)
def forgotPassword():
  return ForgotPasswordHandler(request, mail)

@app.route("/resetPassword", methods=["POST"])
@cross_origin(supports_credentials=True)
def resetPassword():
  return ResetPasswordHandler(request)

@app.route('/refreshCredits', methods = ['POST'])
@jwt_or_session_token_required
def RefreshCredits():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  return jsonify(RefreshCreditsHandler(request, user_email))

# Billing

@app.route('/createCheckoutSession', methods=['POST'])
@jwt_or_session_token_required
def create_checkout_session():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  if not verifyAuthForPaymentsTrustedTesters(user_email):
    abort(401)
  verifyAuthForCheckoutSession(user_email, mail)
  return CreateCheckoutSessionHandler(request, user_email)

@app.route('/createPortalSession', methods=["POST"])
@jwt_or_session_token_required
def customer_portal():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  print("got email customer_portal")
  if not verifyAuthForPaymentsTrustedTesters(user_email):
    print("no verifyAuthForPaymentsTrustedTesters")
    abort(401)
  verifyAuthForPortalSession(request, user_email, mail)
  return CreatePortalSessionHandler(request, user_email)

STRIPE_WEBHOOK_SECRET = "whsec_Ustl52CpxewYc33WdamF06lDCjgg3a2e"

@app.route('/stripeWebhook', methods=['POST'])
def stripe_webhook():
  sig_header = request.headers.get('Stripe-Signature')
  try:
      # Verify the signature of the event
      event = stripe.Webhook.construct_event(
          request.data, sig_header, STRIPE_WEBHOOK_SECRET
      )
  except (stripe.error.SignatureVerificationError, ValueError):
      return 'Invalid signature', 400
  return StripeWebhookHandler(request, event)

@app.route('/viewUser', methods = ['GET'])
@jwt_or_session_token_required
def ViewUser():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  return ViewUserHandler(request, user_email)

# Example of a background task that can consistently do
# some processing in the background independently of your
# actual web app.
# def background_task():
#   try:
#     print("inside background task")
#     with app.app_context():  # This is important to access Flask app resources
#       while True:
#         automation_ids = view_automations_to_process()
#         print("automation_ids", automation_ids)
#         for id in automation_ids:
#           print("in for automation_ids")
#           socketId = get_socket_for_automation(id)
#           print("socketId")
#           print(socketId)
#           trigger_automation_step.remote(id, auth, host, socketId)
#         time.sleep(60)
#   except Exception as e:
#     print(f"Exception in background_task: {e}")
# app.start_background_task(background_task)

# Helper function to scrape sub-URLs from the main website
def get_links(initial_url: str):
    # Send a GET request to the website's URL
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
                web_text = get_text_from_url(web_url)
                if len(web_text) > 0:
                    links.append(web_url)
                    links_text.append(web_text)
    return links, links_text

# Helper function to extract text from a URL
def get_text_from_url(web_url):
    response = requests.get(web_url)
    result = p.from_buffer(response.content)
    text = result.get("content", "").strip()
    return text.replace("\n", "").replace("\t", "")

# Organization routes

@app.route('/create_organization', methods=['POST'])
@valid_api_key_required
def create_organization():
    try:
        name = request.json.get('name')
        organization_type = request.json.get('organization_type')  # 'enterprise' or 'individual'
        website_url = request.json.get('website_url')

        if not name or not organization_type:
            return jsonify({"error": "Missing required fields"}), 400

        # Add organization to the database
        organization_id = add_organization_to_db(name, organization_type, website_url)

        # Scrape website if a URL is provided
        if website_url:
            print(f"Scraping website {website_url}...")
            links, links_text = get_links(website_url)
            for link, link_text in zip(links, links_text):
                print(f"Processing scraped URL {link}...")
                # Ingest each sub-URL's text as a document
                doc_id, doesExist = add_document_to_db(link_text, link, organization_id)
                if not doesExist:
                    ensure_ray_started()
                    chunk_document.remote(link_text, 1000, doc_id)

        return jsonify({"organization_id": organization_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_organization', methods=['GET'])
@valid_api_key_required
def get_organization():
    try:
        organization_id = request.args.get('organization_id')
        if not organization_id:
            return jsonify({"error": "Missing organization_id"}), 400

        # Get organization info from the database
        organization = get_organization_from_db(organization_id)
        if not organization:
            return jsonify({"error": "Organization not found"}), 404

        return jsonify(organization), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/<organization_name>')
def chat_with_organization(organization_name):
    organization = get_organization_from_db_by_name(organization_name)
    if organization:
        return jsonify({
            'name': organization['name'],
            'website_url': organization['website_url'],
            'organization_type': organization['organization_type']
        })
    else:
        return jsonify({'error': 'Organization not found'}), 404

def get_organization_from_db_by_name(organization_name):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT * FROM organizations WHERE name = %s', [organization_name])
    organization = cursor.fetchone()
    conn.close()
    return organization

## CHATBOT SECTION
output_document_path = 'output_document'
chat_history_file = os.path.join(output_document_path, 'chat_history.csv')
vector_base_path = 'db'
source_documents_path = 'source_documents'

@app.route('/api/reset-everything', methods=['POST']) #Change this to use MYSQL db
def reset_everything():
    try:
        # Delete vector database
        #shutil.rmtree(vector_base_path)
        # Delete user input documents
        if os.path.exists(source_documents_path):
            shutil.rmtree(source_documents_path)
        # Delete chat history
        if os.path.exists(output_document_path):
            shutil.rmtree(output_document_path)
            # Recreate the output folder
            os.makedirs(output_document_path)

        # Create an empty chat history CSV file
        chat_history_file_path = os.path.join(output_document_path, 'chat_history.csv')
        with open(chat_history_file_path, 'w', newline='') as csvfile:
            print("test1")
            writer = csv.writer(csvfile)
            writer.writerow(['query', 'response'])

        return 'Reset was successful!'
    except Exception as e:
        return f'Failed to delete DB folder: {str(e)}', 500

@app.route('/download-chat-history', methods=['POST'])
def download_chat_history():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    try:
        chat_type = request.json.get('chat_type')
        chat_id = request.json.get('chat_id')

        messages = retrieve_message_from_db(user_email, chat_id, chat_type)

        paired_messages = []

        for i in range(len(messages) - 1):
            if messages[i]['sent_from_user'] == 1 and messages[i+1]['sent_from_user'] == 0:
                regex = re.compile(r"Document:\s*[^:]+:\s*(.*?)(?=Document:|$)", re.DOTALL)
                if messages[i+1]["relevant_chunks"]:
                    found = re.findall(regex, messages[i+1]["relevant_chunks"])
                    paragraphs = [paragraph.strip() for paragraph in found]
                    if len(paragraphs) > 1:
                        paired_messages.append((messages[i]['message_text'], messages[i+1]['message_text'], paragraphs[0], paragraphs[1]))
                    elif len(paragraphs) == 1:
                        paired_messages.append((messages[i]['message_text'],  messages[i+1]['message_text'], paragraphs[0], None))
                else:
                    paired_messages.append((messages[i]['message_text'], messages[i+1]['message_text'], None, None))


        csv_output = io.StringIO()
        writer = csv.writer(csv_output)
        writer.writerow(['query', 'response', 'chunk1', 'chunk2'])  # Write header
        writer.writerows(paired_messages)
        csv_output.seek(0)  # Go back to the start of the StringIO object

        return Response(
            csv_output.getvalue(),
            mimetype='text/csv',
            headers={"Content-disposition": "attachment; filename=chat_history.csv"}
        )
    except Exception as e:
        print("error is,", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/create-new-chat', methods=['POST'])
def create_new_chat():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    chat_type = request.json.get('chat_type')
    model_type = request.json.get('model_type')

    chat_id = add_chat_to_db(user_email, chat_type, model_type) #for now hardcode the model type as being 0

    return jsonify(chat_id=chat_id)

@app.route('/retrieve-all-chats', methods=['POST'])
def retrieve_chats():
    #Given an input of a chat_type and user_email, it will return as a list of dictionaries all the chats of that user and chat type from the db

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401
    #chat_type = request.json.get('chat_type')

    chat_info = retrieve_chats_from_db(user_email)

    return jsonify(chat_info=chat_info)

@app.route('/retrieve-messages-from-chat', methods=['POST'])
def retrieve_messages_from_chat():
    #Getting current user not working, fix this later
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    chat_type = request.json.get('chat_type')
    chat_id = request.json.get('chat_id')

    messages = retrieve_message_from_db(user_email, chat_id, chat_type)

    return jsonify(messages=messages)

@app.route('/retrieve-shared-messages-from-chat', methods=['POST'])
def get_playbook_messages():
    chat_type = 0
    chat_id = request.json.get('chat_id')

    messages = retrieve_message_from_db("anon@anote.ai", chat_id, chat_type)

    return jsonify(messages=messages)
    
@app.route('/update-chat-name', methods=['POST'])
def update_chat_name():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    chat_name = request.json.get('chat_name')
    chat_id = request.json.get('chat_id')

    print("chat_name", chat_name)

    update_chat_name_db(user_email, chat_id, chat_name)

    return jsonify({"Success": "Chat name updated"}), 200

@app.route('/infer-chat-name', methods=['POST'])
def infer_chat_name():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    chat_messages = request.json.get('messages')
    chat_id = request.json.get('chat_id')

    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user",
             "content": f"Based off these 2 messages between me and my chatbot, please infer a name for the chat. Keep it to a maximum of 4 words, 5 if you must. Do not use the word chat in it. Some good examples are, AI research paper, Apple financial report, Questions about earnings calls. Return only the chatname and nothing else. Here are the messages: {chat_messages}"}
        ]
    )
    new_name = str(completion.choices[0].message.content)

    update_chat_name_db(user_email, chat_id, new_name)

    return jsonify(chat_name=new_name)

@app.route('/update-workflow-name', methods=['POST'])
def update_workflow_name():
    print("Print Update-Workflow-Name")
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    workflow_name = request.json.get('workflow_name')
    workflow_id = request.json.get('workflow_id')

    print("NEW workflow_name", workflow_name)

    update_workflow_name_db(user_email, workflow_id, workflow_name)

    return "Workflow name updated"


@app.route('/delete-chat', methods=['POST'])
def delete_chat():
    chat_id = request.json.get('chat_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    return delete_chat_from_db(chat_id, user_email)


@app.route('/find-most-recent-chat', methods=['POST'])
def find_most_recent_chat():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    chat_info = find_most_recent_chat_from_db(user_email)

    return jsonify(chat_info=chat_info)


@app.route('/ingest-pdf', methods=['POST'])
def ingest_pdfs():
    start_time = datetime.now()
    print("start time is", start_time)

    chat_id = request.form.getlist('chat_id')[0]
    files = request.files.getlist('files[]')

    MAX_CHUNK_SIZE = 1000

    print("before files loop time is", datetime.now() - start_time)
    for file in files:
        #text = get_text_from_single_file(file)
        #text_pages = get_text_pages_from_single_file(file)

        result = p.from_buffer(file)
        text = result["content"].strip()

        filename = file.filename

        doc_id, doesExist = add_document_to_db(text, filename, chat_id=chat_id)

        if not doesExist:
            ensure_ray_started()
            chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)


    return jsonify({"error": "Invalid JWT"}), 200


    #return text, filename

@app.route('/api/ingest-pdf-wf', methods=['POST'])
def ingest_pdfs_wf():
    workflow_id = request.form['workflow_id']

    if 'files' not in request.files:
        return "No file part in the request", 400

    files = request.files.getlist('files')

    MAX_CHUNK_SIZE = 1000

    for file in files:
        text = get_text_from_single_file(file)
        text_pages = get_text_pages_from_single_file(file)
        filename = file.filename

        text
        doc_id, doesExist = add_document_to_db(text, filename, workflow_id)

        if not doesExist:
            ensure_ray_started()
            chunk_document.remote(text_pages, MAX_CHUNK_SIZE, doc_id)
    return text, filename

@app.route('/retrieve-current-docs', methods=['POST'])
def retrieve_current_docs():
    chat_id = request.json.get('chat_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    doc_info = retrieve_docs_from_db(chat_id, user_email)

    return jsonify(doc_info=doc_info)

@app.route('/delete-doc', methods=['POST'])
def delete_doc():
    doc_id = request.json.get('doc_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    delete_doc_from_db(doc_id, user_email)

    return "success"

@app.route('/change-chat-mode', methods=['POST'])
def change_chat_mode_and_reset_chat():
    chat_mode_to_change_to = request.json.get('model_type')
    chat_id = request.json.get('chat_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    try:
        reset_chat_db(chat_id, user_email)
        change_chat_mode_db(chat_mode_to_change_to, chat_id, user_email)

        return "Success"
    except:
        return "Error"

@app.route('/reset-chat', methods=['POST'])
def reset_chat():
    chat_id = request.json.get('chat_id')
    delete_docs = request.json.get('delete_docs')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    if delete_docs:
        reset_uploaded_docs(chat_id, user_email)

    reset_chat_db(chat_id, user_email)

    return jsonify({"Success": "Success"}), 200

@app.route('/process-message-pdf', methods=['POST'])
def process_message_pdf():
    message = request.json.get('message')
    chat_id = request.json.get('chat_id')
    model_type = request.json.get('model_type')
    model_key = request.json.get('model_key')


    is_guest = chat_id == 0

    if not is_guest:
        try:
            user_email = extractUserEmailFromRequest(request)
        except InvalidTokenError:
        # If the JWT is invalid, return an error
            return jsonify({"error": "Invalid JWT"}), 401

        ##Include part where we verify if user actually owns the chat_id later
    else:
        user_email = "guest@gmail.com"
    query = message.strip()

    #This adds user message to db
    if not is_guest:
        add_message_to_db(query, chat_id, 1)

    #Get most relevant section from the document
    if not is_guest:
        sources = get_relevant_chunks(2, query, chat_id, user_email)
    else: 
        sources = []
    
    sources_str = " ".join([", ".join(str(elem) for elem in source) for source in sources])

    if (model_type == 0):
        if model_key:
           model_use = model_key
        else:
           model_use = "gpt-4o-mini"

        print("using OpenAI and model is", model_use)
        
        try:
            completion = client.chat.completions.create(
                model=model_use,
                messages=[
                    {"role": "user",
                     "content": f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources_str} And this is the question:{query}."}
                ]
            )
            print("using fine tuned model")
            answer = str(completion.choices[0].message.content)
        except openai.NotFoundError:
            print(f"The model `{model_use}` does not exist. Falling back to 'gpt-4'.")
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user",
                     "content": f"First, tell the user that their given model key does not exist, and that you have resorted to using GPT-4 before answering their question, then add a line break and answer their question. You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources[0]}{sources[1]} And this is the question:{query}."}
                ]
            )
            answer = str(completion.choices[0].message.content)
    else:
        print("using Claude")

        anthropic = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        completion = anthropic.completions.create(
            model="claude-2",
            max_tokens_to_sample=700,
            prompt = (
              f"{HUMAN_PROMPT} "
              f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. "
              f"please address the question: {query}. "
              f"Consider the provided text as evidence: {sources_str}. "
              f"{AI_PROMPT}")
        )
        answer = completion.completion

    #This adds bot message
    message_id = None
    if not is_guest:
        message_id = add_message_to_db(answer, chat_id, 0)
        if message_id:

            try:
                add_sources_to_db(message_id, sources)
            except:
                print("no sources")

    return jsonify(answer=answer)

# Only for demo purposes
chat_to_document_mapping = {}
#DEMO_CHAT_ID = 99999
DEMO_USER_EMAIL = "demo@example.com"
chat_id = 0

@app.route('/process-message-pdf-demo', methods=['POST'])
def process_message_pdf_demo():
    message = request.json.get('message')
    query = message.strip()

    global chat_id
    user_email = DEMO_USER_EMAIL

    print("CHAT ID IS", chat_id)

    add_message_to_db(query, chat_id, 1)

    sources = get_relevant_chunks(2, query, chat_id, user_email)
    print('sources is', sources)
    sources_str = " ".join([", ".join(str(elem) for elem in source) for source in sources])
    print('sources_str is', sources_str)


    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user",
             "content": f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources_str} And this is the question:{query}."}
        ]
    )
    answer = str(completion.choices[0].message.content)

    message_id = add_message_to_db(answer, chat_id, 0)

    try:
        add_sources_to_db(message_id, sources)
    except:
        print("no sources")

    return jsonify(answer=answer)


@app.route('/ingest-pdf-demo', methods=['POST'])
def ingest_pdfs_demo():
    global chat_id
    user_email = DEMO_USER_EMAIL

    #create_new_demo_chat(chat_id, user_email)

    files = request.files.getlist('files[]')
    MAX_CHUNK_SIZE = 1000

    for file in files:
        result = p.from_buffer(file)  # Ensure your PDF extraction works as expected
        text = result["content"].strip()
        filename = file.filename

        # Assuming add_document_to_db and chunk_document.remote are implemented
        doc_id, doesExist = add_document_to_db(text, filename, chat_id=chat_id)
        if not doesExist:
            ensure_ray_started()
            chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)

    # This mapping is now redundant since we're using a static demo_chat_id, but you could maintain it if you plan to extend functionality
    chat_to_document_mapping[chat_id] = doc_id

    return jsonify({"message": "Document processed successfully"}), 200



@app.route('/download-chat-history-demo', methods=['POST'])
def download_chat_history_demo():
    global chat_id
    user_email = DEMO_USER_EMAIL

    try:
        chat_type = 0

        messages = retrieve_message_from_db(user_email, chat_id, chat_type)

        print("messages", messages)

        paired_messages = []
        for i in range(len(messages) - 1):
            if messages[i]['sent_from_user'] == 1 and messages[i+1]['sent_from_user'] == 0:
                regex = re.compile(r"Document:\s*[^:]+:\s*(.*?)(?=Document:|$)", re.DOTALL)
                if messages[i+1]["relevant_chunks"]:
                    found = re.findall(regex, messages[i+1]["relevant_chunks"])
                    paragraphs = [paragraph.strip() for paragraph in found]
                    if len(paragraphs) > 1:
                        paired_messages.append((messages[i]['message_text'], messages[i+1]['message_text'], paragraphs[0], paragraphs[1]))
                    elif len(paragraphs) == 1:
                        paired_messages.append((messages[i]['message_text'],  messages[i+1]['message_text'], paragraphs[0], None))
                else:
                    paired_messages.append((messages[i]['message_text'], messages[i+1]['message_text'], None, None))

        csv_output = io.StringIO()
        writer = csv.writer(csv_output)
        writer.writerow(['query', 'response', 'chunk1', 'chunk2'])
        writer.writerows(paired_messages)
        csv_output.seek(0)

        # Return the CSV content as a response
        return Response(
            csv_output.getvalue(),
            mimetype='text/csv',
            headers={"Content-disposition": "attachment; filename=chat_history.csv"}
        )
    except Exception as e:
        print("error is,", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/add-model-key', methods=['POST'])
def add_model_key():
    model_key = request.json.get('model_key')
    chat_id = request.json.get('chat_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    add_model_key_to_db(model_key, chat_id, user_email)

    return "success"


#Edgar
@app.route('/check-valid-ticker', methods=['POST'])
def check_valid_ticker():
   ticker = request.json.get('ticker')
   result = check_valid_api(ticker)
   return jsonify({'isValid': result})

@app.route('/add-ticker-to-chat', methods=['POST'])
def add_ticker():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    ticker = request.json.get('ticker')
    chat_id = request.json.get('chat_id')
    isUpdate = request.json.get('isUpdate')

    return add_ticker_to_chat_db(chat_id, ticker, user_email, isUpdate)


@app.route('/process-ticker-info', methods=['POST'])
def process_ticker_info():
    chat_id = request.json.get('chat_id')
    ticker = request.json.get('ticker')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    if ticker:
        MAX_CHUNK_SIZE = 1000

        reset_uploaded_docs(chat_id, user_email)


        url, ticker = download_10K_url_ticker(ticker)
        filename = download_filing_as_pdf(url, ticker)

        text = get_text_from_single_file(filename)

        #result = p.from_buffer(filename)
        #text = result["content"].strip()

        #
        #text_pages = get_text_pages_from_single_file(filename)

        print("test1")
        doc_id, doesExist = add_document_to_db(text, filename, chat_id)

        if not doesExist:
            print("test")
            ensure_ray_started()
            chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
            #remote_task = chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
            #result = ray.get(remote_task)

        #if os.path.exists(filename):
        #    os.remove(filename)
        #    print(f"File '{filename}' has been deleted.")
        #else:
        #    print(f"The file '{filename}' does not exist.")


    return jsonify({"error": "Invalid JWT"}), 200



@app.route('/temp-test', methods=['POST'])
def temp_test():

    anthropic = Anthropic(
      api_key=os.getenv("ANTHROPIC_API_KEY")
    )


    query = "What are some of the risk factors from the company?"

    sources = [
        "The Company's business, reputation, results of operations, financial condition and stock price can be affected by a number of factors, whether currently known or unknown, including those described below. When any one or more of these risks materialize from time to time, the Company's business, reputation, results of operations, financial condition and stock price can be materially and adversely affected. Because of the following factors, as well as other factors affecting the Company's results of operations and financial condition, past financial performance should not be considered to be a reliable indicator of future performance, and investors should not use historical trends to anticipate results or trends in future periods. This discussion of risk factors contains forward-looking statements. This section should be read in conjunction with Part II, Item 7, \"Management's Discussion and Analysis of Financial Condition and Results of Operations\" and the consolidated financial statements and accompanying notes in Part II, Item 8, \"Financial Statements and Supplementary Data\" of this Form 10-K.",
        "The Company's operations and performance depend significantly on global and regional economic conditions and adverse economic conditions can materially adversely affect the Company's business, results of operations and financial condition. The Company has international operations with sales outside the U.S. representing a majority of the Company's total net sales. In addition, the Company's global supply chain is large and complex and a majority of the Company's supplier facilities, including manufacturing and assembly sites, are located outside the U.S. As a result, the Company's operations and performance depend significantly on global and regional economic conditions."
    ]

    completion = anthropic.completions.create(
      model="claude-2",
      max_tokens_to_sample=700,
      prompt = (
        f"{HUMAN_PROMPT} "
        f"You are a factual chatbot that answers questions about 10-K documents. You only answer with answers you find in the text, no outside information. "
        f"please address the question: {query}. "
        f"Consider the provided text as evidence: {sources[0]}{sources[1]}. "
        f"{AI_PROMPT}")
    )

    print("anthropic result", completion.completion)

    return 'success'



## WORKFLOWS SECTION

@app.route('/create-new-workflow', methods=['POST'])
def create_new_workflow():
    print('create_new_workflow')
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    workflow_type = request.json.get('workflow_type')
    model_type = request.json.get('model_type')

    workflow_id = add_workflow_to_db(user_email, workflow_type) #DO I NEED MODEL_TYPE
    print(f'Workflow_id is APP :', workflow_id)
    return jsonify(workflow_id=workflow_id)

@app.route('/remove-ticker-from-workflow', methods=['POST'])
def remove_ticker_from_workflow():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        return jsonify({"error": "Invalid JWT"}), 401

    ticker = request.json.get('ticker')
    workflow_id = request.json.get('workflow_id')

    return remove_ticker_from_workflow_db(workflow_id, ticker, user_email)

@app.route('/add-prompt-to-workflow', methods=['POST'])
def add_prompt_to_workflow():
    try:
        user_email = extractUserEmailFromRequest(request)
        workflow_id = request.json.get('workflow_id')
        prompt_text = request.json.get('prompt_text')
    except InvalidTokenError:
        return jsonify({"error": "Invalid JWT"}), 401

    return add_prompt_to_workflow_db(workflow_id, prompt_text)

@app.route('/remove-prompt-from-workflow', methods=['POST'])
def remove_prompt_from_workflow():
    try:
        user_email = extractUserEmailFromRequest(request)
        prompt_id = request.json.get('prompt_id')
    except InvalidTokenError:
        return jsonify({"error": "Invalid JWT"}), 401

    return remove_prompt_from_workflow_db(prompt_id)




@app.route('/generate_financial_report', methods=['POST'])
def generate_financial_report():
    print("generate_financial_report")

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    try:
        tickers = request.json.get('tickers')
        print(f"tickers: {tickers}")
        questions = request.json.get('questions')
        workflowId = request.json.get('workflowId')

        # Initialize a single PDF for all tickers
        pdf = FPDF()
        pdf.add_page()

        pdf_title = '_'.join(tickers).upper()
        pdf_title = f'Financial_Report_{pdf_title}'
        pdf.set_title(pdf_title)

        for ticker in tickers:
            print(f"Processing ticker: {ticker}")
            pdf.set_font('Times', 'B', 16)
            pdf.ln(2)

            # Include standard header of company information in the PDF
            pdf.ln(h=5)
            pdf.set_font('Times', 'B', 12)
            pdf.write(1, f'Ticker: {ticker.upper()}')

            process_ticker_info_wf(user_email, workflowId, ticker)
            print("SUCCESSFULLY PROCESSED TICKER")

            # Including Q&A in PDF
            for question in questions:
                print(f"for loop")
                answer = process_prompt_answer(question, workflowId, user_email)
                print("Successfully processed answer: ", )
                answer_encoded = answer.encode('latin-1', 'replace').decode('latin-1')
                question_encoded = question.encode('latin-1', 'replace').decode('latin-1')

                pdf.ln(h=5)
                pdf.set_font('Times', 'B', 12)
                pdf.write(1, question_encoded)
                pdf.set_font('Times', '', 12)
                pdf.ln(h=5)
                pdf.multi_cell(0, 5, answer_encoded)
                print("PRINTED Q&A")

        pdf_output_path = 'financial_report.pdf'
        pdf.output(pdf_output_path, 'F')

         # Return the single PDF file
        return send_file(
            pdf_output_path,
            as_attachment=True,
            download_name=pdf_title + '.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f'Failed to generate financial report: {str(e)}')
        return f'Failed to generate financial report: {str(e)}', 500




@app.route("/generateAPIKey", methods=["POST"])
@jwt_or_session_token_required
def generateAPIKey():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  return GenerateAPIKeyHandler(request, user_email)


@app.route("/deleteAPIKey", methods=["POST"])
@jwt_or_session_token_required
def deleteAPIKey():
  verifyAuthForIDs(ProtectedDatabaseTable.API_KEYS, request.json["api_key_id"])
  return DeleteAPIKeyHandler(request)

@app.route('/getAPIKeys', methods = ['GET'])
@jwt_or_session_token_required
def getAPIKeys():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  return GetAPIKeysHandler(request, user_email)


#For the SDK
#later will need to add @valid_api_key_required to all

USER_EMAIL_API = "api@example.com"

@app.route('/public/upload', methods = ['POST'])
@valid_api_key_required
def upload():
    print("Form data:", request.form)
    print("Files:", request.files)

    #chat_type = int(request.form.getlist('task_type')[0])  # Convert to int
    #model_type = int(request.form.getlist('model_type')[0])

    chat_type = request.form.getlist('task_type')[0]
    model_type = request.form.getlist('model_type')[0]

    user_email = USER_EMAIL_API

    print("CHAT TYPE IS", chat_type)
    if chat_type == "documents": #question-answering
        print("question answer")
        files = request.files.getlist('files[]')
        paths = request.form.getlist('html_paths')

        print("paths is", paths)

        print("chat is is", chat_type)
        print("files are", files)

        #create a new user with user_email api@example.com
        ensure_SDK_user_exists(user_email)

        #create new chat
        model_number = 0 if model_type == "gpt" else 1 if model_type == "claude" else None
        chat_number = 0 if chat_type == "documents" else 1 if chat_type == "edgar" else None
        chat_id = add_chat_to_db(user_email, chat_number, model_number)

        #Ingest pdf
        MAX_CHUNK_SIZE = 1000

        for file in files:
            print("file is here")
            result = p.from_buffer(file)
            text = result["content"].strip()

            filename = file.filename

            doc_id, doesExist = add_document_to_db(text, filename, chat_id=chat_id)

            if not doesExist:
                #chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                ensure_ray_started()
                result_id = chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                ensure_ray_started()
                result = ray.get(result_id)
        for path in paths:

            text = get_text_from_url(path)

            doc_id, doesExist = add_document_to_db(text, path, chat_id=chat_id)

            if not doesExist:
                #chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                ensure_ray_started()
                result_id = chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                ensure_ray_started()
                result = ray.get(result_id)
    elif chat_type == "edgar": #edgar
        print("ticker")
        ticker = request.form.getlist('ticker')[0]

        ensure_SDK_user_exists(user_email)

        #create new chat
        model_number = 0 if model_type == "gpt" else 1 if model_type == "claude" else None
        chat_number = 0 if chat_type == "documents" else 1 if chat_type == "edgar" else None
        chat_id = add_chat_to_db(user_email, chat_number, model_number)

        if ticker:
            MAX_CHUNK_SIZE = 1000

            reset_uploaded_docs(chat_id, user_email)


            url, ticker = download_10K_url_ticker(ticker)
            filename = download_filing_as_pdf(url, ticker)

            text = get_text_from_single_file(filename)

            print("test1")
            doc_id, doesExist = add_document_to_db(text, filename, chat_id)

            if not doesExist:
                #print("test")
                #chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                ensure_ray_started()
                result_id = chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                
                result = ray.get(result_id)
    else:
        return jsonify({"id": "Please enter a valid task type"}), 400

    return jsonify({"id": chat_id}), 200


@app.route('/public/chat', methods=['POST'])
@valid_api_key_required
def public_ingest_pdf():
    user_email = USER_EMAIL_API
    ensure_SDK_user_exists(user_email) #do this here in case the user hasn't uploaded a document yet

    message = request.json['message']
    chat_id = request.json['chat_id']

    model_type, task_type = get_chat_info(chat_id)

    model_key = request.json['model_key']

    #at the moment don't think we need to add it to the db?
    #if model_key:
    #    add_model_key_to_db(model_key, chat_id, user_email)

    query = message.strip()

    #This adds user message to db
    add_message_to_db(query, chat_id, 1)

    #Get most relevant section from the document
    sources = get_relevant_chunks(2, query, chat_id, user_email)
    sources_str = " ".join([", ".join(str(elem) for elem in source) for source in sources])

    sources_swapped = [[str(elem) for elem in source[::-1]] for source in sources]
    print('sources swapped', sources_swapped)

    if (model_type == 0):
        if model_key:
           model_use = model_key
        else:
           model_use = "gpt-4o-mini"

        print("using OpenAI and model is", model_use)
        
        try:
            completion = client.chat.completions.create(
                model=model_use,
                messages=[
                    {"role": "user",
                     "content": f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources_str} And this is the question:{query}."}
                ]
            )
            print("using fine tuned model")
            answer = str(completion.choices[0].message.content)
        except openai.NotFoundError:
            print(f"The model `{model_use}` does not exist. Falling back to 'gpt-4'.")
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user",
                     "content": f"First, tell the user that their given model key does not exist, and that you have resorted to using GPT-4 before answering their question, then add a line break and answer their question. You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources[0]}{sources[1]} And this is the question:{query}."}
                ]
            )
            answer = str(completion.choices[0].message.content)
    else:
        print("using Claude")

        if model_key:
           return jsonify({"Error": "You cannot enter a fine-tuned model key when using Claude"}), 400

        anthropic = Anthropic(
            api_key = os.getenv("ANTHROPIC_API_KEY")
        )

        completion = anthropic.completions.create(
            model="claude-2",
            max_tokens_to_sample=700,
            prompt = (
              f"{HUMAN_PROMPT} "
              f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. "
              f"please address the question: {query}. "
              f"Consider the provided text as evidence: {sources_str}. "
              f"{AI_PROMPT}")
        )
        answer = completion.completion

    #This adds bot message
    message_id = add_message_to_db(answer, chat_id, 0)

    try:
        add_sources_to_db(message_id, sources)
    except:
        print("no sources")

    return jsonify(message_id=message_id, answer=answer, sources=sources_swapped) #can modify the sources here if we don't want to return the sources

@app.route('/public/evaluate', methods = ['POST'])
@valid_api_key_required
def evaluate():
    message_id = request.json['message_id']
    user_email = USER_EMAIL_API

    question_json, answer_json = get_message_info(message_id, user_email)

    question = question_json['message_text']
    answer = answer_json['message_text']
    context = answer_json['relevant_chunks']

    #get it in the corret data format to put in ragas
    if not isinstance(context, list):
        context = [context]

    contexts = [context]

    data = {
        "question": [question],
        "answer": [answer],
        "contexts": contexts
    }

    dataset = Dataset.from_dict(data)

    result = ragas.evaluate(
        dataset = dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
        ],
    )

    return result

@app.route('/testing-dashboard', methods=['GET'])
def testing_dashboard():
    """Web-based testing interface for the submit_model API"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Submit Model API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; }
            textarea { width: 100%; height: 200px; }
            button { padding: 10px 20px; margin: 10px 0; }
            .result { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
            .error { background: #ffebee; color: #c62828; }
            .success { background: #e8f5e8; color: #2e7d32; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Test Submit Model API</h1>
            
            <h3>API Key (will be auto-created):</h3>
            <input type="text" id="apiKey" value="test-api-key-12345" style="width: 300px;">
            
            <h3>Test Data (JSON):</h3>
            <textarea id="testData">{
  "benchmarkDatasetName": "flores_spanish_translation",
  "modelName": "test-gpt-model-v1",
  "modelResults": [
    "Hola mundo",
    "Buenos días",
    "Gracias por su ayuda",
    "¿Cómo está usted?",
    "Hasta luego"
  ]
}</textarea>
            
            <br>
            <button onclick="testAPI()">Test Submit Model API</button>
            <button onclick="createAPIKey()">Create Test API Key</button>
            <button onclick="checkHealth()">Check API Health</button>
            
            <div id="result"></div>
        </div>
        
        <script>
            async function createAPIKey() {
                const resultDiv = document.getElementById('result');
                try {
                    const response = await fetch('/create-test-api-key', { method: 'POST' });
                    const result = await response.json();
                    
                    if (result.success) {
                        document.getElementById('apiKey').value = result.api_key;
                        resultDiv.innerHTML = `<div class="result success">
                            <h4>✅ API Key Created</h4>
                            <p>Key: ${result.api_key}</p>
                        </div>`;
                    } else {
                        resultDiv.innerHTML = `<div class="result error">
                            <h4>❌ Failed to create API key</h4>
                            <p>${result.error}</p>
                        </div>`;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `<div class="result error">
                        <h4>❌ Error</h4>
                        <p>${error.message}</p>
                    </div>`;
                }
            }
            
            async function testAPI() {
                const resultDiv = document.getElementById('result');
                const apiKey = document.getElementById('apiKey').value;
                const testData = document.getElementById('testData').value;
                
                try {
                    const response = await fetch('/public/submit_model', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${apiKey}`
                        },
                        body: testData
                    });
                    
                    const result = await response.json();
                    const statusClass = response.ok ? 'success' : 'error';
                    
                    resultDiv.innerHTML = `<div class="result ${statusClass}">
                        <h4>${response.ok ? '✅' : '❌'} API Response (${response.status})</h4>
                        <pre>${JSON.stringify(result, null, 2)}</pre>
                    </div>`;
                } catch (error) {
                    resultDiv.innerHTML = `<div class="result error">
                        <h4>❌ Error</h4>
                        <p>${error.message}</p>
                    </div>`;
                }
            }
            
            async function checkHealth() {
                const resultDiv = document.getElementById('result');
                try {
                    const response = await fetch('/health');
                    const result = await response.json();
                    const statusClass = response.ok && result.status === 'healthy' ? 'success' : 'error';
                    
                    resultDiv.innerHTML = `<div class="result ${statusClass}">
                        <h4>${result.status === 'healthy' ? '✅' : '❌'} Health Check</h4>
                        <pre>${JSON.stringify(result, null, 2)}</pre>
                    </div>`;
                } catch (error) {
                    resultDiv.innerHTML = `<div class="result error">
                        <h4>❌ Error</h4>
                        <p>${error.message}</p>
                    </div>`;
                }
            }
        </script>
    </body>
    </html>
    """

@app.route('/create-test-api-key', methods=['POST'])
def create_test_api_key():
    """Create a test API key for development"""
    try:
        conn, cursor = get_db_connection()
        
        # Check if test user exists, create if not
        cursor.execute("SELECT id FROM users WHERE email = 'api@example.com'")
        user = cursor.fetchone()
        
        if not user:
            cursor.execute("""
                INSERT INTO users (email, person_name, credits) 
                VALUES ('api@example.com', 'Test API User', 1000)
            """)
            user_id = cursor.lastrowid
        else:
            user_id = user['id']
        
        # Create test API key
        test_api_key = 'test-api-key-12345'
        cursor.execute("""
            INSERT INTO apiKeys (user_id, api_key, key_name) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE api_key = VALUES(api_key)
        """, (user_id, test_api_key, 'Test API Key'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "api_key": test_api_key,
            "message": "Test API key created successfully"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/public/get_source_sentences', methods=['GET'])
def get_source_sentences():
    """
    Get source sentences from a benchmark dataset for translation
    
    Query parameters:
    - dataset: benchmark dataset name (default: flores_spanish_translation)  
    - count: number of sentences (default: 5)
    - start_idx: starting index (default: 0)
    
    Returns:
    {
        "success": true,
        "source_sentences": ["English sentence 1", "English sentence 2", ...],
        "sentence_ids": [0, 1, 2, 3, 4],
        "dataset": "flores_spanish_translation"
    }
    """
    try:
        dataset_name = request.args.get('dataset', 'flores_spanish_translation')
        count = int(request.args.get('count', 5))
        start_idx = int(request.args.get('start_idx', 0))
        
        # Get database connection to check for custom datasets
        conn, cursor = get_db_connection()
        
        try:
            # Handle FLORES+ datasets (Spanish, Japanese, Arabic, Chinese)
            flores_datasets = {
                'flores_spanish_translation': 'spa_Latn',
                'flores_japanese_translation': 'jpn_Jpan', 
                'flores_arabic_translation': 'arb_Arab',
                'flores_chinese_translation': 'zho_Hans'
            }
            
            if dataset_name in flores_datasets:
                # Set HF token for dataset access
                import os
                hf_token = os.getenv("HF_TOKEN")
                if hf_token:
                    os.environ["HF_TOKEN"] = hf_token
                
                # Load FLORES+ English source sentences (same for all languages)
                source_lang = "eng_Latn"
                source_dataset = load_dataset("openlanguagedata/flores_plus", source_lang, split="devtest")
                
                # Get requested range of sentences
                end_idx = start_idx + count
                source_sentences = [ex["text"] for ex in source_dataset.select(range(start_idx, end_idx))]
                sentence_ids = list(range(start_idx, end_idx))
                total_available = len(source_dataset)
                
            else:
                # Check if it's a custom dataset
                cursor.execute("""
                    SELECT reference_data FROM benchmark_datasets 
                    WHERE name = %s AND active = TRUE
                """, (dataset_name,))
                
                dataset = cursor.fetchone()
                if not dataset:
                    return jsonify({
                        "success": False,
                        "error": f"Dataset '{dataset_name}' not found"
                    }), 404
                
                reference_data = json.loads(dataset['reference_data'])
                
                if 'source_sentences' not in reference_data:
                    return jsonify({
                        "success": False,
                        "error": f"Dataset '{dataset_name}' does not have source sentences"
                    }), 400
                
                all_source_sentences = reference_data['source_sentences']
                total_available = len(all_source_sentences)
                
                # Get requested range
                end_idx = min(start_idx + count, total_available)
                source_sentences = all_source_sentences[start_idx:end_idx]
                sentence_ids = list(range(start_idx, end_idx))
            
            return jsonify({
                "success": True,
                "source_sentences": source_sentences,
                "sentence_ids": sentence_ids,
                "dataset": dataset_name,
                "total_available": total_available
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error in get_source_sentences: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@app.route('/public/submit_model', methods=['POST'])
def submit_model():
    """
    Submit a model's results to a benchmark dataset for evaluation
    
    Expected JSON input:  
    {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "my-model-v1", 
        "modelResults": ["Traducción 1", "Traducción 2", ...],
        "sentence_ids": [0, 1, 2, 3, 4]  // Required: specify which FLORES+ sentences were translated
    }
    
    Returns:
    {
        "success": true/false,
        "bleu_score": 0.543,
        "submission_id": 123,
        "evaluation_details": {...},
        "error": "error message if any"
    }
    """
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        benchmark_dataset_name = data.get('benchmarkDatasetName')
        model_name = data.get('modelName')
        model_results = data.get('modelResults')
        sentence_ids = data.get('sentence_ids')  # Optional: specific FLORES+ sentence positions
        
                # Validate required fields
        if not all([benchmark_dataset_name, model_name, model_results, sentence_ids]):
            return jsonify({
                "success": False,
                "error": "Missing required fields: benchmarkDatasetName, modelName, modelResults, sentence_ids"
            }), 400
        
        if not isinstance(model_results, list):
            return jsonify({
                "success": False,
                "error": "modelResults must be a list"
            }), 400
        
        # Get database connection
        conn, cursor = get_db_connection()
        
        try:
            # Check if benchmark dataset exists
            cursor.execute(
                "SELECT id, task_type, evaluation_metric, reference_data FROM benchmark_datasets WHERE name = %s AND active = TRUE",
                (benchmark_dataset_name,)
            )
            dataset = cursor.fetchone()
            
            if not dataset:
                return jsonify({
                    "success": False,
                    "error": f"Benchmark dataset '{benchmark_dataset_name}' not found"
                }), 404
            
            dataset_id = dataset['id']
            task_type = dataset['task_type']
            evaluation_metric = dataset['evaluation_metric']
            reference_data_str = dataset['reference_data']
            
            # Store model submission
            cursor.execute("""
                INSERT INTO model_submissions (benchmark_dataset_id, model_name, submitted_by, model_results)
                VALUES (%s, %s, %s, %s)
            """, (dataset_id, model_name, USER_EMAIL_API, json.dumps(model_results)))
            
            submission_id = cursor.lastrowid
            
            # Run evaluation based on the dataset type
            if task_type == 'translation' and evaluation_metric == 'bleu':
                try:
                    # Handle FLORES+ datasets (Spanish, Japanese, Arabic, Chinese, Korean)
                    flores_datasets = {
                        'flores_spanish_translation': 'spa_Latn',
                        'flores_japanese_translation': 'jpn_Jpan', 
                        'flores_arabic_translation': 'arb_Arab',
                        'flores_chinese_translation': 'cmn_Hans',
                        'flores_korean_translation': 'kor_Hang'
                    }
                    
                    if benchmark_dataset_name in flores_datasets:
                        # FLORES+ evaluation logic for all supported languages
                        # Set HF token for dataset access (environment variable approach)
                        import os
                        hf_token = os.getenv("HF_TOKEN")
                        if hf_token:
                            os.environ["HF_TOKEN"] = hf_token
                        
                        # Load FLORES+ reference sentences for the target language
                        target_lang = flores_datasets[benchmark_dataset_name]
                        target_dataset = load_dataset("openlanguagedata/flores_plus", target_lang, split="devtest")
                        
                        # Use specific sentence positions (Option C - now required)
                        if len(sentence_ids) != len(model_results):
                            return jsonify({
                                "success": False,
                                "error": "Length of sentence_ids must match length of modelResults"
                            }), 400
                        reference_sentences = [target_dataset[idx]["text"] for idx in sentence_ids]
                        
                    else:
                        # Custom dataset evaluation logic
                        # Parse the reference data from database
                        reference_data = json.loads(reference_data_str)
                        
                        if 'reference_translations' not in reference_data:
                            return jsonify({
                                "success": False,
                                "error": "Dataset does not have reference translations"
                            }), 400
                        
                        all_reference_sentences = reference_data['reference_translations']
                        
                        # Use sentence_ids to get specific reference sentences
                        if len(sentence_ids) != len(model_results):
                            return jsonify({
                                "success": False,
                                "error": "Length of sentence_ids must match length of modelResults"
                            }), 400
                        
                        # Validate sentence_ids are within bounds
                        max_id = len(all_reference_sentences) - 1
                        for sid in sentence_ids:
                            if sid < 0 or sid > max_id:
                                return jsonify({
                                    "success": False,
                                    "error": f"sentence_id {sid} is out of range (0-{max_id})"
                                }), 400
                        
                        reference_sentences = [all_reference_sentences[idx] for idx in sentence_ids]
                    
                    # Calculate real BLEU score using Angela's function
                    bleu_score = get_bleu(model_results, reference_sentences)
                    
                    # No evaluation details needed for spec compliance
                    score = bleu_score
                    
                except Exception as e:
                    print(f"BLEU evaluation failed: {str(e)}")
                    return jsonify({
                        "success": False,
                        "error": "BLEU evaluation failed"
                    }), 500
            else:
                return jsonify({
                    "success": False,
                    "error": "Only translation tasks with BLEU metric supported"
                }), 400
            
            # Store evaluation result (simplified)
            cursor.execute("""
                INSERT INTO evaluation_results (model_submission_id, score, evaluation_details)
                VALUES (%s, %s, %s)
            """, (submission_id, score, json.dumps({"metric": "bleu"})))
            
            # Commit the transaction
            conn.commit()
            
             # Return spec-compliant response: success boolean + score
            return jsonify({
                "success": True,
                "score": score
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error in submit_model: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@app.route('/public/add_dataset_to_leaderboard', methods=['POST'])
def add_dataset_to_leaderboard():
    """
    Add a new benchmark dataset to the leaderboard
    
    Expected form data:
    - dataset_name: string - unique name for the dataset
    - description: string - optional description  
    - task_type: string - e.g., 'translation', 'classification', 'qa'
    - evaluation_metric: string - e.g., 'bleu', 'accuracy', 'f1'
    - dataset_file: file - CSV/JSON file with reference data
    
    Returns:
    {
        "success": true/false,
        "dataset_id": integer,
        "error": "error message if any"
    }
    """
    try:
        # Get form data
        dataset_name = request.form.get('dataset_name')
        description = request.form.get('description', '')
        task_type = request.form.get('task_type')
        evaluation_metric = request.form.get('evaluation_metric')
        
        # Validate required fields
        if not dataset_name or not task_type or not evaluation_metric:
            return jsonify({
                "success": False,
                "error": "Missing required fields: dataset_name, task_type, evaluation_metric"
            }), 400
        
        # Validate task_type and evaluation_metric combinations
        valid_combinations = {
            'translation': ['bleu', 'meteor', 'rouge'],
            'classification': ['accuracy', 'f1', 'precision', 'recall'],
            'qa': ['exact_match', 'f1', 'bleu'],
            'summarization': ['rouge', 'bleu']
        }
        
        if task_type not in valid_combinations:
            return jsonify({
                "success": False,
                "error": f"Unsupported task_type: {task_type}. Supported: {list(valid_combinations.keys())}"
            }), 400
            
        if evaluation_metric not in valid_combinations[task_type]:
            return jsonify({
                "success": False,
                "error": f"Invalid evaluation_metric '{evaluation_metric}' for task_type '{task_type}'. Valid options: {valid_combinations[task_type]}"
            }), 400
        
        # Get uploaded file
        if 'dataset_file' not in request.files:
            return jsonify({
                "success": False,
                "error": "No dataset_file provided"
            }), 400
            
        dataset_file = request.files['dataset_file']
        if dataset_file.filename == '':
            return jsonify({
                "success": False,
                "error": "No dataset_file selected"
            }), 400
        
        # Process the dataset file
        try:
            reference_data = process_dataset_file(dataset_file, task_type)
        except ValueError as e:
            return jsonify({
                "success": False,
                "error": f"Invalid dataset file: {str(e)}"
            }), 400
        
        # Save to database
        conn, cursor = get_db_connection()
        
        try:
            # Check if dataset name already exists
            cursor.execute("""
                SELECT id FROM benchmark_datasets WHERE name = %s
            """, (dataset_name,))
            
            if cursor.fetchone():
                return jsonify({
                    "success": False,
                    "error": f"Dataset with name '{dataset_name}' already exists"
                }), 400
            
            # Insert new dataset
            cursor.execute("""
                INSERT INTO benchmark_datasets 
                (name, description, task_type, evaluation_metric, reference_data)
                VALUES (%s, %s, %s, %s, %s)
            """, (dataset_name, description, task_type, evaluation_metric, json.dumps(reference_data)))
            
            dataset_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({
                "success": True,
                "dataset_id": dataset_id
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error in add_dataset_to_leaderboard: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

def process_dataset_file(file_storage, task_type):
    """
    Process uploaded dataset file and extract reference data
    
    Returns:
    - For translation: {"source_sentences": [...], "reference_translations": [...]}
    - For classification: {"texts": [...], "labels": [...]}  
    - For qa: {"questions": [...], "answers": [...], "contexts": [...]}
    """
    filename = secure_filename(file_storage.filename)
    ext = os.path.splitext(filename)[1].lower()
    
    file_storage.seek(0)
    
    if ext == ".csv":
        import pandas as pd
        df = pd.read_csv(file_storage)
        
        if task_type == 'translation':
            # Expected columns: source, target (or source_text, target_text)
            source_col = None
            target_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ['source', 'source_text', 'source_sentence']:
                    source_col = col
                elif col_lower in ['target', 'target_text', 'reference', 'reference_translation']:
                    target_col = col
            
            if not source_col or not target_col:
                raise ValueError(f"Translation dataset must have source and target columns. Found columns: {list(df.columns)}")
            
            return {
                "source_sentences": df[source_col].tolist(),
                "reference_translations": df[target_col].tolist()
            }
            
        elif task_type == 'classification':
            # Expected columns: text, label
            text_col = None
            label_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ['text', 'sentence', 'document']:
                    text_col = col
                elif col_lower in ['label', 'class', 'category']:
                    label_col = col
            
            if not text_col or not label_col:
                raise ValueError(f"Classification dataset must have text and label columns. Found columns: {list(df.columns)}")
            
            return {
                "texts": df[text_col].tolist(),
                "labels": df[label_col].tolist()
            }
            
        elif task_type == 'qa':
            # Expected columns: question, answer, context (optional)
            question_col = None
            answer_col = None
            context_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in ['question', 'query']:
                    question_col = col
                elif col_lower in ['answer', 'response']:
                    answer_col = col
                elif col_lower in ['context', 'passage', 'document']:
                    context_col = col
            
            if not question_col or not answer_col:
                raise ValueError(f"QA dataset must have question and answer columns. Found columns: {list(df.columns)}")
            
            result = {
                "questions": df[question_col].tolist(),
                "answers": df[answer_col].tolist()
            }
            
            if context_col:
                result["contexts"] = df[context_col].tolist()
            
            return result
            
        else:
            raise ValueError(f"Unsupported task_type for CSV: {task_type}")
            
    elif ext == ".json":
        import json
        data = json.load(file_storage)
        
        # Validate JSON structure based on task_type
        if task_type == 'translation':
            if not isinstance(data, dict) or 'source_sentences' not in data or 'reference_translations' not in data:
                raise ValueError("Translation JSON must have 'source_sentences' and 'reference_translations' keys")
            return data
            
        elif task_type == 'classification':
            if not isinstance(data, dict) or 'texts' not in data or 'labels' not in data:
                raise ValueError("Classification JSON must have 'texts' and 'labels' keys")
            return data
            
        elif task_type == 'qa':
            if not isinstance(data, dict) or 'questions' not in data or 'answers' not in data:
                raise ValueError("QA JSON must have 'questions' and 'answers' keys")
            return data
            
        else:
            raise ValueError(f"Unsupported task_type for JSON: {task_type}")
    
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported: .csv, .json")

@app.route('/public/get_leaderboard', methods=['GET'])
def get_leaderboard():
    """
    Get leaderboard showing model submissions and scores for a dataset
    
    Query parameters:
    - dataset: benchmark dataset name (optional, shows all if not specified)
    - limit: number of results to return (default: 10)
    
    Returns:
    {
        "success": true,
        "leaderboard": [
            {
                "rank": 1,
                "model_name": "model-v1",
                "score": 0.95,
                "dataset_name": "test_spanish_translation",
                "task_type": "translation",
                "evaluation_metric": "bleu",
                "submitted_at": "2025-01-08T12:34:56Z"
            }
        ]
    }
    """
    try:
        dataset_name = request.args.get('dataset')
        limit = int(request.args.get('limit', 100))  # Increased from 10 to 100 to show more results per dataset
        
        conn, cursor = get_db_connection()
        
        try:
            if dataset_name:
                # Get leaderboard for specific dataset
                query = """
                    SELECT 
                        ms.model_name,
                        bd.name as dataset_name,
                        bd.task_type,
                        bd.evaluation_metric,
                        er.score,
                        ms.created as submitted_at
                    FROM model_submissions ms
                    JOIN benchmark_datasets bd ON ms.benchmark_dataset_id = bd.id
                    JOIN evaluation_results er ON er.model_submission_id = ms.id
                    WHERE bd.name = %s AND bd.active = TRUE
                    ORDER BY er.score DESC
                    LIMIT %s
                """
                cursor.execute(query, (dataset_name, limit))
            else:
                # Get leaderboard for all datasets
                query = """
                    SELECT 
                        ms.model_name,
                        bd.name as dataset_name,
                        bd.task_type,
                        bd.evaluation_metric,
                        er.score,
                        ms.created as submitted_at
                    FROM model_submissions ms
                    JOIN benchmark_datasets bd ON ms.benchmark_dataset_id = bd.id
                    JOIN evaluation_results er ON er.model_submission_id = ms.id
                    WHERE bd.active = TRUE
                    ORDER BY bd.name, er.score DESC
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            
            results = cursor.fetchall()
            
            # Add ranking
            leaderboard = []
            for i, row in enumerate(results):
                leaderboard.append({
                    "rank": i + 1,
                    "model_name": row['model_name'],
                    "dataset_name": row['dataset_name'],
                    "task_type": row['task_type'],
                    "evaluation_metric": row['evaluation_metric'],
                    "score": float(row['score']),
                    "submitted_at": row['submitted_at'].isoformat() if row['submitted_at'] else None
                })
            
            return jsonify({
                "success": True,
                "leaderboard": leaderboard
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error in get_leaderboard: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@app.route('/api/companies', methods=['GET'])
def get_companies():
    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT id, name, path FROM companies")
    companies = cursor.fetchall()
    cursor.close()
    return jsonify(companies)


def get_user_from_token(token):
    if not token:
        return None

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT * FROM users WHERE session_token = %s
    """, (token,))
    user = cursor.fetchone()

    if user and user.get("session_token_expiration"):
        # session_token_expiration is usually stored as a datetime string
        expiration = user["session_token_expiration"]
        # Convert expiration string to datetime object (assuming ISO format)
        expiration_dt = datetime.strptime(expiration, "%Y-%m-%d %H:%M:%S")
        if expiration_dt > datetime.utcnow():
            return user
    return None


@app.route("/api/user/companies", methods=["GET"])
@jwt_required()
def get_user_companies():
    user_email = get_jwt_identity()

    cursor = mysql.connection.cursor(dictionary=True)

    # Get user ID from email
    cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        return jsonify({"error": "Invalid user"}), 401

    user_id = user["id"]

    # Get companies for this user
    cursor.execute("SELECT name, path FROM user_company_chatbots WHERE user_id = %s", (user_id,))
    companies = cursor.fetchall()

    cursor.close()
    return jsonify(companies)

# translate with gpt
def translate_gpt(prompt):
    from openai import OpenAI
    import os
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful translator."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

# calculate BLEU score
def get_bleu(translations, references, weights=(0.5, 0.5, 0, 0)):
    bleu_scores = [
        sentence_bleu([ref.split()], trans.split(), weights=weights)
        for ref, trans in zip(references, translations)
    ]
    return sum(bleu_scores) / len(bleu_scores)

@app.route('/multi-language-gpt-evaluation', methods=['POST'])
@cross_origin(supports_credentials=True)
def multi_language_gpt_evaluation():
    """
    Multi-language GPT evaluation endpoint
    Supports Spanish, Japanese, Arabic, Chinese, and Korean translations
    
    Expected JSON payload:
    {
        "language": "spanish|japanese|arabic|chinese|korean",
        "count": 5
    }
    
    Returns:
    {
        "success": true,
        "bleu_score": 0.65,
        "translations": [...],
        "references": [...],
        "source_sentences": [...],
        "language": "spanish",
        "dataset_name": "flores_spanish_translation"
    }
    """
    try:
        # get request data
        data = request.get_json()
        language = data.get('language', 'spanish').lower()
        count = data.get('count', 5)

        # Language mapping
        language_configs = {
            'spanish': {
                'target_lang': 'spa_Latn',
                'prompt_lang': 'Spanish',
                'dataset_name': 'flores_spanish_translation'
            },
            'japanese': {
                'target_lang': 'jpn_Jpan',
                'prompt_lang': 'Japanese',
                'dataset_name': 'flores_japanese_translation'
            },
            'arabic': {
                'target_lang': 'arb_Arab',
                'prompt_lang': 'Arabic',
                'dataset_name': 'flores_arabic_translation'
            },
            'chinese': {
                'target_lang': 'cmn_Hans',
                'prompt_lang': 'Chinese',
                'dataset_name': 'flores_chinese_translation'
            },
            'korean': {
                'target_lang': 'kor_Hang',
                'prompt_lang': 'Korean',
                'dataset_name': 'flores_korean_translation'
            }
        }
        
        if language not in language_configs:
            return jsonify({
                "success": False,
                "error": f"Unsupported language: {language}. Supported: {list(language_configs.keys())}"
            }), 400

        config = language_configs[language]
        
        # Set HF token for dataset access
        import os
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            os.environ["HF_TOKEN"] = hf_token

        # load datasets
        source_lang = "eng_Latn"
        target_lang = config['target_lang']
        source_dataset = load_dataset("openlanguagedata/flores_plus", source_lang, split="devtest")
        target_dataset = load_dataset("openlanguagedata/flores_plus", target_lang, split="devtest")

        # compile sentences into lists
        source_sentences = [ex["text"] for ex in source_dataset.select(range(count))]
        reference_sentences = [ex["text"] for ex in target_dataset.select(range(count))]

        # generate gpt translations from benchmark source sentences
        gpt_translations = []
        for sentence in source_sentences:
            prompt = f"Translate this sentence to {config['prompt_lang']}:\n\n{sentence}"
            translation = translate_gpt(prompt)
            gpt_translations.append(translation)
            time.sleep(1)

        bleu_score = get_bleu(gpt_translations, reference_sentences)

        # return results as json
        return jsonify({
            "success": True,
            "bleu_score": bleu_score,
            "translations": gpt_translations,
            "references": reference_sentences,
            "source_sentences": source_sentences,
            "language": language,
            "dataset_name": config['dataset_name']
        })

    except Exception as e:
        print("Error:", str(e))
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/spanish-gpt-evaluation', methods=['POST'])
@cross_origin(supports_credentials=True)
def spanish_gpt_evaluation():
    try:
        # get number of sentences to translate
        data = request.get_json()
        count = data.get('count', 10)

        # load datasets
        source_lang = "eng_Latn"
        target_lang = "spa_Latn"
        source_dataset = load_dataset("openlanguagedata/flores_plus", source_lang, split="devtest")
        target_dataset = load_dataset("openlanguagedata/flores_plus", target_lang, split="devtest")

        # compile sentences into lists
        source_sentences = [ex["text"] for ex in source_dataset.select(range(count))]
        reference_sentences = [ex["text"] for ex in target_dataset.select(range(count))]

        # generate gpt translations from benchmark source sentences
        spa_gpt_translations = []
        for sentence in source_sentences:
            prompt = f"Translate this sentence to Spanish:\n\n{sentence}"
            translation = translate_gpt(prompt)
            spa_gpt_translations.append(translation)
            time.sleep(1)

        bleu_score = get_bleu(spa_gpt_translations, reference_sentences)

        # return results as json
        return jsonify({
            "bleu_score": bleu_score,
            "translations": spa_gpt_translations,
            "references": reference_sentences
        })

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

api = Blueprint('api', __name__)
app.register_blueprint(api)

if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
