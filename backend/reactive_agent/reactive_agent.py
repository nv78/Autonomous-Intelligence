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
        """Enhanced search through uploaded documents with validation"""
        try:
            sources = get_relevant_chunks(3, query, self.chat_id, self.user_email)
            
            # Check if sources are valid
            if not sources or all(isinstance(source, str) and any(indicator in source.lower() for indicator in ["no text found", "no relevant", "error"]) for source in sources):
                return "No relevant documents found for your query. Please ensure you have uploaded relevant documents."
            
            # Process and format sources with confidence indicators
            formatted_sources = []
            for source in sources[:2]:  # Limit to top 2 for readability
                if isinstance(source, tuple):
                    if len(source) >= 4:  # Enhanced format with confidence
                        content, doc_name, sim_score, confidence = source[:4]
                        confidence_level = "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low"
                        formatted_sources.append(f"From {doc_name} (confidence: {confidence_level}): {content[:200]}...")
                    elif len(source) >= 2:
                        content, doc_name = source[:2]
                        formatted_sources.append(f"From {doc_name}: {content[:200]}...")
                    else:
                        formatted_sources.append(f"Document content: {str(source[0])[:200]}...")
                elif isinstance(source, str):
                    formatted_sources.append(f"Found: {source[:200]}...")
            
            if formatted_sources:
                return "Found relevant information:\\n" + "\\n\\n".join(formatted_sources)
            else:
                return "Found documents but could not extract clear information. Please try a more specific query."
                
        except Exception as e:
            print(f"[ERROR] Document search failed: {e}")
            return "Document search encountered an error. Please try rephrasing your query."
    
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
        """Generate a reactive response with enhanced document grounding"""
        # Add user input to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Check if we should use a tool
        tool_to_use = self.should_use_tool(user_input)
        tool_result = None
        
        if tool_to_use:
            tool_result = self.execute_tool(tool_to_use, user_input)
            self.agent_state["last_action"] = tool_to_use
            self.agent_state["active_tools"].append(tool_to_use)
        
        # Build enhanced context for the AI response
        context_parts = []
        
        # Add conversation history (last 8 messages for better focus)
        recent_history = self.conversation_history[-8:] if len(self.conversation_history) > 8 else self.conversation_history
        if len(recent_history) > 1:  # Only add if there's actual conversation
            formatted_history = []
            for msg in recent_history[-4:]:  # Last 4 messages for context
                role = "User" if msg["role"] == "user" else "Assistant"
                formatted_history.append(f"{role}: {msg['content'][:150]}...")
            context_parts.append(f"Recent conversation:\\n" + "\\n".join(formatted_history))
        
        # Add tool result if available
        if tool_result:
            context_parts.append(f"Tool result from {tool_to_use}:\\n{tool_result}")
        
        # Add document context if no tool was used or if search tool was used
        document_context_added = False
        if not tool_to_use or tool_to_use == "search_documents":
            try:
                sources = get_relevant_chunks(3, user_input, self.chat_id, self.user_email)
                if sources and not all(isinstance(source, str) and any(indicator in source.lower() for indicator in ["no text found", "no relevant", "error"]) for source in sources):
                    formatted_sources = []
                    for source in sources[:2]:
                        if isinstance(source, tuple) and len(source) >= 2:
                            content, doc_name = source[:2]
                            formatted_sources.append(f"From {doc_name}: {str(content)[:300]}...")
                        elif isinstance(source, str):
                            formatted_sources.append(f"Document: {source[:300]}...")
                    
                    if formatted_sources:
                        context_parts.append(f"Relevant document information:\\n" + "\\n\\n".join(formatted_sources))
                        document_context_added = True
            except Exception as e:
                print(f"[WARNING] Failed to add document context: {e}")
        
        # Enhanced system prompt with better instructions
        system_prompt = f"""You are an intelligent document assistant with access to conversation history and uploaded documents. 

CONTEXT:
{chr(10).join(context_parts) if context_parts else "No additional context available"}

INSTRUCTIONS:
1. Be conversational and helpful
2. When referencing documents, be specific about sources when possible
3. If you used a tool, naturally incorporate its results
4. If document information is available, ground your response in that information
5. If you don't have relevant information, be honest about limitations
6. Keep responses focused and informative
7. Show understanding of the conversation flow

{"Document information is available - use it to inform your response." if document_context_added else "No specific document context available - rely on conversation and general assistance."}

User message: {user_input}"""
        
        try:
            completion = client.chat.completions.create(
                model=self.model_type,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.3,  # Lower temperature for more grounded responses
                max_tokens=800
            )
            
            response = completion.choices[0].message.content
            
            # Validate response if we have document context
            if document_context_added and tool_to_use != "search_documents":
                # Basic check for grounded response
                response_lower = response.lower()
                hallucination_indicators = ["i believe", "in my opinion", "generally speaking", "typically", "usually", "based on my knowledge"]
                
                for indicator in hallucination_indicators:
                    if indicator in response_lower:
                        print(f"[WARNING] Potential hallucination detected in response: {indicator}")
                        break
            
            # Add assistant response to conversation history
            self.conversation_history.append({"role": "chatbot", "content": response})
            
            # Update agent memory with enhanced tracking
            self.agent_state["memory"].append({
                "timestamp": datetime.now().isoformat(),
                "user_input": user_input,
                "tool_used": tool_to_use,
                "document_context_used": document_context_added,
                "response_summary": response[:100] + "..." if len(response) > 100 else response
            })
            
            # Keep memory manageable
            if len(self.agent_state["memory"]) > 20:
                self.agent_state["memory"] = self.agent_state["memory"][-15:]
            
            return response, tool_to_use, tool_result
            
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error while processing your request. Please try rephrasing your question."
            print(f"[ERROR] Reactive agent response generation failed: {e}")
            return error_msg, tool_to_use, tool_result
