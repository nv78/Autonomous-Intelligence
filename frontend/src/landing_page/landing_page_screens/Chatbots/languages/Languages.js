import React, { useState, useEffect, useRef } from "react";
import { LANGUAGE_ROUTES } from "../../../../constants/RouteConstants";
import { useParams, useNavigate } from "react-router-dom";


const LANGUAGE_MODELS = {
  korean: "GPT-4",
  spanish: "GPT-3.5",
  japanese: "Claude 3",
  arabic: "GPT-4",
  chinese: "GPT-4",
};

const LANGUAGE_API_ENDPOINTS = { //fill in with model fetch links
    spanish: "/api/chat/spanish",
    korean: "/api/chat/korean",
    japanese: "/api/chat/japanese",
    arabic: "/api/chat/arabic",
    chinese: "/api/chat/chinese",
  };

const validLanguages = Object.keys(LANGUAGE_MODELS);
const Languages = () => {
    const [selectedLanguage, setSelectedLanguage] = useState("english");
    const navigate = useNavigate();
    const { lang } = useParams();

    const initialLang = validLanguages.includes(lang) ? lang : "spanish";
    // Hooks must be called always, so move this above the early return
    const [messages, setMessages] = useState([
      { message: "Hello! Choose a language and start chatting.", direction: "incoming" },
    ]);
    const inputRef = useRef(null);
    const scrollRef = useRef(null);
  
    // Redirect to Spanish if no language is selected
    useEffect(() => {
        if (!lang || !validLanguages.includes(lang)) {
        navigate("/languages/spanish", { replace: true });
        }
    }, [lang, navigate]);
  
    useEffect(() => {
        if (lang && validLanguages.includes(lang)) {
          setSelectedLanguage(lang);
        }
      }, [lang]);

    useEffect(() => {
        scrollRef.current?.scrollTo({
          top: scrollRef.current.scrollHeight,
          behavior: "smooth",
        });
      }, [messages]);
      
    if (!lang || !validLanguages.includes(lang)) return null;
      
  
    const sendMessage = async (text) => {
      if (!text.trim()) return;
      inputRef.current.value = "";
  
      const tempId = Date.now();
      setMessages((prev) => [
        ...prev,
        { message: text, direction: "outgoing" },
        { message: "Thinking...", direction: "incoming", id: tempId },
      ]);
  
      try {
        const apiUrl = LANGUAGE_API_ENDPOINTS[selectedLanguage] || "/api/chat/spanish";

        const res = await fetch(apiUrl, {

          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text }),
        });
  
        const data = await res.json();
  
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === tempId
              ? { message: data.response, direction: "incoming" }
              : msg
          )
        );
      } catch (error) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === tempId
              ? { message: "❌ Error fetching response.", direction: "incoming" }
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
  
    // ... rest of your JSX remains unchanged
  
    return (
      <section className="min-h-screen bg-black text-white p-6">
        {/* Title */}
        <h1 className="text-4xl font-bold text-center mb-8">
          <span className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">
            Languages
          </span>
        </h1>
  
        {/* Main Row Layout */}
        <div className="flex flex-col md:flex-row gap-8 justify-center items-start">
          {/* Language Selector on the Left */}
          <div className="w-full md:w-1/4 flex flex-col items-center md:items-start">
            <select
              value={selectedLanguage}
              onChange={(e) => {
                const lang = e.target.value;
                setSelectedLanguage(lang);
                navigate(`/languages/${lang.toLowerCase()}`);
              }}
              className="mt-6 bg-gray-800 text-white border border-gray-600 rounded px-4 py-2 w-full mb-2"
            >
              {Object.keys(LANGUAGE_MODELS).map((lang) => (
                <option key={lang} value={lang}>
                  {lang.charAt(0).toUpperCase() + lang.slice(1)}
                </option>
              ))}
            </select>
  
            <p className="text-xs text-gray-400">
              Model:{" "}
              <span className="text-green-400">
                {LANGUAGE_MODELS[selectedLanguage]}
              </span>
            </p>
  
            <p className="text-[10px] text-gray-500 mt-6">
              Each language uses the best model from our{" "}
              <a href="/models" className="underline text-blue-300 hover:text-blue-100">
                leaderboard
              </a>
              .
            </p>
          </div>
  
          {/* Chat UI on the Right */}
          <div className="w-full md:w-3/4 bg-[#1a1a1a] rounded-xl p-4 h-[70vh] flex flex-col shadow-md">
            {/* Header */}
            <div className="flex justify-between items-center mb-2">
              <div></div>
              <h2 className="text-md font-medium text-white">Chat</h2>
              <div className="text-xs text-green-400">
                {LANGUAGE_MODELS[selectedLanguage]}
              </div>
            </div>
            <hr className="border-gray-600 mb-2" />
  
            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 pr-2">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${
                    msg.direction === "incoming" ? "justify-start" : "justify-end"
                  }`}
                >
                  <div className="rounded-2xl px-4 py-2 max-w-[75%] bg-[#2e2e2e] text-white">
                    {msg.message}
                  </div>
                </div>
              ))}
            </div>
  
            {/* Input */}
            <div className="flex items-center mt-4">
              <input
                ref={inputRef}
                type="text"
                placeholder="Type your message..."
                onKeyDown={handleKeyPress}
                className="flex-grow px-4 py-2 rounded-xl bg-[#141414] text-white border border-[#9b9b9b] focus:outline-none placeholder:text-[#9B9B9B]"
              />
              <button
                onClick={() => sendMessage(inputRef.current.value)}
                className="ml-3 bg-[#3A3B41] p-3 rounded-xl text-white"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      </section>
    );
  };
  
  export default Languages;
  