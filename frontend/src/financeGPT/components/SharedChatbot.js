import React, { useState, useRef } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPaperPlane,
  faDownload,
  faFile,
} from "@fortawesome/free-solid-svg-icons";
import "../styles/Chatbot.css";

const SharedChatbot = (props) => {
  const context = props.context;
  const [message, setMessage] = useState("");
  const [uploadButtonClicked, setUploadButtonClicked] = useState(false);
  const inputRef = useRef(null);

  // Get chat ID from context or props
  console.log(context);

  if (!context) {
    return <div>404 not found</div>;
  }

  const id = context.chat_info.chat_id;

  return (
    <div className={`py-2 sticky top-0 h-full bg-transparent flex flex-col`}>
      <div className="w-full bg-transparent md:shadow-none shadow-lg md:mb-0  items-center flex justify-center  flex-shrink-0">
        <span className="text-white fixed items-center w-full max-w-4xl py-3  flex justify-center top-0 rounded  px-4">
          {context.chat_info.chat_name}
        </span>
      </div>
      <div
        className={`flex-1 rounded overflow-hidden ${
          context.messages.length > 0 ? "block" : "hidden"
        } flex justify-center min-h-0`}
      >
        <div
          ref={(ref) =>
            ref && ref.scrollTo({ top: ref.scrollHeight, behavior: "smooth" })
          }
          className="py-3 flex-col  px-4 flex gap-3 w-full max-w-4xl mx-6 overflow-y-auto"
        >
          {context.messages.map((msg, index) => (
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
                <p className="whitespace-pre-wrap">{msg.message_text}</p>

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
    </div>
  );
};

export default SharedChatbot;
