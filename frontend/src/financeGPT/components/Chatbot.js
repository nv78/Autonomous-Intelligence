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
} from "@fortawesome/free-solid-svg-icons";
import "../styles/Chatbot.css";
import fetcher from "../../http/RequestConfig";
import { useLocation, useNavigate, useParams } from "react-router-dom";

const Chatbot = (props) => {
  const [message, setMessage] = useState("");
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const pollingStartedRef = useRef(false);
  const { id } = useParams();
  const location = useLocation();
  const [chatNameGenerated, setChatNameGenerated] = useState(false);
  const [messages, setMessages] = useState([]);
  const [uploadButtonClicked, setUploadButtonClicked] = useState(false);
  const pollingTimeoutRef = useRef(null);

  // State for tracking expanded reasoning sections
  const [expandedReasoning, setExpandedReasoning] = useState({});

  const inferChatName = async (text, answer, chatId) => {
    const combinedText = `${text} ${answer}`;
    try {
      const response = await fetcher("infer-chat-name", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ messages: combinedText, chat_id: chatId }),
      });
      const data = await response.json();
      props.setCurrChatName(data.chat_name);
      props.handleForceUpdate();
    } catch (err) {
      console.error("Chat name inference failed", err);
    }
  };

  const pollForMessages = useCallback((chatId, maxAttempts = 3) => {
    let attempts = 0;

    const poll = async () => {
      attempts++;
      try {
        const res = await fetcher("retrieve-messages-from-chat", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ chat_id: chatId, chat_type: 0 }),
        });

        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          const formatted = data.messages.map((m) => ({
            id: m.id,
            chat_id: chatId,
            content: m.message_text,
            role: m.sent_from_user === 1 ? "user" : "assistant",
            relevant_chunks: m.relevant_chunks,
            reasoning: m.reasoning || [], // Include reasoning data from database
            sources: m.sources || [], // Include sources if available
          }));
          setMessages(formatted);
          localStorage.removeItem(`pending-message-${chatId}`);
          pollingTimeoutRef.current = null;
          return;
        }

        if (attempts < maxAttempts) {
          pollingTimeoutRef.current = setTimeout(poll, 2000);
        } else {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.isThinking
                ? {
                    ...msg,
                    content:
                      "Sorry, the request is taking too long. Please try again.",
                    isThinking: false,
                  }
                : msg
            )
          );
        }
      } catch (err) {
        console.error("Polling error:", err);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.isThinking
              ? {
                  ...msg,
                  content:
                    "Sorry, I couldn't connect to the server. Please check your connection.",
                  isThinking: false,
                }
              : msg
          )
        );
        localStorage.removeItem(`pending-message-${chatId}`);
      }
    };

    pollingTimeoutRef.current = setTimeout(poll, 2000);
  }, []);

  const handleLoadChat = useCallback(async () => {
    if (!id) return;

    if (!props.selectedChatId) {
      props.handleChatSelect(id);
    }

    try {
      const res = await fetcher("retrieve-messages-from-chat", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_id: id, chat_type: 0 }),
      });

      const data = await res.json();

      console.log("res", data);
      props.setCurrChatName(data.chat_name);
      setChatNameGenerated(true);

      if (!data.messages?.length) {
        const pending =
          location.state?.message ||
          localStorage.getItem(`pending-message-${id}`);
        if (pending) {
          console.log(
            "[handleLoadChat] Loading pending message after new chat creation:",
            pending
          );
          const userMsg = {
            id: "user-content",
            chat_id: id,
            role: "user",
            content: pending,
          };
          const thinkingMsg = {
            id: `thinking-${Date.now()}`,
            chat_id: id,
            role: "assistant",
            content: "",
            isThinking: true,
            reasoning: [],
            sources: [],
          };
          setMessages([userMsg, thinkingMsg]);
          if (location.state?.message) {
            localStorage.setItem(
              `pending-message-${id}`,
              location.state.message
            );
          }
          await sendToAPI(pending, id, thinkingMsg.id);
          return;
        } else {
          setMessages([]);
        }
        return;
      }

      localStorage.removeItem(`pending-message-${id}`);
      const formatted = data.messages.map((m) => ({
        id: m.id,
        chat_id: id,
        content: m.message_text,
        role: m.sent_from_user === 1 ? "user" : "assistant",
        relevant_chunks: m.relevant_chunks,
        reasoning: m.reasoning || [], // Include reasoning data from database
        sources: m.sources || [], // Include sources if available
      }));
      setMessages(formatted);
    } catch (err) {
      console.error("Failed to load chat:", err);
    }
  }, [id, location.state?.message, pollForMessages]);

  const handleSendMessage = async (event) => {
    event.preventDefault();
    if (!message.trim()) return;

    const currentMessage = message.trim();
    setMessage("");

    let targetChatId = id;

    const isNewChat =
      !id ||
      window.location.pathname === "/" ||
      window.location.pathname === "/chat";

    if (isNewChat) {
      try {
        targetChatId = await props.createNewChat();
        navigate(`/chat/${targetChatId}`, {
          state: { message: currentMessage },
        });

        localStorage.setItem(`pending-message-${targetChatId}`, currentMessage);

        const userMsg = {
          id: `user-${Date.now()}`,
          chat_id: targetChatId,
          role: "user",
          relevant_chunks: [],
          content: currentMessage,
        };
        const thinkingMsg = {
          id: `thinking-${Date.now()}`,
          chat_id: targetChatId,
          role: "assistant",
          content: "",
          isThinking: true,
          reasoning: [],
          sources: [],
        };

        setMessages([userMsg, thinkingMsg]);

        if (!pollingStartedRef.current) {
          pollForMessages(targetChatId);
          pollingStartedRef.current = true;
        }

        return;
      } catch (err) {
        console.error("Failed to create chat:", err);
        setMessage(currentMessage);
        return;
      }
    }

    // For existing chat
    const thinkingId = `thinking-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        chat_id: targetChatId,
        role: "user",
        content: currentMessage,
      },
      {
        id: thinkingId,
        chat_id: targetChatId,
        role: "assistant",
        content: "",
        isThinking: true,
        reasoning: [],
        sources: [],
      },
    ]);

    localStorage.setItem(`pending-message-${targetChatId}`, currentMessage);
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
              // Mark streaming as complete
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === thinkingId ? { ...msg, isThinking: false } : msg
                )
              );
              break;
            }

            try {
              const eventData = JSON.parse(dataContent);

              // Update the message directly in the messages array
              setMessages((prev) =>
                prev.map((msg) => {
                  if (msg.id === thinkingId) {
                    return updateMessageWithStreamData(msg, eventData);
                  }
                  return msg;
                })
              );

              // Generate chat name when we get the final answer
              if (
                eventData.type === "complete" &&
                eventData.answer &&
                !chatNameGenerated
              ) {
                await inferChatName(originalText, eventData.answer, chatId);
                setChatNameGenerated(true);
                props.handleForceUpdate?.();
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
        updatedMessage.currentStep = null;
        break;
      case "step-complete":
        // Set final answer and sources
        updatedMessage.content = eventData.answer || "";
        updatedMessage.sources = eventData.sources || [];
        updatedMessage.isThinking = false;

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
        updatedMessage.currentStep = null;
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
          return "border-l-green-500 bg-green-950/30";
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

  useEffect(() => {
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }

    pollingStartedRef.current = false;

    if (id) {
      handleLoadChat();
    } else {
      setMessages([]);
      setChatNameGenerated(false);
    }

    return () => {
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
    };
  }, [id, handleLoadChat]);

  const handleInputKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (message.trim() !== "") {
        handleSendMessage(e);
      }
    }
  };

  const handleRefreshChatName = async () => {
    if (typeof handleLoadChat === "function") {
      await handleLoadChat();
    }
  };

  console.log(messages);

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
          <div className="px-4 md:px-8 lg:px-16 xl:px-32">
            {messages.map((msg, index) => (
              <div
                key={`${msg.chat_id}-${msg.id || index}`}
                className={`flex items-start gap-4 mb-4 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
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
                  {msg.role === "assistant" && msg.reasoning?.length > 0 && (
                    <div className="bg-[#0f1419] border border-[#2e3a4c] rounded-xl p-4">
                      <button
                        onClick={() => toggleReasoningExpansion(msg.id)}
                        className="flex items-center justify-between w-full text-left text-xs text-gray-400 hover:text-gray-200 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <FontAwesomeIcon icon={faBrain} />
                          <span>
                            AI Reasoning Steps ({msg.reasoning.length})
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
                          {msg.reasoning.map((step, idx) => (
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

                        {/* Current step indicator */}
                        {msg.currentStep && (
                          <ThinkingIndicator step={msg.currentStep} />
                        )}

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

                        {/* Sources Section */}
                        {msg.sources?.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-[#2e3a4c]">
                            <div className="flex items-center gap-2 mb-2 text-gray-400 text-xs font-semibold">
                              <FontAwesomeIcon icon={faFile} />
                              <span>Sources</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {msg.sources.map((source, idx) => (
                                <span
                                  key={idx}
                                  className="text-xs bg-[#2e3a4c] text-gray-300 px-2 py-1 rounded"
                                >
                                  {typeof source === "string"
                                    ? source
                                    : source.name || "Document"}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Assistant Agent Info */}
                        {msg.role === "assistant" && msg.agent && (
                          <div className="mt-2 text-[11px] text-gray-500 italic">
                            🤖 {msg.agent.name}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div
        className={`flex-shrink-0 borderrounded-xl ${
          messages.length === 0
            ? "flex-1 flex items-center gap-2 flex-col justify-center"
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
        <div className="flex w-full justify-center my-5  px-4">
          <div className="flex items-center gap-3 w-full max-w-4xl">
            {/* Left side - Upload button */}
            <button
              type="button"
              onClick={() => {
                console.log("Upload button clicked in Chatbot", "selectedChatId:", props.selectedChatId);
                if (props.onUploadClick) {
                  setUploadButtonClicked(true);
                  props.onUploadClick(props.selectedChatId);
                  setTimeout(() => setUploadButtonClicked(false), 1000);
                }
              }}
              disabled={props.isUploading}
              className={`flex items-center justify-center w-12 h-12 rounded-xl transition-colors flex-shrink-0 ${
                uploadButtonClicked
                  ? "bg-blue-600 text-white"
                  : props.isUploading
                  ? "bg-gray-500 text-gray-300 cursor-not-allowed"
                  : "bg-blue-500 hover:bg-blue-600 text-white"
              }`}
              title={!id ? "Please select or create a chat first" : "Add files"}
            >
              <FontAwesomeIcon icon={faFile} className="text-lg" />
            </button>

            {/* Center - Input */}
            <div className="flex-1">
              <div className="relative">
                <div className="relative flex items-center bg-gray-700 rounded-3xl border border-gray-600 focus-within:border-gray-500 transition-colors">
                  <textarea
                    className="w-full border-none resize-none text-lg px-6 py-2 focus:ring-0 focus:outline-none text-white placeholder:text-gray-400 bg-anoteblack-800 rounded-3xl"
                    rows={1}
                    placeholder="Ask your document a question"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    ref={inputRef}
                    onKeyDown={handleInputKeyDown}
                    disabled={messages.some((msg) => msg.isThinking)}
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
            </div>

            {/* Right side - Send button */}
            <button
              type="button"
              onClick={handleSendMessage}
              disabled={
                !message ||
                message.trim() === "" ||
                messages.some((msg) => msg.isThinking)
              }
              className={`flex items-center justify-center w-12 h-12 rounded-xl transition-colors flex-shrink-0 ${
                !message ||
                message.trim() === "" ||
                messages.some((msg) => msg.isThinking)
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
