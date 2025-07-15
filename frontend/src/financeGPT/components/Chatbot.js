import React, { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPaperPlane, faDownload, faFile } from "@fortawesome/free-solid-svg-icons";
import "../styles/Chatbot.css";
import fetcher from "../../http/RequestConfig";
import { useLocation, useNavigate, useParams } from "react-router-dom";

const Chatbot = (props) => {
  const [message, setMessage] = useState("");
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { id } = useParams();
  const location = useLocation();
  const [isFirstMessageSent, setIsFirstMessageSent] = useState(false);
  const [messages, setMessages] = useState([]);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [docsViewerOpen, setDocsViewerOpen] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [uploadButtonClicked, setUploadButtonClicked] = useState(false);

  // Reset model key state and confirmation popup
  const [showConfirmResetKey, setShowConfirmResetKey] = useState(false);

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
          setIsFirstMessageSent(false);

          // Store in localStorage for refresh persistence
          if (location.state?.message) {
            localStorage.setItem(
              `pending-message-${id}`,
              location.state.message
            );
          }
        } else {
          // No messages and no pending message - empty chat
          setMessages([]);
          setIsFirstMessageSent(false);
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
      setIsFirstMessageSent(transformedMessages.length > 0);
    } catch (error) {
      console.error("Error loading chat:", error);
    }
  }, [id, location.state?.message]);

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
        const previousCount = uploadedDocs.length;
        console.log(response_data.doc_info);
        setUploadedDocs(response_data.doc_info);

        // Auto-open documents viewer when first document is uploaded
        if (previousCount === 0 && response_data.doc_info.length > 0) {
          setDocsViewerOpen(true);
        }
      }
    } catch (error) {
      console.error("Error loading documents:", error);
      setUploadedDocs([]);
    }
    setLoadingDocs(false);
  }, [id, uploadedDocs.length]);

  // Load chat when component mounts or ID changes
  useEffect(() => {
    if (id) {
      handleLoadChat();
      handleLoadDocs();
    } else {
      setMessages([]);
      setIsFirstMessageSent(false);
      setUploadedDocs([]);
    }
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
    await sendToAPI(currentMessage, targetChatId, false, thinkingId);
  };

  // Send message to API and handle response
  const sendToAPI = async (
    messageText,
    chatId,
    hadFiles = false,
    thinkingId = null
  ) => {
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

      // Update chat name for first message
      if (!isFirstMessageSent) {
        props.setCurrChatName?.(messageText);
        setIsFirstMessageSent(true);
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
      className={` py-2 h-full bg-anoteblack-800 lg:w-4/5 flex flex-col  ${
        props.menu ? "md:blur-none blur" : ""
      }`}
    >
      {/* Chat title for mobile */}
      <div className="w-full bg-transparent md:py-0 py-4 md:shadow-none shadow-lg md:mb-0 mb-2 items-center flex justify-center  flex-shrink-0">
        <span className="md:hidden rounded py-2 px-4">
          {props.currChatName}
        </span>
      </div>
      {/* Messages container */}
      <div
        ref={(ref) =>
          ref && ref.scrollTo({ top: ref.scrollHeight, behavior: "smooth" })
        }
        className={`h-full rounded md:mt-8 overflow-auto ${
          messages.length > 0 ? "block" : "hidden"
        } flex justify-center`}
      >
        <div className="py-3 flex-col mt-4 px-4 flex gap-3 w-full max-w-4xl mx-6">
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
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {/* Show agent info for assistant messages */}
                {msg.role === "assistant" && msg.agent && (
                  <div className="mt-1 text-xs text-gray-500">
                    🤖 {msg.agent.name}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      {/* Welcome message and input */}
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
        <div className="flex w-full justify-center px-4">
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
              className="flex-1 mt-3"
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
