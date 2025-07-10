import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import PDFUploader from "./PdfUploader";
import {
  faFileDownload,
  faPaperPlane,
  faUndoAlt,
  faEye,
} from "@fortawesome/free-solid-svg-icons";
import "../styles/Chatbot.css";
import fetcher from "../../http/RequestConfig";
import { faLink } from "@fortawesome/free-solid-svg-icons";





const Chatbot = (props) => {
  const [messages, setMessages] = useState([]);
  const [isFirstMessageSent, setIsFirstMessageSent] = useState(false);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const responseColor = "black";
  const userColor = "black";

  //initial state
  useEffect(() => {
    loadLatestChat();
    handleLoadChat();
    setIsFirstMessageSent(false);
    setMessages([
      {
        message: "Hello, I am your Panacea, your agentic AI assistant. What can I do to help?",
        sentTime: "just now",
        direction: "incoming",
      },
    ]);
  }, []);

  useEffect(() => {
    if (props.selectedChatId === 0) {
      if (messages.length ===0) {
          handleLoadChat();
      }
    }else{
      handleLoadChat();
    }
    setIsFirstMessageSent(false);
  }, [props.selectedChatId, props.forceUpdate]);


  const scrollToBottom = () => {
    messagesEndRef.current.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  };

  const loadLatestChat = async () => {
    try {
      const response = await fetcher("find-most-recent-chat", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });

      const response_data = await response.json();

      props.handleChatSelect(response_data.chat_info.id);
      props.setCurrChatName(response_data.chat_info.chat_name)


    } catch (e) {
      console.error("Error during chat deletion", e);
    }
  }

  const handleDownload = async () => {
    if (props.selectedChatId === null) {
      console.log("Error: no chat selected"); //replace this later with a popup
    } else {
      try {
        const response = await fetcher('download-chat-history', {
          method: 'POST',
          headers: {
            Accept: 'text/csv',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ chat_id: props.selectedChatId, chat_type: props.chat_type }),
        });
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.setAttribute('download', 'chat_history.csv'); // or any other filename
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
      } catch (error) {
        console.error('Error downloading the file:', error);
      }
    }
  };


  const togglePopup = (index) => {
    props.setActiveMessageIndex(props.activeMessageIndex === index ? null : index);
  };

  const handleTryMessage = (text, chat_id, isPrivate) => {
    if (chat_id === null || chat_id === undefined) {
      props.createNewChat().then((newChatId) => {
        if (newChatId) {
          handleSendMessage(text, newChatId, isPrivate);
        } else {
          console.error("Failed to create new chat");
        }
      });
    } else {
      handleSendMessage(text, chat_id, isPrivate);
    }
  };

  const handleSendMessage = async (text, chat_id) => {
    inputRef.current.value = "";

    const tempMessageId = Date.now();
    setMessages((prevMessages) => [
      ...prevMessages,
      {
        message: text,
        direction: "outgoing",
      },
      {
        id: tempMessageId,
        message: "Loading...",
        direction: "incoming",
      },
    ]);

    try {
      scrollToBottom();
      const response = await fetcher("process-message-pdf", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          chat_id: chat_id,
          model_type: props.isPrivate,
          model_key: props.confirmedModelKey,
        }),
      });
      const response_data = await response.json();
      const answer = response_data.answer;
      setMessages((prevMessages) =>
        prevMessages.map((msg) =>
          msg.id === tempMessageId
            ? { ...msg, message: answer, id: undefined } // Replace the loading message
            : msg
        )
      );

      handleLoadChat();
      scrollToBottom();

      if (!isFirstMessageSent) {
        inferChatName(text, answer);
        setIsFirstMessageSent(true);
      }
    } catch (e) {
      console.error("Error in fetcher:", e);
    }

  };

  const inferChatName = async (text, answer) => {
    const combined_text = text.concat(answer);
    console.log("infer chat");
    try {
      const response = await fetcher("infer-chat-name", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: combined_text,
          chat_id: props.selectedChatId
        }),
      });
      const response_data = await response.json();
      console.log("response data 123", response_data.chat_name)
      props.setCurrChatName(response_data.chat_name);

      props.handleForceUpdate();
    } catch (error) {
      console.error("Error loading chat messages:", error);
    }

  };

  const handleLoadChat = async () => {

    if (props.selectedChatId === 0) {
      console.log("Guest session - not loading from database");
      // Only reset to welcome message if this is the initial load
      if (messages.length === 0) {
        setMessages([
          {
            message: "Hello, I am your Panacea, your agentic AI assistant. What can I do to help?",
            sentTime: "just now",
            direction: "incoming",
          },
        ]);
      }
      return;
    }
    try {
      const response = await fetcher("retrieve-messages-from-chat", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          chat_id: props.selectedChatId,
          chat_type: props.chat_type,
        }),
      });

      setMessages([
        {
          message: "Hello, I am your Panacea, your agentic AI assistant. What can I do to help?",
          sentTime: "just now",
          direction: "incoming",
        },
      ]);

      const response_data = await response.json();

      if (!response_data.messages || response_data.messages.length === 0) {
      console.log("⚠️ No messages returned from API");
      return;
      }

      const transformedMessages = response_data.messages.map((item) => ({
        message: item.message_text,
        direction: item.sent_from_user === 1 ? "outgoing" : "incoming",
        relevant_chunks: item.relevant_chunks,
      }));

      setMessages((prevMessages) => [...prevMessages, ...transformedMessages]);

      if (transformedMessages.length > 1) {
        setIsFirstMessageSent(true);
      } else {
        setIsFirstMessageSent(false);
      }

    } catch (error) {
      console.error("Error loading chat messages:", error);
    }
  };

  const resetServer = async () => {
    const response = await fetcher("reset-chat", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ chat_id: props.selectedChatId, delete_docs: true }),
    });
    const response_data = await response;
    props.handleForceUpdate();
  };

  return (
    <>
      <div className="min-h-[50vh] h-[85vh] mt-2 relative bg-[#141414]
 p-4 w-full rounded-2xl border-[#9B9B9B] border-2">
        {props.currChatName ? (
          <>
            <div className="flex flex-row justify-between">
              <FontAwesomeIcon
                icon={faUndoAlt}
                onClick={resetServer}
                className="reset-icon"
              />
              <div className="text-white font-bold">{props.currChatName}</div>
              <div className="download-button send-button">
                <FontAwesomeIcon
                  icon={faFileDownload}
                  onClick={handleDownload}
                  className="file-upload"
                />
              
              </div>
            </div>
            <hr />
            <div className="flex flex-col mt-4 space-y-2 h-[70vh] overflow-y-scroll relative">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`message ${msg.direction === "incoming" ? "incoming" : "outgoing"
                    }`}
                >
                  <div className="message-content">
                    <div
                      className="message-text"
                      style={{
                        color:
                          msg.direction === "incoming"
                            ? responseColor
                            : userColor,
                      }}
                    >
                      {msg.message}
                    </div>
                    {msg.direction === "incoming" && index != 0 && (
                      <FontAwesomeIcon
                        style={{
                          height: "13px",
                          cursor: "pointer",
                          marginLeft: "10px",
                        }}
                        icon={faEye}
                        onClick={() => togglePopup(index)}
                        className="eye-icon text-black"
                      />
                    )}

                    {props.activeMessageIndex === index && (
                      <div
                        style={{
                          position: "absolute",
                          border: "1px solid #ccc",
                          padding: "10px",
                          borderRadius: "5px",
                          boxShadow: "0 2px 10px rgba(0,0,0,0.2)",
                          width: "70%",
                          height: "30%",
                          overflowY: "auto",
                          whiteSpace: "pre-wrap",
                        }}
                        className="bg-[#141414] text-white"
                      >
                        {console.log(
                          "active message index",
                          props.activeMessageIndex,
                          index
                        )}
                        {console.log("xyz is", msg.relevant_chunks)}
                        {props.setRelevantChunk(msg.relevant_chunks)}
                        <p>{msg.relevant_chunks}</p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} /> {/* Empty div for scrolling */}
            </div>
            <div className="absolute bottom-7 flex items-center w-[95%] mx-auto ">
              <div className="mr-4 bg-gradient-to-r from-[#28b2fb] to-[#28b2fb] rounded-xl p-2 cursor-pointer text-black">
                <PDFUploader
                  className=""
                  chat_id={props.selectedChatId}
                  handleForceUpdate={props.handleForceUpdate}
                />
              </div>
              <input
                className="w-full rounded-xl bg-[#3A3B41] border-none focus:ring-0 focus:border-white text-white placeholder:text-gray-300"
                type="text"
                placeholder="Ask your document a question"
                ref={inputRef} // Assign the input ref
                onKeyPress={(e) => {
                  if (e.key === "Enter") {
                    const text = e.target.value;
                    handleTryMessage(
                      text,
                      props.selectedChatId,
                      props.isPrivate
                    );
                  }
                }}
              />
              <div
                className="text-white bg-[#28b2fb] p-2 rounded-xl ml-4 cursor-pointer"
                onClick={() => {
                  const text = inputRef.current.value; // Get the input value
                  handleTryMessage(text, props.selectedChatId, props.isPrivate);
                }}
              >
                <FontAwesomeIcon className="w-8" icon={faPaperPlane} />
              </div>
            </div>
          </>
        ) : (
          <div className="text-white">
            Create a new chat from left sidebar
          </div>
        )}

      </div>
    </>
  );
};

export default Chatbot;
