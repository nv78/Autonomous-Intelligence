from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from typing import Dict, List, Any, Optional, Generator, Union
import os
import time
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
    name: str = "document_retrieval"
    description: str = "Retrieve relevant document chunks based on a query for a specific chat"
    chat_id: int = Field(...)
    user_email: str = Field(...)

    def __init__(self, chat_id: int, user_email: str, **kwargs):
        super().__init__(chat_id=chat_id, user_email=user_email, **kwargs)

    def _run(self, query: str, k: int = 6) -> str:
        try:
            sources = get_relevant_chunks(k, query, self.chat_id, self.user_email)
            if not sources:
                return "No relevant documents found for this query."

            print("SOURCES:", sources)

            result = []
            for i, (chunk_text, document_name) in enumerate(sources):
                result.append(f"Document {i+1} ({document_name}): {chunk_text.strip()}")

            return "\n\n".join(result)

        except Exception as e:
            return f"Error retrieving documents: {str(e)}"

class ChatHistoryTool(BaseTool):
    name: str = "chat_history"
    description: str = "Retrieve chat history for context understanding"
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
    name: str = "document_list"
    description: str = "List all documents available in the current chat"
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
    name: str = "general_knowledge"
    description: str = "Use general LLM knowledge to answer questions when documents don't contain relevant information"
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


from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.agents import AgentAction, AgentFinish
from typing import Dict, List, Any, Optional
import re

class StreamingAgentCallbackHandler(BaseCallbackHandler):
    """Custom callback handler to capture intermediate steps for streaming"""

    def __init__(self, stream_callback):
        super().__init__()
        self.stream_callback = stream_callback
        self.intermediate_steps = []

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """Called when LLM starts generating"""
        try:
            self.stream_callback({
                "type": "llm_start",
                "message": "LLM is thinking...",
                "model": serialized.get("name", "unknown_model"),
                "timestamp": self._get_timestamp()
            })
        except Exception as e:
            print(f"Error in llm_start callback: {e}")

    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any
    ) -> None:
        """Called when LLM finishes generating"""
        try:
            # Extract the LLM's raw output/reasoning
            if response.generations and len(response.generations) > 0:
                generation = response.generations[0][0]
                llm_output = generation.text

                # Parse the reasoning from the LLM output
                thought_match = re.search(r'Thought:\s*(.*?)(?=\nAction:|$)', llm_output, re.DOTALL)
                action_match = re.search(r'Action:\s*(.*?)(?=\nAction Input:|$)', llm_output, re.DOTALL)

                self.stream_callback({
                    "type": "llm_reasoning",
                    "raw_output": llm_output[:500] + "..." if len(llm_output) > 500 else llm_output,
                    "thought": thought_match.group(1).strip() if thought_match else None,
                    "planned_action": action_match.group(1).strip() if action_match else None,
                    "timestamp": self._get_timestamp()
                })
        except Exception as e:
            print(f"Error in llm_end callback: {e}")

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Called when a chain starts"""
        try:
            chain_name = serialized.get("name", "unknown_chain")
            if chain_name != "AgentExecutor":  # Avoid too much noise
                self.stream_callback({
                    "type": "chain_start",
                    "chain_name": chain_name,
                    "inputs": str(inputs)[:200] + "..." if len(str(inputs)) > 200 else str(inputs),
                    "timestamp": self._get_timestamp()
                })
        except Exception as e:
            print(f"Error in chain_start callback: {e}")

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """Called when a tool starts running"""
        tool_name = serialized.get("name", "unknown_tool")
        try:
            self.stream_callback({
                "type": "tool_start",
                "tool_name": tool_name,
                "input": input_str,
                "message": f"Using tool: {tool_name}",
                "timestamp": self._get_timestamp()
            })
        except Exception as e:
            print(f"Error in tool_start callback: {e}")

    def on_tool_end(
        self,
        output: str,
        **kwargs: Any
    ) -> None:
        """Called when a tool finishes running"""
        try:
            self.stream_callback({
                "type": "tool_end",
                "output": output[:300] + "..." if len(str(output)) > 300 else str(output),
                "message": "Tool execution completed",
                "timestamp": self._get_timestamp()
            })
        except Exception as e:
            print(f"Error in tool_end callback: {e}")

    def on_agent_action(
        self,
        action: AgentAction,
        **kwargs: Any
    ) -> None:
        """Called when agent decides on an action"""
        try:
            # Extract detailed reasoning from the action log
            action_log = getattr(action, 'log', '')

            # Parse different parts of the reasoning
            thought_match = re.search(r'Thought:\s*(.*?)(?=\nAction:|$)', action_log, re.DOTALL)
            action_match = re.search(r'Action:\s*(.*?)(?=\nAction Input:|$)', action_log, re.DOTALL)
            action_input_match = re.search(r'Action Input:\s*(.*?)(?=\nObservation:|$)', action_log, re.DOTALL)

            self.stream_callback({
                "type": "agent_thinking",
                "thought": thought_match.group(1).strip() if thought_match else "Thinking...",
                "action": action.tool,
                "action_input": str(action.tool_input),
                "reasoning": action_log[:400] + "..." if len(action_log) > 400 else action_log,
                "message": f"Agent decided to use: {action.tool}",
                "timestamp": self._get_timestamp()
            })
        except Exception as e:
            print(f"Error in agent_action callback: {e}")

    def on_agent_finish(
        self,
        finish: AgentFinish,
        **kwargs: Any
    ) -> None:
        """Called when agent finishes"""
        try:
            # Extract the final reasoning
            finish_log = getattr(finish, 'log', '')
            final_thought_match = re.search(r'Thought:\s*(.*?)(?=\nFinal Answer:|$)', finish_log, re.DOTALL)

            self.stream_callback({
                "type": "agent_finish",
                "output": finish.return_values.get("output", ""),
                "final_thought": final_thought_match.group(1).strip() if final_thought_match else None,
                "reasoning": finish_log[:400] + "..." if len(finish_log) > 400 else finish_log,
                "message": "Agent reached final conclusion",
                "timestamp": self._get_timestamp()
            })
        except Exception as e:
            print(f"Error in agent_finish callback: {e}")

    def on_text(
        self,
        text: str,
        **kwargs: Any
    ) -> None:
        """Called when there's text output (verbose thoughts)"""
        try:
            # Filter out empty or system messages
            if text.strip() and not text.startswith("Entering") and not text.startswith("Finished"):
                self.stream_callback({
                    "type": "verbose_text",
                    "text": text.strip(),
                    "timestamp": self._get_timestamp()
                })
        except Exception as e:
            print(f"Error in text callback: {e}")

    @staticmethod
    def _get_timestamp():
        import time
        return time.time()


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
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                streaming=True  # Enable streaming for OpenAI
            )
        else:  # Anthropic/Claude
            return ChatAnthropic(
                model="claude-3-sonnet-20240229",
                temperature=AgentConfig.AGENT_TEMPERATURE,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                streaming=True  # Enable streaming for Anthropic
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

        agent = create_react_agent(self.llm, tools, prompt, stop_sequence=["Observation:"])
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,  # Always enable verbose for streaming
            max_iterations=AgentConfig.AGENT_MAX_ITERATIONS,
            handle_parsing_errors=True,
            return_intermediate_steps=True  # Important for capturing reasoning
        )

    def process_query_stream(self, query: str, chat_id: int, user_email: str) -> Generator[Dict[str, Any], None, None]:
        """
        Streamable version of process_query that yields intermediate results and final response
        """
        try:
            # Create agent for this specific chat context
            agent_executor = self._create_agent(chat_id, user_email)

            # Add user message to database
            add_message_to_db(query, chat_id, 1)

            # Yield initial status
            yield {
                "type": "start",
                "message": "Processing your query...",
                "timestamp": self._get_timestamp()
            }

            # Track intermediate steps and current answer
            intermediate_steps = []
            current_answer = ""

            # Create a list to collect streaming events
            streaming_events = []

            # Track the final reasoning steps as built by frontend logic
            final_reasoning_steps = []

            # Create a callback to capture streaming events
            def stream_callback(event):
                streaming_events.append(event)

            try:
                # Process the query with callbacks
                callback_handler = StreamingAgentCallbackHandler(stream_callback)

                response = agent_executor.invoke(
                    {"input": query},
                    config={"callbacks": [callback_handler]}
                )

                # Yield any streaming events that were captured
                for event in streaming_events:
                    yield event

                # Extract the final answer
                answer = response.get("output", "I couldn't process your query.")

                # Yield thinking/processing updates from intermediate steps
                intermediate_steps = response.get("intermediate_steps", [])
                if intermediate_steps:
                    for i, (action, observation) in enumerate(intermediate_steps):
                        yield {
                            "type": "tool_execution",
                            "step": i + 1,
                            "tool": getattr(action, 'tool', 'unknown_tool'),
                            "input": str(getattr(action, 'tool_input', '')),
                            "output": str(observation)[:200] + "..." if len(str(observation)) > 200 else str(observation),
                            "timestamp": self._get_timestamp()
                        }

                # Yield final answer
                yield {
                    "type": "final_answer",
                    "answer": answer,
                    "timestamp": self._get_timestamp()
                }

                # Add bot message to database
                print("*"*50)

                # Build reasoning steps using same logic as frontend
                for event_data in streaming_events:
                    if event_data.get('type') == 'tool_start' or event_data.get('type') == 'tools_start':
                        # Add reasoning step for tool start
                        tool_start_step = {
                            'id': f'step-{int(time.time() * 1000)}',
                            'type': event_data['type'],
                            'tool_name': event_data.get('tool_name', ''),
                            'message': f"Using {event_data.get('tool_name', 'tool')}...",
                            'timestamp': int(time.time() * 1000)
                        }
                        final_reasoning_steps.append(tool_start_step)

                    elif event_data.get('type') == 'tool_end':
                        # Update the last tool step with output (same as frontend logic)
                        last_tool_index = -1
                        for i in range(len(final_reasoning_steps) - 1, -1, -1):
                            if final_reasoning_steps[i]['type'] in ['tool_start', 'tools_start']:
                                last_tool_index = i
                                break

                        if last_tool_index != -1:
                            final_reasoning_steps[last_tool_index].update({
                                'tool_output': event_data.get('output', ''),
                                'message': 'Tool execution completed'
                            })

                    elif event_data.get('type') == 'agent_thinking':
                        # Add thinking step
                        thinking_step = {
                            'id': f'step-{int(time.time() * 1000)}',
                            'type': event_data['type'],
                            'agent_thought': event_data.get('thought', ''),
                            'planned_action': event_data.get('action', ''),
                            'message': 'Planning next step...',
                            'timestamp': int(time.time() * 1000)
                        }
                        final_reasoning_steps.append(thinking_step)

                # Try to extract sources from the agent's reasoning
                sources = self._extract_sources_from_response(response, chat_id, user_email, query)

                # Extract final thought from streaming events if available
                final_thought = None
                for event in reversed(streaming_events):
                    if event.get('type') == 'llm_reasoning' and event.get('thought'):
                        final_thought = event['thought']
                        break

                # Create the complete step for database storage
                complete_step = {
                    'id': f'step-{int(time.time() * 1000)}',
                    'type': 'step-complete',
                    'answer': answer,
                    'sources': sources if sources else [],
                    'thought': final_thought,
                    'message': 'Query processing completed',
                    'timestamp': int(time.time() * 1000)
                }
                yield complete_step
                final_reasoning_steps.append(complete_step)

                # Convert reasoning steps to JSON string for database storage
                reasoning_json = json.dumps(final_reasoning_steps) if final_reasoning_steps else None
                print(f"Saving reasoning steps: {len(final_reasoning_steps)} steps")

                # Save to database with complete reasoning steps
                message_id = add_message_to_db(answer, chat_id, 0, reasoning_json)

                if sources and message_id:
                    try:
                        add_sources_to_db(message_id, sources)
                    except Exception as e:
                        print(f"Error adding sources to db: {e}")

                # Yield final result with metadata (reuse the complete_step data)
                yield {
                    "type": "complete",
                    "answer": answer,
                    "message_id": message_id,
                    "sources": sources if sources else [],
                    "thought": final_thought,
                    "agent_reasoning": response.get("intermediate_steps", []),
                    "timestamp": self._get_timestamp()
                }

            except Exception as e:
                error_msg = f"Agent processing error: {str(e)}"
                print(f"Agent error: {e}")  # Debug logging
                yield {
                    "type": "error",
                    "error": error_msg,
                    "timestamp": self._get_timestamp()
                }

        except Exception as e:
            error_msg = f"Agent initialization error: {str(e)}"
            message_id = add_message_to_db(error_msg, chat_id, 0)
            print(f"Initialization error: {e}")  # Debug logging
            yield {
                "type": "error",
                "error": error_msg,
                "message_id": message_id,
                "timestamp": self._get_timestamp()
            }

    def process_query(self, query: str, chat_id: int, user_email: str) -> Dict[str, Any]:
        """
        Non-streaming version (original method) - kept for backward compatibility
        """
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
            print(f"Agent processing error: {e}")  # Log the detailed error server-side
            generic_error_msg = "An internal error has occurred."
            message_id = add_message_to_db(generic_error_msg, chat_id, 0)
            return {
                "answer": generic_error_msg,
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

    @staticmethod
    def _get_timestamp():
        import time
        return time.time()


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