import React, { useState, useEffect, useRef, useCallback } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPaperPlane,
  faFile,
  faDownload,
  faShareAlt,
  faSyncAlt,
  faBrain,
  faSearch,
  faCog,
  faCheckCircle,
  faExclamationTriangle,
  faChevronDown,
  faChevronUp,
  faArrowRight,
  faInfoCircle,
  faSitemap,
  faLightbulb,
} from "@fortawesome/free-solid-svg-icons";
import "../styles/Chatbot.css";
import fetcher from "../../http/RequestConfig";
import { useLocation, useNavigate, useParams } from "react-router-dom";

const Chatbot = (props) => {
  const [message, setMessage] = useState("");
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { id } = useParams();
  const location = useLocation();
  const [chatNameGenerated, setChatNameGenerated] = useState(false);
  const [messages, setMessages] = useState([]);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [docsViewerOpen, setDocsViewerOpen] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [uploadButtonClicked, setUploadButtonClicked] = useState(false);
  const pollingTimeoutRef = useRef(null);

  // Load existing chat messages
  const handleLoadChat = useCallback(async () => {
    if (!id) return;
    if (!props.selectedChatId) {
      props.handleChatSelect(id);
    }
    try {
      const response = await fetcher("retrieve-messages-from-chat", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          chat_id: id,
          chat_type: 0,
        }),
      });

      const response_data = await response.json();
      if (!props.currChatName && !chatNameGenerated) {
        props.setCurrChatName(response.chat_name);
        setChatNameGenerated(true);
      }
      // If no messages, this could be a new chat or a chat still processing
      if (!response_data.messages?.length) {
        // Check for pending message from navigation state or localStorage
        const pendingMessage =
          location.state?.message ||
          localStorage.getItem(`pending-message-${id}`);

        if (pendingMessage) {
          const userMessage = {
            id: "user-content",
            chat_id: id,
            role: "user",
            content: pendingMessage,
          };
          const thinkingMessage = {
            id: `temp-thinking-${Date.now()}`,
            chat_id: id,
            role: "assistant",
            content: "Thinking...",
          };
          setMessages([userMessage, thinkingMessage]);

          // Store in localStorage for refresh persistence
          if (location.state?.message) {
            localStorage.setItem(
              `pending-message-${id}`,
              location.state.message
            );
          }

          // Set up polling to check for the response
          let pollAttempts = 0;
          const maxPollAttempts = 30; // 60 seconds maximum (30 * 2 seconds)

          // Clear any existing polling timeout
          if (pollingTimeoutRef.current) {
            clearTimeout(pollingTimeoutRef.current);
          }

          const pollForResponse = async () => {
            pollAttempts++;
            console.log(
              `Polling attempt ${pollAttempts}/${maxPollAttempts} for chat ${id}`
            );

            try {
              const pollResponse = await fetcher(
                "retrieve-messages-from-chat",
                {
                  method: "POST",
                  headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                  },
                  body: JSON.stringify({
                    chat_id: id,
                    chat_type: 0,
                  }),
                }
              );

              const pollData = await pollResponse.json();
              console.log("Poll response for chat %s:", id, pollData);

              if (pollData.messages?.length > 0) {
                // We got the response! Update messages
                console.log(
                  `Messages received for chat ${id}, stopping polling`
                );
                localStorage.removeItem(`pending-message-${id}`);
                const transformedMessages = pollData.messages.map((item) => ({
                  id: item.id,
                  chat_id: id,
                  content: item.message_text,
                  role: item.sent_from_user === 1 ? "user" : "assistant",
                  relevant_chunks: item.relevant_chunks,
                }));
                setMessages(transformedMessages);
                pollingTimeoutRef.current = null; // Clear the ref
                return; // Stop polling
              } else if (pollAttempts < maxPollAttempts) {
                // Still no response, poll again in 2 seconds if we haven't exceeded max attempts
                console.log(
                  `No messages yet for chat ${id}, continuing polling...`
                );
                pollingTimeoutRef.current = setTimeout(pollForResponse, 2000);
              } else {
                // Max attempts reached, show error message
                console.warn(
                  "Polling timeout: No response received after maximum attempts"
                );
                setMessages((prevMessages) => {
                  return prevMessages.map((msg) => {
                    if (msg.content === "Thinking...") {
                      return {
                        ...msg,
                        content:
                          "Sorry, the request is taking longer than expected. Please try again.",
                      };
                    }
                    return msg;
                  });
                });
                localStorage.removeItem(`pending-message-${id}`);
                pollingTimeoutRef.current = null; // Clear the ref
              }
            } catch (error) {
              console.error("Error polling for response:", error);
              // Show error message and stop polling
              setMessages((prevMessages) => {
                return prevMessages.map((msg) => {
                  if (msg.content === "Thinking...") {
                    return {
                      ...msg,
                      content:
                        "Sorry, I couldn't connect to the server. Please check your connection and try again.",
                    };
                  }
                  return msg;
                });
              });
              localStorage.removeItem(`pending-message-${id}`);
              pollingTimeoutRef.current = null; // Clear the ref
            }
          };

          // Start polling after a short delay
          pollingTimeoutRef.current = setTimeout(pollForResponse, 2000);
        } else {
          // No messages and no pending message - empty chat
          setMessages([]);
        }
        return;
      }

      // We have messages, so clear any pending message
      localStorage.removeItem(`pending-message-${id}`);

      const transformedMessages = response_data.messages.map((item) => ({
        id: item.id,
        chat_id: id,
        content: item.message_text,
        role: item.sent_from_user === 1 ? "user" : "assistant",
        relevant_chunks: item.relevant_chunks,
      }));
      console.log(transformedMessages);
      setMessages(transformedMessages);
    } catch (error) {
      console.error("Error loading chat:", error);
    }
  }, [id, location.state?.message]);
  const inferChatName = async (text, answer, chatId) => {
    const combined_text = text + " " + answer;
    console.log("infer chat with chatId:", chatId);
    try {
      const response = await fetcher("infer-chat-name", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: combined_text,
          chat_id: chatId,
        }),
      });
      const response_data = await response.json();
      console.log("response data 123", response_data.chat_name);
      props.setCurrChatName(response_data.chat_name);

      props.handleForceUpdate();
    } catch (error) {
      console.error("Error inferring chat name:", error);
    }
  };
  // Load uploaded documents for the current chat
  const handleLoadDocs = useCallback(async () => {
    if (!id) return;

    setLoadingDocs(true);
    try {
      const response = await fetcher("retrieve-current-docs", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          chat_id: id,
        }),
      });

      const response_data = await response.json();
      if (response_data.doc_info) {
        setUploadedDocs((prevDocs) => {
          const previousCount = prevDocs.length;
          // Auto-open documents viewer when first document is uploaded
          if (previousCount === 0 && response_data.doc_info.length > 0) {
            setDocsViewerOpen(true);
          }
          return response_data.doc_info;
        });
        console.log(response_data.doc_info);
      }
    } catch (error) {
      console.error("Error loading documents:", error);
      setUploadedDocs([]);
    }
    setLoadingDocs(false);
  }, [id]);

  // Load chat when component mounts or ID changes
  useEffect(() => {
    // Clear any existing polling when chat changes
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }

    if (id) {
      handleLoadChat();
      handleLoadDocs();
    } else {
      setMessages([]);
      setChatNameGenerated(false);
      setUploadedDocs([]);
    }

    // Cleanup function to clear polling on unmount or chat change
    return () => {
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
    };
  }, [id, handleLoadChat, handleLoadDocs]);

  // Main message sending function
  const handleSendMessage = async (event) => {
    event.preventDefault();

    // Only prevent submission if there's no message text
    if (!message || message.trim() === "") return;

    const currentPath = window.location.pathname;
    const currentMessage = message;

    // Clear input immediately
    setMessage("");

    // If we're on root path or base chat path, create new chat first
    let targetChatId = id;
    if (currentPath === "/" || currentPath === "/chat" || !id) {
      try {
        // Create new chat first
        targetChatId = await props.createNewChat();
        // Navigate to new chat URL
        navigate(`/chat/${targetChatId}`, {
          state: { message: currentMessage },
        });
      } catch (error) {
        console.error("Error creating new chat:", error);
        // Restore message on failure
        setMessage(currentMessage);
        return;
      }
    }

    // Add user message and thinking placeholder immediately
    const thinkingId = `temp-thinking-${Date.now()}`;
    const newMessages = [
      {
        id: `temp-user-${Date.now()}`,
        chat_id: targetChatId,
        role: "user",
        content: currentMessage,
      },
      {
        id: thinkingId,
        chat_id: targetChatId,
        role: "assistant",
        content: "Thinking...",
      },
    ];

    // Store the message in localStorage for refresh persistence
    localStorage.setItem(`pending-message-${targetChatId}`, currentMessage);

    if (currentPath === "/" || currentPath === "/chat" || !id) {
      // New chat - set messages directly
      setMessages(newMessages);
    } else {
      // Existing chat - append to existing messages
      setMessages((prev) => [...prev, ...newMessages]);
    }

    // Send to API
    await sendToAPI(currentMessage, targetChatId, thinkingId);
  };

  const sendToAPI = async (text, chatId, thinkingId) => {
    try {
      const res = await fetcher("process-message-pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          chat_id: Number(chatId),
          model_type: props.isPrivate,
          model_key: props.confirmedModelKey,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      await handleSSEStreamingResponse(res, thinkingId, text, chatId);
      localStorage.removeItem(`pending-message-${chatId}`);
    } catch (err) {
      console.error("Message send error:", err);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === thinkingId
            ? {
                ...msg,
                content:
                  "Sorry, I couldn't connect to the server. Please try again.",
                isThinking: false,
              }
            : msg
        )
      );
    }
  };

  const handleSSEStreamingResponse = async (
    response,
    thinkingId,
    originalText,
    chatId
  ) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.trim() === "") continue;

          if (line.startsWith("data: ")) {
            const dataContent = line.slice(6);

            if (dataContent === "[DONE]") {
              console.log("✅ Stream completed");
              // Mark streaming as complete and ensure final state
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === thinkingId 
                    ? { 
                        ...msg, 
                        isThinking: false, 
                        currentStep: null 
                      } 
                    : msg
                )
              );
              break;
            }

            try {
              const eventData = JSON.parse(dataContent);

              // Update the message directly in the messages array
              setMessages((prev) => {
                const updated = prev.map((msg) => {
                  if (msg.id === thinkingId) {
                    const updatedMsg = updateMessageWithStreamData(msg, eventData);
                    // Force re-render by ensuring object reference changes
                    return { ...updatedMsg };
                  }
                  return msg;
                });
                return [...updated]; // Force array reference change
              });

              // Generate chat name when we get the final answer
              if (
                (eventData.type === "complete" || eventData.type === "step-complete") &&
                eventData.answer &&
                !chatNameGenerated
              ) {
                await inferChatName(originalText, eventData.answer, chatId);
                setChatNameGenerated(true);
                props.handleForceUpdate?.();
              }

              // Force final state update for completion events
              if (eventData.type === "complete" || eventData.type === "step-complete") {
                setTimeout(() => {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === thinkingId
                        ? {
                            ...msg,
                            isThinking: false,
                            currentStep: null,
                            content: eventData.answer || msg.content,
                            sources: eventData.sources || msg.sources || [],
                          }
                        : msg
                    )
                  );
                }, 100); // Small delay to ensure all updates are processed
              }
            } catch (e) {
              console.error("Error parsing streaming data:", e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Streaming error:", error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === thinkingId
            ? {
                ...msg,
                content: "Sorry, there was an error processing your request.",
                isThinking: false,
              }
            : msg
        )
      );
    }
  };

  const updateMessageWithStreamData = (message, eventData) => {
    const updatedMessage = { ...message };

    console.log("Processing event:", eventData);

    switch (eventData.type) {
      case "tool_start":
      case "tools_start":
        // Add reasoning step for tool start
        const toolStartStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          tool_name: eventData.tool_name,
          message: `Using ${eventData.tool_name}...`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          toolStartStep,
        ];
        updatedMessage.currentStep = toolStartStep;
        break;

      case "tool_end":
        // Update the last tool step with output
        const reasoningWithOutput = [...(updatedMessage.reasoning || [])];
        const lastToolIndex = reasoningWithOutput.findLastIndex(
          (step) => step.type === "tool_start" || step.type === "tools_start"
        );
        if (lastToolIndex !== -1) {
          reasoningWithOutput[lastToolIndex] = {
            ...reasoningWithOutput[lastToolIndex],
            tool_output: eventData.output,
            message: "Tool execution completed",
          };
        }
        updatedMessage.reasoning = reasoningWithOutput;
        updatedMessage.currentStep = {
          type: "tool_end",
          message: "Tool execution completed",
        };
        break;

      case "agent_thinking":
        // Add thinking step
        const thinkingStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_thought: eventData.thought,
          planned_action: eventData.action,
          message: "Planning next step...",
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          thinkingStep,
        ];
        updatedMessage.currentStep = thinkingStep;
        break;

      case "complete":
        // Set final answer and sources
        updatedMessage.content = eventData.answer || "";
        updatedMessage.sources = eventData.sources || [];
        updatedMessage.isThinking = false;
        updatedMessage.currentStep = null;

        // Add completion step to reasoning
        const completeStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          thought: eventData.thought,
          message: "Response complete",
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          completeStep,
        ];
        break;
      case "step-complete":
        // Set final answer and sources
        updatedMessage.content = eventData.answer || "";
        updatedMessage.sources = eventData.sources || [];
        updatedMessage.isThinking = false;
        updatedMessage.currentStep = null;

        // Add completion step to reasoning
        const StepComplete = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          thought: eventData.thought,
          message: "Query processing completed",
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          StepComplete,
        ];
        break;

      // Multi-agent system event types
      case "agent_start":
        const agentStartStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_name: eventData.agent_name,
          message: eventData.message || `${eventData.agent_name} started`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          agentStartStep,
        ];
        updatedMessage.currentStep = agentStartStep;
        break;

      case "agent_progress":
        const progressStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          current_agent: eventData.current_agent,
          completed_agents: eventData.completed_agents,
          message: eventData.message || `${eventData.current_agent} completed`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          progressStep,
        ];
        break;

      case "agent_reasoning":
        const reasoningStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_name: eventData.agent_name,
          reasoning: eventData.reasoning,
          message: `${eventData.agent_name} reasoning`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          reasoningStep,
        ];
        break;

      case "agent_tool_use":
        const agentToolStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_name: eventData.agent_name,
          tool_name: eventData.tool_name,
          input: eventData.input,
          message: eventData.message || `${eventData.agent_name} using ${eventData.tool_name}`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          agentToolStep,
        ];
        break;

      case "agent_tool_complete":
        // Update the last agent tool step with output
        const agentReasoningWithOutput = [...(updatedMessage.reasoning || [])];
        const lastAgentToolIndex = agentReasoningWithOutput.findLastIndex(
          (step) => step.type === "agent_tool_use"
        );
        if (lastAgentToolIndex !== -1) {
          agentReasoningWithOutput[lastAgentToolIndex] = {
            ...agentReasoningWithOutput[lastAgentToolIndex],
            tool_output: eventData.output,
            message: eventData.message || "Agent tool execution completed",
          };
        }
        updatedMessage.reasoning = agentReasoningWithOutput;
        break;

      case "reasoning_step":
        // Add reasoning step from multi-agent system
        if (eventData.step) {
          updatedMessage.reasoning = [
            ...(updatedMessage.reasoning || []),
            eventData.step,
          ];
        }
        break;

      default:
        console.warn("Unhandled event type:", eventData.type);
    }

    return updatedMessage;
  };

  // Component for displaying thinking steps
  const ThinkingIndicator = ({ step }) => {
    const getStepIcon = (type) => {
      switch (type) {
        case "llm_reasoning":
          return <FontAwesomeIcon icon={faBrain} className="text-blue-400" />;
        case "tool_start":
        case "tools_start":
        case "tool_end":
          return <FontAwesomeIcon icon={faSearch} className="text-green-400" />;
        case "agent_thinking":
          return <FontAwesomeIcon icon={faCog} className="text-purple-400" />;
        case "complete":
        case "step-complete":
          return (
            <FontAwesomeIcon icon={faCheckCircle} className="text-green-500" />
          );
        // Multi-agent system icons
        case "agent_start":
          return <FontAwesomeIcon icon={faCog} className="text-yellow-400" />;
        case "agent_progress":
          return <FontAwesomeIcon icon={faArrowRight} className="text-orange-400" />;
        case "agent_reasoning":
          return <FontAwesomeIcon icon={faBrain} className="text-cyan-400" />;
        case "agent_tool_use":
        case "agent_tool_complete":
          return <FontAwesomeIcon icon={faSearch} className="text-emerald-400" />;
        case "agent_completion":
        case "agent_error":
          return <FontAwesomeIcon icon={faInfoCircle} className="text-indigo-400" />;
        case "orchestrator_decision":
        case "orchestrator_synthesis":
          return <FontAwesomeIcon icon={faSitemap} className="text-pink-400" />;
        case "reasoning_step":
          return <FontAwesomeIcon icon={faLightbulb} className="text-amber-400" />;
        default:
          return <FontAwesomeIcon icon={faCog} className="text-gray-400" />;
      }
    };
    console.log("stepsss", step)
    const getStepColor = (type) => {
      switch (type) {
        case "llm_reasoning":
          return "border-l-blue-400 bg-blue-950/20";
        case "tool_start":
        case "tools_start":
        case "tool_end":
          return "border-l-green-400 bg-green-950/20";
        case "agent_thinking":
          return "border-l-purple-400 bg-purple-950/20";
        case "complete":
        case "step-complete":
          return "border-l-green-500 bg-green-950/30";
        // Multi-agent system colors
        case "agent_start":
          return "border-l-yellow-400 bg-yellow-950/20";
        case "agent_progress":
          return "border-l-orange-400 bg-orange-950/20";
        case "agent_reasoning":
          return "border-l-cyan-400 bg-cyan-950/20";
        case "agent_tool_use":
        case "agent_tool_complete":
          return "border-l-emerald-400 bg-emerald-950/20";
        case "agent_completion":
          return "border-l-indigo-400 bg-indigo-950/20";
        case "agent_error":
          return "border-l-red-400 bg-red-950/20";
        case "orchestrator_decision":
        case "orchestrator_synthesis":
          return "border-l-pink-400 bg-pink-950/20";
        case "reasoning_step":
          return "border-l-amber-400 bg-amber-950/20";
        default:
          return "border-l-gray-400 bg-gray-800/20";
      }
    };
    console.log(`${step.message || "Processing"}: `, step);
    if (!step) return null;
    return (
      <div
        className={`border-l-2 ${getStepColor(
          step.type
        )} pl-3 py-2 mb-2 text-sm`}
      >
        <div className="flex items-center gap-2 mb-1">
          {getStepIcon(step.type)}
          <span className="text-gray-300 font-medium">
            {step.message || "Processing..."}
          </span>
        </div>

        {step.thought && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Thought:</strong> {step.thought}
          </div>
        )}

        {step.agent_thought && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Planning:</strong> {step.agent_thought}
          </div>
        )}

        {step.tool_name && (
          <div className="text-gray-500 text-xs">
            <strong>Tool:</strong> {step.tool_name}
          </div>
        )}

        {step.tool_output && (
          <div className="text-gray-500 text-xs mt-1">
            <strong>Result:</strong>{" "}
            {step.tool_output.length > 100
              ? step.tool_output.substring(0, 100) + "..."
              : step.tool_output}
          </div>
        )}

        {/* Multi-agent system specific fields */}
        {step.agent_name && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Agent:</strong> {step.agent_name}
          </div>
        )}

        {step.reasoning && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Reasoning:</strong> {step.reasoning.length > 150 ? step.reasoning.substring(0, 150) + "..." : step.reasoning}
          </div>
        )}

        {step.current_agent && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Current Agent:</strong> {step.current_agent}
          </div>
        )}

        {step.completed_agents && step.completed_agents.length > 0 && (
          <div className="text-gray-500 text-xs">
            <strong>Completed:</strong> {step.completed_agents.join(", ")}
          </div>
        )}

        {step.final_thought && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Final Thought:</strong> {step.final_thought}
          </div>
        )}

        {step.planned_action && (
          <div className="text-gray-500 text-xs">
            <strong>Planned Action:</strong> {step.planned_action}
          </div>
        )}

        {step.confidence && (
          <div className="text-gray-500 text-xs">
            <strong>Confidence:</strong> {Math.round(step.confidence * 100)}%
          </div>
        )}

        {step.error && (
          <div className="text-red-400 text-xs mt-1">
            <strong>Error:</strong> {step.error}
          </div>
        )}
      </div>
    );
  };

  // Function to toggle reasoning expansion
  const toggleReasoningExpansion = (messageId) => {
    setExpandedReasoning((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  // Auto-expand reasoning for new thinking messages
  useEffect(() => {
    messages.forEach((msg) => {
      if (msg.role === "assistant" && msg.isThinking && expandedReasoning[msg.id] === undefined) {
        setExpandedReasoning((prev) => ({
          ...prev,
          [msg.id]: true, // Auto-expand reasoning for thinking messages
        }));
      }
    });
  }, [messages, expandedReasoning]);

  const handleGenerateShareableUrl = async () => {
    if (!props.selectedChatId) {
      alert("No chat selected");
      return;
    }
    try {
      const response = await fetcher(
        `generate-playbook/${props.selectedChatId}`,
        {
          method: "GET",
          credentials: "include",
          headers: {
            Accept: "application/json",
          },
        }
      );
      const data = await response.json();
      const shareableUrl = data.url || `/playbook/${data.share_uuid}`;
      alert(`Your shareable URL: ${shareableUrl}`);
    } catch (error) {
      console.error("Error generating shareable URL:", error);
      alert("Failed to generate shareable URL.");
    }
  };

  // Send message to API and handle response
  const sendToAPI = async (messageText, chatId, thinkingId = null) => {
    try {
      const response = await fetcher("process-message-pdf", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: messageText,
          chat_id: Number(chatId),
          model_type: props.isPrivate,
          model_key: props.confirmedModelKey,
        }),
      });

      const response_data = await response.json();
      const answer = response_data.answer;

      // Replace the specific "Thinking..." message with actual response
      setMessages((messages) => {
        // Find the specific thinking message by its ID
        const thinkingIndex = messages.findIndex(
          (msg) => msg.id === thinkingId
        );

        if (thinkingIndex !== -1) {
          // Replace the found "Thinking..." message
          const updatedMessages = [...messages];
          updatedMessages[thinkingIndex] = {
            ...updatedMessages[thinkingIndex],
            id: response_data.id,
            content: answer,
          };
          return updatedMessages;
        }

        // Fallback: find first "Thinking..." message for this chat if thinkingId doesn't match
        const fallbackIndex = messages.findIndex(
          (msg) =>
            msg.content === "Thinking..." && msg.chat_id === Number(chatId)
        );

        if (fallbackIndex !== -1) {
          const updatedMessages = [...messages];
          updatedMessages[fallbackIndex] = {
            ...updatedMessages[fallbackIndex],
            id: response_data.id,
            content: answer,
          };
          return updatedMessages;
        }

        // If no "Thinking..." message found, just add the new response
        return [
          ...messages,
          {
            id: response_data.id,
            chat_id: Number(chatId),
            role: "assistant",
            content: answer,
          },
        ];
      });

      // Update chat name for first message (only if chat name hasn't been generated yet)
      if (!chatNameGenerated) {
        console.log("Generating chat name for chat:", chatId);
        await inferChatName(messageText, answer, chatId);
        setChatNameGenerated(true);
        props.handleForceUpdate?.();
      }

      // Clear any pending message from localStorage since we got a response
      localStorage.removeItem(`pending-message-${chatId}`);

      // Refresh documents list to pick up any newly uploaded files from sidebar
      setTimeout(() => {
        handleLoadDocs();
      }, 1000);
    } catch (error) {
      console.error("Error sending message:", error);

      // Replace the specific "Thinking..." message with error message
      setMessages((messages) => {
        // Find the specific thinking message by its ID
        const thinkingIndex = messages.findIndex(
          (msg) => msg.id === thinkingId
        );

        if (thinkingIndex !== -1) {
          // Replace the found "Thinking..." message
          const updatedMessages = [...messages];
          updatedMessages[thinkingIndex] = {
            ...updatedMessages[thinkingIndex],
            content:
              "Sorry, I couldn't connect to the server. Please check your connection and try again.",
          };
          return updatedMessages;
        }

        // Fallback: find first "Thinking..." message for this chat if thinkingId doesn't match
        const fallbackIndex = messages.findIndex(
          (msg) =>
            msg.content === "Thinking..." && msg.chat_id === Number(chatId)
        );

        if (fallbackIndex !== -1) {
          const updatedMessages = [...messages];
          updatedMessages[fallbackIndex] = {
            ...updatedMessages[fallbackIndex],
            content:
              "Sorry, I couldn't connect to the server. Please check your connection and try again.",
          };
          return updatedMessages;
        }

        // If no "Thinking..." message found, add a new error message
        return [
          ...messages,
          {
            id: `error-${Date.now()}`,
            chat_id: Number(chatId),
            role: "assistant",
            content:
              "Sorry, I couldn't connect to the server. Please check your connection and try again.",
          },
        ];
      });

      // Don't clear localStorage on error - keep the pending message for potential retry
    }
  };

  // Handle Enter key press
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  // Handle deleting an uploaded document
  const handleDeleteDoc = async (docId) => {
    console.log("here");
    try {
      await fetcher("delete-doc", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          doc_id: docId,
        }),
      });

      setUploadedDocs((prev) => prev.filter((doc) => doc.doc_id !== docId));

      // Automatically refresh the documents list after successful deletion
      handleLoadDocs();
    } catch (error) {
      console.error("Error deleting document:", error);
      // Still try to refresh in case the deletion actually worked
      handleLoadDocs();
    }
  };

  return (
    <div
      className={`h-full bg-anoteblack-800 w-full flex flex-col ${
        props.menu ? "md:blur-none blur" : ""
      }`}
    >
      <div
        ref={(ref) =>
          ref && ref.scrollTo({ top: ref.scrollHeight, behavior: "smooth" })
        }
        className={`h-full rounded overflow-auto ${
          messages.length > 0 ? "block" : "hidden"
        } flex justify-center`}
      >
        <div className="py-3 flex-col mt-0 px-4 flex gap-3 w-full">
          <div className="bg-anoteblack-800 flex items-center sticky top-0 lg:top-0 z-10 w-full border-b border-gray-400/30 px-2">
            {/* Left: Reload button */}
            <div className="flex items-center flex-shrink-0 z-10">
              <button
                onClick={handleRefreshChatName}
                className="p-2 hover:bg-gray-700 rounded transition-colors"
                title="Refresh chat name"
              >
                <FontAwesomeIcon
                  icon={faSyncAlt}
                  className="text-lg text-[#DFDFDF]"
                />
              </button>
            </div>
            {/* Center: Chat name */}
            <div className="absolute left-0 right-0 flex justify-center items-center pointer-events-none h-14">
              <h1 className="text-white truncate text-center w-2/3 pointer-events-auto">
                {props.currChatName}
              </h1>
            </div>
            {/* Right: Share/Download */}
            <div className="flex gap-2 flex-shrink-0 ml-auto z-10">
              <button
                onClick={handleGenerateShareableUrl}
                className="p-2 hover:bg-gray-700 rounded transition-colors"
                title="Share chat"
              >
                <FontAwesomeIcon
                  icon={faShareAlt}
                  className="text-lg text-[#DFDFDF]"
                />
              </button>
              <button
                className="p-2 hover:bg-gray-700 rounded transition-colors"
                title="Download chat"
              >
                <FontAwesomeIcon
                  icon={faDownload}
                  className="text-lg text-[#DFDFDF]"
                />
              </button>
            </div>
          </div>
          {messages.map((msg, index) => (
            <div
              key={`${msg.chat_id}-${msg.id || index}`}
              className={`flex items-center gap-4 ${
                msg.role === "user" ? "justify-end" : ""
              }`}
            >
              <div
                className={`rounded-lg p-3 max-w-[80%] ${
                  msg.role === "user"
                    ? "from-[#40C6FF] to-[#5299D3] rounded-br-none bg-gradient-to-b text-white ml-auto"
                    : "bg-transparent border rounded-bl-none text-white"
                }`}
              >
                {/* FIXED: Responsive width for assistant messages */}
                <div
                  className={`space-y-3 ${
                    msg.role === "assistant"
                      ? "w-full md:w-5/6 lg:w-3/4 xl:w-2/3"
                      : ""
                  }`}
                >
                  {/* Reasoning Box - Shows during streaming and after completion */}
                  {msg.role === "assistant" && (msg.reasoning?.length > 0 || msg.isThinking) && (
                    <div className="bg-[#0f1419] border border-[#2e3a4c] rounded-xl p-4 mb-3">
                      <button
                        onClick={() => toggleReasoningExpansion(msg.id)}
                        className="flex items-center justify-between w-full text-left text-xs text-gray-400 hover:text-gray-200 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <FontAwesomeIcon icon={faBrain} />
                          <span>
                            {msg.isThinking 
                              ? "AI Reasoning (Live)" 
                              : `AI Reasoning Steps (${msg.reasoning?.length || 0})`
                            }
                          </span>
                        </div>
                        <FontAwesomeIcon
                          icon={
                            expandedReasoning[msg.id]
                              ? faChevronUp
                              : faChevronDown
                          }
                          className="text-xs"
                        />
                      </button>

                      {expandedReasoning[msg.id] && (
                        <div className="mt-3 space-y-2 animate-fade-in">
                          {/* Show current step during thinking */}
                          {msg.isThinking && msg.currentStep && (
                            <div className="border-l-2 border-yellow-400 bg-yellow-950/20 pl-3 py-2 mb-2">
                              <ThinkingIndicator step={msg.currentStep} />
                            </div>
                          )}
                          
                          {/* Show completed reasoning steps */}
                          {msg.reasoning?.map((step, idx) => (
                            <ThinkingIndicator
                              key={step.id || idx}
                              step={step}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Main message content */}
                  <div
                    className={`rounded-2xl p-4 shadow-lg transition-all ${
                      msg.role === "user"
                        ? "bg-gradient-to-br from-[#28b2fb] to-[#111827] text-white ml-auto rounded-br-none"
                        : "bg-[#1f2937] text-white border border-[#2e3a4c] rounded-bl-none"
                    }`}
                  >
                    {/* Assistant Thinking Animation */}
                    {msg.isThinking ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-[#defe47] rounded-full animate-pulse"></div>
                            <div
                              className="w-2 h-2 bg-[#defe47] rounded-full animate-pulse"
                              style={{ animationDelay: "0.2s" }}
                            ></div>
                            <div
                              className="w-2 h-2 bg-[#defe47] rounded-full animate-pulse"
                              style={{ animationDelay: "0.4s" }}
                            ></div>
                          </div>
                          <span className="text-sm text-gray-400">
                            AI is thinking...
                          </span>
                        </div>

                        {/* Show partial content if available during streaming */}
                        {msg.content && (
                          <div className="mt-3">
                            <p className="whitespace-pre-wrap leading-relaxed text-sm">
                              {msg.content}
                            </p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div>
                        {/* Main response content */}
                        <p className="whitespace-pre-wrap leading-relaxed text-sm">
                          {msg.content}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div
        className={`flex-shrink-0 borderrounded-xl ${
          messages.length === 0
            ? "flex-1 flex items-center  gap-2 flex-col justify-center"
            : ""
        }`}
      >
        {/* Welcome message */}
        {messages.length === 0 && (
          <div className="w-full text-anoteblack-100 animate-typing overflow-hidden whitespace-nowrap flex items-center justify-center font-bold text-2xl mb-4">
            What can I help you with?
          </div>
        )}

        {/* Input form */}
        <div className="flex w-full justify-center my-5 px-4">
          <div className="flex items-center gap-3 w-full max-w-4xl">
            {/* Left side - Upload button */}
            <button
              type="button"
              onClick={() => {
                console.log("Upload button clicked in Chatbot");
                console.log(
                  "props.onUploadClick exists:",
                  !!props.onUploadClick
                );
                console.log("Chat ID (id):", id);
                if (props.onUploadClick) {
                  console.log("Calling props.onUploadClick");
                  setUploadButtonClicked(true);
                  props.onUploadClick();
                  // Reset the visual state after a short delay
                  setTimeout(() => setUploadButtonClicked(false), 1000);
                } else {
                  console.log("props.onUploadClick is not available");
                }
              }}
              disabled={props.isUploading || !id}
              className={`flex items-center justify-center w-12 h-12 rounded-xl transition-colors flex-shrink-0 ${
                uploadButtonClicked
                  ? "bg-blue-600 text-white"
                  : props.isUploading
                  ? "bg-gray-500 text-gray-300 cursor-not-allowed"
                  : !id
                  ? "bg-gray-600 text-gray-400 cursor-not-allowed"
                  : "bg-blue-500 hover:bg-blue-600 text-white"
              }`}
              title={!id ? "Please select or create a chat first" : "Add files"}
            >
              <FontAwesomeIcon icon={faFile} className="text-lg" />
            </button>

            {/* Center - Input form */}
            <form
              id="chat-form"
              className="flex-1"
              onSubmit={handleSendMessage}
            >
              <div className="relative">
                {/* Textarea with rounded design */}
                <div className="relative  flex items-center bg-gray-700 rounded-3xl border border-gray-600 focus-within:border-gray-500 transition-colors">
                  <textarea
                    className="w-full border-none resize-none text-lg px-6 py-2 focus:ring-0 focus:outline-none text-white placeholder:text-gray-400 bg-anoteblack-800 rounded-3xl"
                    rows={1}
                    placeholder="Ask your document a question"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    ref={inputRef}
                  />
                </div>

                {/* File upload progress */}
                {props.isUploading && props.uploadProgress !== undefined && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 bg-gray-700 rounded-full h-1">
                      <div
                        className="bg-blue-600 h-1 rounded-full transition-all duration-300"
                        style={{ width: `${props.uploadProgress}%` }}
                      ></div>
                    </div>
                    <span className="text-xs text-gray-400">
                      {props.uploadProgress}%
                    </span>
                  </div>
                )}
              </div>
            </form>

            {/* Right side - Send button */}
            <button
              type="submit"
              onClick={handleSendMessage}
              disabled={!message || message.trim() === ""}
              className={`flex items-center justify-center w-12 h-12 rounded-xl transition-colors flex-shrink-0 ${
                !message || message.trim() === ""
                  ? "bg-gray-600 text-gray-400 cursor-not-allowed"
                  : "bg-blue-500 hover:bg-blue-600 text-white"
              }`}
            >
              <FontAwesomeIcon icon={faPaperPlane} className="text-lg" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;
