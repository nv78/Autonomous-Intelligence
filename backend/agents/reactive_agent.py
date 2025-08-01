from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from typing import Dict, List, Any, Optional
import os
from pydantic import BaseModel, Field
import json
import requests
from database.db import get_db_connection
from api_endpoints.financeGPT.chatbot_endpoints import (
    get_relevant_chunks, add_message_to_db, add_sources_to_db,
    retrieve_message_from_db, retrieve_docs_from_db
)
from .config import AgentConfig


class DocumentRetrievalTool(BaseTool):
    name = "document_retrieval"
    description = "Retrieve relevant document chunks based on a query for a specific chat"
    chat_id: int = Field(...)
    user_email: str = Field(...)
    
    def __init__(self, chat_id: int, user_email: str, **kwargs):
        super().__init__(chat_id=chat_id, user_email=user_email, **kwargs)
    
    def _run(self, query: str, k: int = 6) -> str:
        try:
            sources = get_relevant_chunks(k, query, self.chat_id, self.user_email)
            if not sources or sources == ["No text found"]:
                return "No relevant documents found for this query."
            
            result = []
            for i, (chunk_text, document_name) in enumerate(sources):
                result.append(f"Document {i+1} ({document_name}): {chunk_text}")
            
            return "\n\n".join(result)
        except Exception as e:
            return f"Error retrieving documents: {str(e)}"


class ChatHistoryTool(BaseTool):
    name = "chat_history"
    description = "Retrieve chat history for context understanding"
    chat_id: int = Field(...)
    user_email: str = Field(...)
    
    def __init__(self, chat_id: int, user_email: str, **kwargs):
        super().__init__(chat_id=chat_id, user_email=user_email, **kwargs)
    
    def _run(self, limit: int = 5) -> str:
        try:

            data = json.loads(limit)
            limit = int(data.get("n", 5))

            messages = retrieve_message_from_db(self.user_email, self.chat_id, 0)
            if not messages:
                return "No chat history found."
            
            recent_messages = messages[-limit*2:] if len(messages) > limit*2 else messages
            
            history = []
            for msg in recent_messages:
                role = "User" if msg['sent_from_user'] == 1 else "Assistant"
                history.append(f"{role}: {msg['message_text']}")
            
            return "\n".join(history)
        except Exception as e:
            return f"Error retrieving chat history: {str(e)}"


class DocumentListTool(BaseTool):
    name = "document_list"
    description = "List all documents available in the current chat"
    chat_id: int = Field(...)
    user_email: str = Field(...)
    
    def __init__(self, chat_id: int, user_email: str, **kwargs):
        super().__init__(chat_id=chat_id, user_email=user_email, **kwargs)
    
    def _run(self, dummy: str = "") -> str:
        try:
            docs = retrieve_docs_from_db(self.chat_id, self.user_email)
            if not docs:
                return "No documents found in this chat."
            
            doc_list = []
            for doc in docs:
                doc_list.append(f"- {doc['document_name']} (ID: {doc['id']})")
            
            return "Available documents:\n" + "\n".join(doc_list)
        except Exception as e:
            return f"Error listing documents: {str(e)}"


class GeneralKnowledgeTool(BaseTool):
    name = "general_knowledge"
    description = "Use general LLM knowledge to answer questions when documents don't contain relevant information"
    llm: Any = Field(..., exclude=True)
    
    def __init__(self, llm, **kwargs):
        super().__init__(llm=llm, **kwargs)
    
    def _run(self, query: str) -> str:
        try:
            # Use the same LLM as the agent to provide general knowledge answers
            response = self.llm.invoke(f"Please provide a helpful and accurate answer to this question using your general knowledge: {query}")
            return f"Based on general knowledge: {response.content}"
        except Exception as e:
            return f"Error accessing general knowledge: {str(e)}"


class ReactiveDocumentAgent:
    def __init__(self, model_type: int = 0, model_key: Optional[str] = None):
        self.model_type = model_type
        self.model_key = model_key
        self.llm = self._initialize_llm()
        self.agent_executor = None
        
    def _initialize_llm(self):
        if self.model_type == 0:  # OpenAI/GPT
            model_name = self.model_key if self.model_key else "gpt-4"
            return ChatOpenAI(
                model=model_name,
                temperature=AgentConfig.AGENT_TEMPERATURE,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
        else:  # Anthropic/Claude
            return ChatAnthropic(
                model="claude-3-sonnet-20240229",
                temperature=AgentConfig.AGENT_TEMPERATURE,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
            )
    
    def _create_agent(self, chat_id: int, user_email: str) -> AgentExecutor:
        tools = [
            DocumentRetrievalTool(chat_id, user_email),
            ChatHistoryTool(chat_id, user_email),
            DocumentListTool(chat_id, user_email),
        ]
        
        # Add general knowledge tool if enabled
        if AgentConfig.is_general_knowledge_enabled():
            tools.append(GeneralKnowledgeTool(self.llm))
        
        # Create prompt based on whether general knowledge is enabled
        if AgentConfig.is_general_knowledge_enabled():
            prompt_template = """
            You are a helpful AI assistant that answers questions based on uploaded documents, with fallback to general knowledge when needed.
            You have access to the following tools to help you:

            {tools}

            Use the following format:

            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question

            IMPORTANT GUIDELINES:
            1. ALWAYS check if the question refers to previous conversation (words like "it", "that", "the one", "shorter", "longer", "what I said", etc.) - if so, use chat_history tool FIRST
            2. Try the document_retrieval tool to find relevant information in uploaded documents
            3. If document_retrieval returns "No relevant documents found" or the documents don't contain sufficient information to answer the question, then use the general_knowledge tool
            4. When using document information, base your answers on the documents and include document names and relevant quotes
            5. When using general knowledge, clearly indicate that the answer is based on general knowledge rather than the uploaded documents
            6. Be concise but comprehensive
            7. For follow-up questions or when context is unclear, ALWAYS use the chat_history tool
            8. You can use document_list to see what documents are available

            Question: {input}
            {agent_scratchpad}
            """
        else:
            prompt_template = """
            You are a helpful AI assistant that answers questions based on uploaded documents. 
            You have access to the following tools to help you:

            {tools}

            Use the following format:

            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question

            IMPORTANT GUIDELINES:
            1. ALWAYS check if the question refers to previous conversation (words like "it", "that", "the one", "shorter", "longer", "what I said", etc.) - if so, use chat_history tool FIRST
            2. Use the document_retrieval tool to find relevant information before answering
            3. Base your answers ONLY on the information found in the documents
            4. If no relevant information is found, say so clearly
            5. Include document names and relevant quotes in your answer
            6. Be concise but comprehensive
            7. For follow-up questions or when context is unclear, ALWAYS use the chat_history tool
            8. You can use document_list to see what documents are available

            Question: {input}
            {agent_scratchpad}
            """
        
        prompt = PromptTemplate.from_template(prompt_template)
        
        agent = create_react_agent(self.llm, tools, prompt)
        return AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=AgentConfig.ENABLE_AGENT_VERBOSE,  # Enable verbose for debugging
            max_iterations=AgentConfig.AGENT_MAX_ITERATIONS,
            handle_parsing_errors=True
        )
    
    def process_query(self, query: str, chat_id: int, user_email: str) -> Dict[str, Any]:
        try:
            # Create agent for this specific chat context
            agent_executor = self._create_agent(chat_id, user_email)
            
            # Add user message to database
            add_message_to_db(query, chat_id, 1)
            
            # Process the query with the agent
            response = agent_executor.invoke({"input": query})
            
            # Extract the final answer
            answer = response.get("output", "I couldn't process your query.")
            
            # Add bot message to database
            message_id = add_message_to_db(answer, chat_id, 0)
            
            # Try to extract sources from the agent's reasoning
            sources = self._extract_sources_from_response(response, chat_id, user_email, query)
            
            if sources and message_id:
                try:
                    add_sources_to_db(message_id, sources)
                except Exception as e:
                    print(f"Error adding sources to db: {e}")
            
            return {
                "answer": answer,
                "message_id": message_id,
                "sources": sources if sources else [],
                "agent_reasoning": response.get("intermediate_steps", [])
            }
            
        except Exception as e:
            error_msg = f"Agent processing error: {str(e)}"
            message_id = add_message_to_db(error_msg, chat_id, 0)
            return {
                "answer": error_msg,
                "message_id": message_id,
                "sources": [],
                "agent_reasoning": []
            }
    
    def _extract_sources_from_response(self, response: Dict, chat_id: int, user_email: str, query: str) -> List[tuple]:
        try:
            # Try to get sources from the document retrieval that was likely used
            sources = get_relevant_chunks(2, query, chat_id, user_email)
            if sources and sources != ["No text found"]:
                return sources
        except Exception as e:
            print(f"Error extracting sources: {e}")
        
        return []


class WorkflowReactiveAgent(ReactiveDocumentAgent):
    def __init__(self, model_type: int = 1):  # Default to Claude for workflows
        super().__init__(model_type)
    
    def process_workflow_query(self, query: str, workflow_id: int, user_email: str) -> str:
        from api_endpoints.financeGPT.chatbot_endpoints import get_relevant_chunks_wf
        from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
        
        try:
            # Get relevant chunks for workflow
            sources = get_relevant_chunks_wf(2, query, workflow_id, user_email)
            sources_str = " ".join([", ".join(str(elem) for elem in source) for source in sources])
            
            # Use Claude for workflow processing
            anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            
            completion = anthropic_client.completions.create(
                model="claude-2",
                max_tokens_to_sample=700,
                prompt=(
                    f"{HUMAN_PROMPT} "
                    f"You are a factual chatbot that answers questions about 10-K documents. "
                    f"You only answer with answers you find in the text, no outside information. "
                    f"Please address the question: {query}. "
                    f"Consider the provided text as evidence: {sources_str}. "
                    f"{AI_PROMPT}"
                )
            )
            
            return completion.completion
            
        except Exception as e:
            return f"Error processing workflow query: {str(e)}"