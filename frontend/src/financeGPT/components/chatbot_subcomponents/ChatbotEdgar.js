import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faFileDownload,
  faPaperPlane,
  faUndoAlt,
  faEye,
  faPen,
} from "@fortawesome/free-solid-svg-icons";
import "../../styles/Chatbot.css";
import fetcher from "../../../http/RequestConfig";

const ChatbotEdgar = (props) => {
  const [messages, setMessages] = useState([]);
  const [isFirstMessageSent, setIsFirstMessageSent] = useState(false);
  const inputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const responseColor = "black";
  const userColor = "black";

  //const [showChatbot, setShowChatbot] = useState(false);
  //const [ticker, setTicker] = useState('');
  const [isValidTicker, setIsValidTicker] = useState(false);

  const [showEditModal, setShowEditModal] = useState(false);

  const [isUploading, setIsUploading] = useState(false);

  //initial state
  useEffect(() => {
    handleLoadChat();
    setIsFirstMessageSent(false);
    if (props.ticker) {
      setMessages([
        {
          message: `Hello, I am your Panacea, your agentic AI assistant. I can answer questions about the company ${props.ticker}, how can I help you?`,
          sentTime: "just now",
          direction: "incoming",
        },
      ]);
    } else {
      setMessages([
        {
          message: "Hello, I am your Panacea, your agentic AI assistant. What can I do to help?",
          sentTime: "just now",
          direction: "incoming",
        },
      ]);
    }
  }, []);

  useEffect(() => {
    handleLoadChat();
    setIsFirstMessageSent(false);
  }, [props.selectedChatId, props.forceUpdate]);

  const scrollToBottom = () => {
    messagesEndRef.current.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  };

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

  const inferChatName = async(text, answer) => {
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
    try {
      console.log("chat type is", props.chat_type);
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

      if (props.ticker) {
        setMessages([
          {
            message: `Hello, I am your Panacea, your agentic AI assistant. I can answer questions about the company ${props.ticker}, how can I help you?`,
            sentTime: "just now",
            direction: "incoming",
          },
        ]);
      } else {
        setMessages([
          {
            message:
              "Hello, I am your Panacea, your agentic AI assistant. What can I do to help?",
            sentTime: "just now",
            direction: "incoming",
          },
        ]);
      }

      const response_data = await response.json();

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

  //Edgar specific stuff
  const checkTickerValidity = async (inputTicker) => {
    const response = await fetcher("check-valid-ticker", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ticker: inputTicker }),
    });

    const data = await response.json();
    console.log("tiker abc", inputTicker);
    console.log("data is", data.isValid);
    setIsValidTicker(data.isValid);
  };

  const handleTickerChange = (e) => {
    const inputTicker = e.target.value.toUpperCase(); // Convert to uppercase
    props.setTicker(inputTicker);
    checkTickerValidity(inputTicker);
  };

  const processTickerInfo = () => {
    if (props.isEdit) {
      setShowEditModal(true);
    } else {
      if (props.ticker) {
        setMessages([
          {
            message: `Hello, I am your Panacea, your agentic AI assistant. I can answer questions about the company ${props.ticker}, how can I help you?`,
            sentTime: "just now",
            direction: "incoming",
          },
        ]);
        processTickerBackend(props.ticker);
        addTickerdb(props.ticker, props.isEdit);
        props.setShowChatbot(true);
        props.setIsEdit(0);
      }
    }
  };

  const addTickerdb = async (ticker, isUpdate) => {
    const response = await fetcher("add-ticker-to-chat", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: props.selectedChatId,
        ticker: ticker,
        isUpdate: isUpdate,
      }),
    });
  };

  const processTickerBackend = async (ticker) => {
    setIsUploading(true);
    try {
      const response = await fetcher("process-ticker-info", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_id: props.selectedChatId, ticker: ticker }),
      });
    } catch (error) {
      console.error("Error in processTickerBackend:", error);
    } finally {
      setIsUploading(false);
      props.handleForceUpdate(true);
    }
  };

  const handleEditTicker = async () => {
    props.setIsEdit(1);
  };

  const confirmEditTicker = () => {
    if (props.ticker) {
      setMessages([
        {
          message: `Hello, I am your Panacea, your agentic AI assistant. I can answer questions about the company ${props.ticker}, how can I help you?`,
          sentTime: "just now",
          direction: "incoming",
        },
      ]);
      processTickerBackend(props.ticker);
      addTickerdb(props.ticker, props.isEdit);
      props.setShowChatbot(true);
      props.setIsEdit(0);
      setShowEditModal(false);
    }
  };

  const cancelEditTicker = () => {
    setShowEditModal(false);
  };

  const splashScreenStyle = {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    backgroundColor: "rgba(0, 0, 0, 0.7)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontSize: "1.5rem",
    color: "white",
    zIndex: 1000,
  };

  const confirmEditPopup = showEditModal ? (
    <div
      className="bg-[#141414]
 text-white p-5"
      style={{
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 1000,

        boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
        textAlign: "center",
      }}
    >
      <p className="mb-2">
        Warning: You are changing the ticker. This will reset your current chat
        and delete its history. Are you sure you want to proceed?
      </p>
      <button
        onClick={confirmEditTicker}
        className="p-2 my-1 w-1/6 bg-gray-600 rounded-lg hover:bg-gray-500 mr-5"
      >
        Yes
      </button>
      <button
        onClick={cancelEditTicker}
        className="p-2 my-1 w-1/6 bg-gray-600 rounded-lg hover:bg-gray-500"
      >
        No
      </button>
    </div>
  ) : null;

  return (
    <div>
      {confirmEditPopup}
      {isUploading && (
        <div style={splashScreenStyle}>Processing Document...</div>
      )}
      <div className="bg-[#141414]
 mt-2 px-4 py-2 rounded-xl">
        <div>
          <div className="flex flex-row w-full items-baseline">
            <h2 className="text-white w-1/3" htmlFor="ticker-input">
              Enter ticker:
            </h2>
            <input
              className="w-full disabled:cursor-not-allowed disabled:text-gray-300 text-white rounded-xl bg-[#3A3B41] border-none focus:ring-0 focus:border-white  placeholder:text-gray-300"
              type="text"
              id="ticker-input"
              placeholder="e.g. AAPL"
              value={props.ticker}
              onChange={handleTickerChange}
              disabled={props.showChatbot === true && props.isEdit === 0}
            />
            {props.showChatbot === true && props.isEdit === 0 ? (
              <button
                className="mx-2 px-3 py-2 rounded-xl mb-2 hover:bg-gray-700 text-white"
                // Style for the new button
                onClick={handleEditTicker}
              >
                <FontAwesomeIcon icon={faPen} />
              </button>
            ) : (
              <button
                onClick={processTickerInfo}
                className="mx-2 font-bold px-3 py-2 rounded-xl mb-2 hover:bg-gray-700 text-white"
              >
                &#10003; {/* Check Mark */}
              </button>
            )}
          </div>
          <div className="text-center mt-0.5">
            {isValidTicker ? (
              <div className="text-green-500">
                Now you may ask a question based on {props.ticker}.
              </div>
            ) : (
              <div className="text-red-600">
                Ticker {props.ticker} is invalid.
              </div>
            )}
          </div>
        </div>
      </div>
      {/* Chatbot */}
      {props.showChatbot && (
        <div className="min-h-[90vh] h-[90vh] mt-2 relative bg-[#141414]
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
                    className={`message ${
                      msg.direction === "incoming" ? "incoming" : "outgoing"
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
                          className="eye-icon text-white"
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
                          className="bg-[#141414]
 text-white"
                        >
                          {console.log(
                            "active message index",
                            props.activeMessageIndex,
                            index
                          )}
                          {props.setRelevantChunk(msg.relevant_chunks)}
                          <p>{msg.relevant_chunks}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} /> {/* Empty div for scrolling */}
              </div>
              <div className="absolute bottom-12 flex items-center w-[95%] mx-auto ">
                <input
                  className="w-full rounded-xl bg-[#3A3B41] border-none focus:ring-0 focus:border-white text-white placeholder:text-gray-300"
                  type="text"
                  placeholder="Ask your 10-K a question"
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
                  className="text-white bg-[#3A3B41] p-2 rounded-xl ml-4 cursor-pointer"
                  onClick={() => {
                    const text = inputRef.current.value; // Get the input value
                    handleTryMessage(
                      text,
                      props.selectedChatId,
                      props.isPrivate
                    );
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
      )}
    </div>
  );
};

export default ChatbotEdgar;
