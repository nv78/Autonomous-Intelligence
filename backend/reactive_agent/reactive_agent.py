from langchain_community.llms import OpenAI
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import ray
import openai
import datetime
import shutil
import time
import numpy as np
import PyPDF2
import uuid
from sec_api import QueryApi, RenderApi
import requests
from flask import jsonify

# from openai import OpenAI

# """Module for fetching data from the SEC EDGAR Archives"""
import json
import os
import re
import uuid
from flask import jsonify
import requests
import webbrowser
from fpdf import FPDF
from typing import List, Optional, Tuple, Union
from ratelimit import limits, sleep_and_retry
import anthropic
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
import sys
if sys.version_info < (3, 8):
    from typing_extensions import Final
else:
    from typing import Final

from database.db import get_db_connection
from tika import parser as p


load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
API_KEY = os.getenv('OPENAI_API_KEY')
embeddings = OpenAIEmbeddings(api_key=API_KEY)
sec_api_key = os.getenv('SEC_API_KEY')

MAX_CHUNK_SIZE = 1000

from api_endpoints.financeGPT.chatbot_endpoints import add_prompt_to_workflow_db, add_workflow_to_db, \
    add_chat_to_db, add_message_to_db, chunk_document, get_text_from_single_file, add_document_to_db, get_relevant_chunks


# Reactive Agent System
class ReactiveAgent:
    def __init__(self, chat_id, user_email, model_type="gpt-4o-mini"):
        self.chat_id = chat_id
        self.user_email = user_email
        self.model_type = model_type
        self.conversation_history = []
        self.agent_state = {
            "context": {},
            "active_tools": [],
            "last_action": None,
            "memory": []
        }
        self.available_tools = {
            "search_documents": self.search_documents,
            "analyze_sentiment": self.analyze_sentiment,
            "summarize_conversation": self.summarize_conversation,
            "get_relevant_info": self.get_relevant_info
        }
    
    def search_documents(self, query):
        """Search through uploaded documents for relevant information"""
        try:
            sources = get_relevant_chunks(3, query, self.chat_id, self.user_email)
            if sources:
                return f"Found relevant information: {' '.join([str(source[0]) for source in sources[:2]])}"
            return "No relevant documents found."
        except:
            return "Document search is not available for this chat."
    
    def analyze_sentiment(self, text):
        """Analyze the sentiment of the given text"""
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": f"Analyze the sentiment of this text and return only 'positive', 'negative', or 'neutral': {text}"}
                ]
            )
            return completion.choices[0].message.content.strip().lower()
        except:
            return "neutral"
    
    def summarize_conversation(self):
        """Summarize the current conversation"""
        if len(self.conversation_history) < 2:
            return "Conversation just started, no summary needed yet."
        
        recent_messages = self.conversation_history[-6:] if len(self.conversation_history) > 6 else self.conversation_history
        conversation_text = " ".join([f"{'User' if msg['role'] == 'user' else 'chatbot'}: {msg['content']}" for msg in recent_messages])
        
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": f"Summarize this conversation in 2-3 sentences: {conversation_text}"}
                ]
            )
            return completion.choices[0].message.content
        except:
            return "Unable to summarize conversation at this time."
    
    def get_relevant_info(self, topic):
        """Get relevant information about a specific topic from the conversation"""
        relevant_messages = [msg['content'] for msg in self.conversation_history if topic.lower() in msg['content'].lower()]
        if relevant_messages:
            return f"Found {len(relevant_messages)} mentions of '{topic}' in our conversation."
        return f"No previous discussion about '{topic}' found."
    
    def should_use_tool(self, user_input):
        """Determine if the agent should use a tool based on user input"""
        tool_triggers = {
            "search_documents": ["search", "find", "document", "look up", "information about"],
            "analyze_sentiment": ["how do you feel", "sentiment", "emotion", "mood"],
            "summarize_conversation": ["summarize", "summary", "recap", "what have we discussed"],
            "get_relevant_info": ["tell me about", "what did we say about", "previous mention"]
        }
        
        user_input_lower = user_input.lower()
        for tool, triggers in tool_triggers.items():
            if any(trigger in user_input_lower for trigger in triggers):
                return tool
        return None
    
    def execute_tool(self, tool_name, user_input):
        """Execute a specific tool with the user input"""
        if tool_name in self.available_tools:
            if tool_name == "search_documents":
                return self.available_tools[tool_name](user_input)
            elif tool_name == "analyze_sentiment":
                return self.available_tools[tool_name](user_input)
            elif tool_name == "summarize_conversation":
                return self.available_tools[tool_name]()
            elif tool_name == "get_relevant_info":
                # Extract topic from user input
                words = user_input.lower().split()
                if "about" in words:
                    topic_index = words.index("about") + 1
                    if topic_index < len(words):
                        topic = " ".join(words[topic_index:topic_index+2])
                        return self.available_tools[tool_name](topic)
        return None
    
    def generate_response(self, user_input):
        """Generate a reactive response based on user input and conversation history"""
        # Add user input to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Check if we should use a tool
        tool_to_use = self.should_use_tool(user_input)
        tool_result = None
        
        if tool_to_use:
            tool_result = self.execute_tool(tool_to_use, user_input)
            self.agent_state["last_action"] = tool_to_use
            self.agent_state["active_tools"].append(tool_to_use)
        
        # Build the context for the AI response
        context_parts = []
        
        # Add conversation history (last 10 messages)
        recent_history = self.conversation_history[-10:] if len(self.conversation_history) > 10 else self.conversation_history
        if recent_history:
            context_parts.append(f"Recent conversation: {json.dumps(recent_history)}")
        
        # Add tool result if available
        if tool_result:
            context_parts.append(f"Tool result from {tool_to_use}: {tool_result}")
        
        # Add document context if available
        try:
            sources = get_relevant_chunks(2, user_input, self.chat_id, self.user_email)
            if sources:
                sources_str = " ".join([str(source[0]) for source in sources])
                context_parts.append(f"Relevant document context: {sources_str}")
        except:
            pass
        
        # Create the system prompt
        system_prompt = f"""You are a reactive AI assistant that adapts to user needs. You have access to conversation history and can use tools when needed.
        Current conversation context:
        {chr(10).join(context_parts)}

        Guidelines:
        1. Be conversational and natural
        2. Reference previous parts of the conversation when relevant
        3. If you used a tool, incorporate its results naturally into your response
        4. Be helpful and proactive in suggesting follow-up actions
        5. Keep responses concise but informative
        6. Show that you understand the context and flow of the conversation

        User's current message: {user_input}"""
        
        try:
            completion = client.chat.completions.create(
                model=self.model_type,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.6
            )
            
            response = completion.choices[0].message.content
            
            # Add assistant response to conversation history
            self.conversation_history.append({"role": "chatbot", "content": response})
            
            # Update agent memory
            self.agent_state["memory"].append({
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
                "tool_used": tool_to_use,
                "response_summary": response[:100] + "..." if len(response) > 100 else response
            })
            
            return response, tool_to_use, tool_result
            
        except Exception as e:
            return f"I apologize, but I encountered an error while processing your request: {str(e)}", None, None
