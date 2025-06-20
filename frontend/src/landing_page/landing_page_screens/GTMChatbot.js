import React from "react";
import Chatbot from "../landing_page_components/Chatbot/Chatbot.js"

const GTMChatbot = ()  => {
  console.log("✅ GTMChatbot component loaded");
  return (
    <div className="text-white text-center mt-10">
      <h1 className="text-4xl font-bold mb-4">GTM Chatbot</h1>
      <p>This is your go-to-market chatbot builder page!</p>
      <Chatbot />
    </div>
  );
}

export default GTMChatbot;
