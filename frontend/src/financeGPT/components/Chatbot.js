import React, { useState, useEffect, useRef, useCallback } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPaperPlane,
  faFile,
  faDownload,
  faShareAlt,
  faSyncAlt,
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
              msg.content === "Thinking..."
                ? {
                    ...msg,
                    content:
                      "Sorry, the request is taking too long. Please try again.",
                  }
                : msg
            )
          );
          // localStorage.removeItem(`pending-message-${chatId}`);
        }
      } catch (err) {
        console.error("Polling error:", err);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.content === "Thinking..."
              ? {
                  ...msg,
                  content:
                    "Sorry, I couldn't connect to the server. Please check your connection.",
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

      // if (!props.currChatName && !chatNameGenerated) {
      console.log("res", data);
      props.setCurrChatName(data.chat_name);
      setChatNameGenerated(true);
      // }

      if (!data.messages?.length) {
        const pending =
          location.state?.message ||
          localStorage.getItem(`pending-message-${id}`);
        if (pending) {
          console.log(
            "[handleLoadChat] Loading pending message after new chat creation:",
            pending
          ); // Added log
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
            content: "Thinking...",
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

        // 🧠 Only trigger polling after new chat creation
        localStorage.setItem(`pending-message-${targetChatId}`, currentMessage);

        const userMsg = {
          id: `user-${Date.now()}`,
          chat_id: targetChatId,
          role: "user",
          content: currentMessage,
        };
        const thinkingMsg = {
          id: `thinking-${Date.now()}`,
          chat_id: targetChatId,
          role: "assistant",
          content: "Thinking...",
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
        content: "Thinking...",
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

      const data = await res.json();
      const answer = data.answer;

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === thinkingId ? { ...msg, id: data.id, content: answer } : msg
        )
      );

      if (!chatNameGenerated) {
        await inferChatName(text, answer, chatId);
        setChatNameGenerated(true);
        props.handleForceUpdate?.();
      }

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
              }
            : msg
        )
      );
    }
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

  // const handleLoadDocs = useCallback(async () => {
  //   if (!id) return;
  //   setLoadingDocs(true);
  //   try {
  //     const res = await fetcher("retrieve-current-docs", {
  //       method: "POST",
  //       headers: { Accept: "application/json", "Content-Type": "application/json" },
  //       body: JSON.stringify({ chat_id: id }),
  //     });
  //     const data = await res.json();
  //     if (data.doc_info) {
  //       setUploadedDocs(data.doc_info);
  //       if (data.doc_info.length > 0 && uploadedDocs.length === 0) {
  //         setDocsViewerOpen(true);
  //       }
  //     }
  //   } catch (err) {
  //     console.error("Failed to load docs:", err);
  //   } finally {
  //     setLoadingDocs(false);
  //   }
  // }, [id, uploadedDocs.length]);

  useEffect(() => {
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }

    pollingStartedRef.current = false; // Reset for new chat navigation

    if (id) {
      handleLoadChat();
      // handleLoadDocs();
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

  // Function to handle Enter to send in textarea
  const handleInputKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (message.trim() !== "") {
        handleSendMessage(e);
      }
    }
  };

  // Add the refresh handler
  const handleRefreshChatName = async () => {
    if (typeof handleLoadChat === "function") {
      await handleLoadChat();
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
        <span className="md:hidden rounded py-2 truncate px-4">
          {props.currChatName}
        </span>
      </div>
      <div
        ref={(ref) =>
          ref && ref.scrollTo({ top: ref.scrollHeight, behavior: "smooth" })
        }
        className={`h-full rounded md:mt-8 overflow-auto ${
          messages.length > 0 ? "block" : "hidden"
        } flex justify-center`}
      >
        <div className="py-3 flex-col mt-0 md:mt-4 px-4 flex gap-3 w-full max-w-4xl mx-6">
          <div className="bg-anoteblack-800 flex items-center sticky top-4 z-10 w-full border-b border-gray-400/30 px-2">
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
            {/* Center: Chat name (absolutely centered, not pushing buttons) */}
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
                    ref={inputRef}
                    onKeyDown={handleInputKeyDown}
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
              // Removed onClick={handleSendMessage} to prevent double trigger
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
