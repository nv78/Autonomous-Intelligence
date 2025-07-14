import React, { useState, useRef, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPaperPlane, faUndoAlt } from "@fortawesome/free-solid-svg-icons";

const GTMChatbot = () => {
  const [messages, setMessages] = useState([
    {
      message: "Hello, I’m your chatbot. How can I help you today?",
      direction: "incoming",
    },
  ]);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const sendMessage = async (text) => {
    console.log("🟡 Attempting to send:", text);
    if (!text.trim()) return;
    inputRef.current.value = "";

    const tempId = Date.now();
    setMessages((prev) => [
      ...prev,
      { message: text, direction: "outgoing" },
      { message: "Loading...", direction: "incoming", id: tempId },
    ]);

    try {
      console.log("Sending message:", text);

      const res = await fetch("/gtm/respond", {
        method: "POST",
        credentials: "include", //necessary to avoid CORS issues 
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      });

      
      const data = await res.json();

      console.log("Received response:", res);

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempId
            ? { message: data.response, direction: "incoming" }
            : msg
        )
      );
    } catch (e) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempId
            ? { message: "Error connecting to server.", direction: "incoming" }
            : msg
        )
      );
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      sendMessage(inputRef.current.value);
    }
  };

  return (
    <div className="bg-[#1a1a1a] text-white h-[70vh] rounded-2xl p-4 flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center mb-2">
        <FontAwesomeIcon icon={faUndoAlt} className="cursor-pointer text-white" />
        <h2 className="text-lg font-semibold">Chat</h2>
        <div></div>
      </div>
      <hr className="border-gray-600 mb-2" />

      {/* Chat messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-2 pr-2"
      >
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.direction === "incoming" ? "justify-start" : "justify-end"}`}
          >
            <div
              className="rounded-2xl px-4 py-2 max-w-[75%] bg-[#2e2e2e] text-white"
            >
              {msg.message}
            </div>
          </div>
        ))}
      </div>

      {/* Input field */}
      <div className="flex items-center mt-4">
        <input
          ref={inputRef}
          type="text"
          placeholder="Type your message..."
          onKeyDown={handleKeyPress}
          className="flex-grow px-4 py-2 rounded-xl bg-[#141414] text-white border border-[#9b9b9b] focus:outline-none focus:ring-1 focus:ring-white placeholder:text-[#9B9B9B]"
        />
        <button
          onClick={() => sendMessage(inputRef.current.value)}
          className="ml-3 bg-[#3A3B41] p-3 rounded-xl text-white"
        >
          <FontAwesomeIcon icon={faPaperPlane} />
        </button>
      </div>
    </div>
  );
};

export default GTMChatbot;