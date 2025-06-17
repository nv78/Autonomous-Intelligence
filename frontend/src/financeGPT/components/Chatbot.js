import React, { useState, useEffect, useRef } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import PDFUploader from "./PdfUploader";
import {
  faFileDownload,
  faDownload,
  faPaperPlane,
  faUndoAlt,
  faEye,
} from "@fortawesome/free-solid-svg-icons";
import "../styles/Chatbot.css";
import fetcher from "../../http/RequestConfig";
import { useLocation, useNavigate, useParams } from "react-router-dom";

const Chatbot = (props) => {
  const [message, setMessage] = useState(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { id } = useParams();
  const [isFirstMessageSent, setIsFirstMessageSent] = useState(false);

  const location = useLocation();
  const [messages, setMessages] = useState([]);
  //initial state

  const handleLoadChat = async () => {
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
      console.log("response_data", response_data);
      if (!response_data.messages.length) return;
      const transformedMessages = response_data.messages.map((item) => ({
        content: item.message_text,
        role: item.sent_from_user === 1 ? "user" : "assistant",
        relevant_chunks: item.relevant_chunks,
      }));
      console.log("here ", transformedMessages);
      setMessages(transformedMessages);
    } catch (error) {
      console.log("???");
      console.log(error);
    }
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
      props.setCurrChatName(response_data.chat_info.chat_name);
    } catch (e) {
      console.error("Error during chat deletion", e);
    }
  };

  // useEffect(() => {
  //   loadLatestChat();
  //   handleLoadChat();
  // }, [])

  useEffect(() => {
    console.log("use effect");
    // };
    // if (id) handleLoadChat();
    // const loadLatestChat = async () => {
    //   try {
    //     const response = await fetcher("find-most-recent-chat", {
    //       method: "POST",
    //       headers: {
    //         Accept: "application/json",
    //         "Content-Type": "application/json",
    //       },
    //       body: JSON.stringify({}),
    //     });

    //     const response_data = await response.json();
    //     if (!response_data) return;
    //     props.handleChatSelect(response_data.chat_info.id);
    //     props.setCurrChatName(response_data.chat_info.chat_name);
    //   } catch (e) {
    //     console.error("Error during chat deletion", e);
    //   }
    // };
    //     const response_data = await response.json();
    //     console.log("chat response_data", props);

    //     const transformedMessages = response_data.messages.map((item) => ({
    //       content: item.message_text,
    //       role: item.sent_from_user === 1 ? "user" : "assistants",
    //       relevant_chunks: item.relevant_chunks,
    //     }));

    //     setMessages((prevMessages) => [
    //       ...prevMessages,
    //       ...transformedMessages,
    //     ]);

    //     if (transformedMessages.length > 1) {
    //       setIsFirstMessageSent(true);
    //     } else {
    //       setIsFirstMessageSent(false);
    //     }
    //   } catch (error) {
    //     console.error("Error loading chat messages:", error);
    //   }
    // };
    //   // setIsFirstMessageSent(false);
    //   // setMessages((prev) => [...prev, { content: "a", role: "assistant" }]);
    //   // setMessages([
    //   //   {
    //   //     content:
    //   //       "Hello, I am your Panacea, your agentic AI assistant. What can I do to help?",
    //   //     sentTime: "just now",
    //   //     role: "assistant",
    //   //   },
    //   // ]);
    //   // const resolve = () => dispatch(viewUser)
    //   // resolve()
    handleLoadChat();
  }, [props.selectedChatId, props.forceUpdate]);

  // const scrollToBottom = () => {
  //   messagesEndRef.current.scrollIntoView({
  //     behavior: "smooth",
  //     block: "end",
  //   });
  // };

  // const handleDownload = async () => {
  //   if (props.selectedChatId === null) {
  //     console.log("Error: no chat selected"); //replace this later with a popup
  //   } else {
  //     try {
  //       const response = await fetcher("download-chat-history", {
  //         method: "POST",
  //         headers: {
  //           Accept: "text/csv",
  //           "Content-Type": "application/json",
  //         },
  //         body: JSON.stringify({
  //           chat_id: props.selectedChatId,
  //           chat_type: props.chat_type,
  //         }),
  //       });
  //       const blob = await response.blob();
  //       const downloadUrl = window.URL.createObjectURL(blob);
  //       const link = document.createElement("a");
  //       link.href = downloadUrl;
  //       link.setAttribute("download", "chat_history.csv"); // or any other filename
  //       document.body.appendChild(link);
  //       link.click();
  //       link.parentNode.removeChild(link);
  //     } catch (error) {
  //       console.error("Error downloading the file:", error);
  //     }
  //   }
  // };

  // const togglePopup = (index) => {
  //   props.setActiveMessageIndex(
  //     props.activeMessageIndex === index ? null : index
  //   );
  // };

  // const handleTryMessage = (text, chat_id, isPrivate) => {
  //   if (chat_id === null || chat_id === undefined) {
  //     props.createNewChat().then((newChatId) => {
  //       if (newChatId) {
  //         handleSendMessage(text, newChatId, isPrivate);
  //       } else {
  //         console.error("Failed to create new chat");
  //       }
  //     });
  //   } else {
  //     handleSendMessage(text, chat_id, isPrivate);
  //   }
  // };

  // const handleSendMessage = async (text, chat_id) => {
  //   inputRef.current.value = "";

  //   const tempMessageId = Date.now();
  //   setMessages((prevMessages) => [
  //     ...prevMessages,
  //     {
  //       message: text,
  //       direction: "outgoing",
  //     },
  //     {
  //       id: tempMessageId,
  //       message: "Loading...",
  //       direction: "incoming",
  //     },
  //   ]);

  //   try {
  //     // scrollToBottom();
  //     const response = await fetcher("process-message-pdf", {
  //       method: "POST",
  //       headers: {
  //         Accept: "application/json",
  //         "Content-Type": "application/json",
  //       },
  //       body: JSON.stringify({
  //         message: text,
  //         chat_id: chat_id,
  //         model_type: props.isPrivate,
  //         model_key: props.confirmedModelKey,
  //       }),
  //     });
  //     const response_data = await response.json();
  //     const answer = response_data.answer;
  //     setMessages((prevMessages) =>
  //       prevMessages.map((msg) =>
  //         msg.id === tempMessageId
  //           ? { ...msg, message: answer, id: undefined } // Replace the loading message
  //           : msg
  //       )
  //     );

  //     // handleLoadChat();
  //     // scrollToBottom();

  //     // if (!isFirstMessageSent) {
  //     //   inferChatName(text, answer);
  //     //   setIsFirstMessageSent(true);
  //     // }
  //   } catch (e) {
  //     console.error("Error in fetcher:", e);
  //   }
  // };

  const handleTryMessage = async (event) => {
    event.preventDefault();
    const currentPath = window.location.pathname;
    // Check if on root

    if (currentPath === "/") {
      // Create a new chat (assuming this returns a new chat ID or object)
      const newChat = await props.createNewChat(); // make sure this returns ID or dat
      // Navigate to new chat path  
      handleForm(event, newChat, "new");
      // navigate(`/chat/${newChat}`, { replace: true, state: { message, messages } });
    } else {
      handleForm(event, id, "old");
    }
  };

  function isScrolledToBottom(element) {
    if (element) {
      element.scroll({ top: element.scrollHeight, behavior: "smooth" });
    }
  }

  async function handleForm(e, id, type) {
    console.log("id", id);
    e.preventDefault();
    console.log("state", location.state);
    const inputMessage = message || location.state?.message;

    if (!inputMessage) return;

    setMessage("");
    setMessages((messages) => [
      ...messages,
      { chat_id: id, role: "user", content: inputMessage },
      { chat_id: id, role: "assistant", content: "Thinking..." },
    ]);

    try {
      const response = await fetcher(`process-message-pdf`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: inputMessage,
          chat_id: id ? Number(id) : props.selectedChatId,
          model_type: props.isPrivate,
          model_key: props.confirmedModelKey,
        }),
      });

      const response_data = await response.json();
      const answer = response_data.answer;
      console.log("answer before setMessage", props.forceUpdate);
      setMessages((messages) => {
        let lastMessage = messages[messages.length - 1];
        let otherMessages = messages.slice(0, messages.length - 1);
        return [
          ...otherMessages,
          {
            ...lastMessage,
            id: response_data.id,
            content:
              lastMessage.content === "Thinking..."
                ? answer
                : lastMessage.content + answer,
          },
        ];
      });
      if(type === "new") navigate(`/chat/${id}`, { state: { message } });
      await handleLoadChat()

      if (!isFirstMessageSent) {
        inferChatName(inputMessage, answer);
        setIsFirstMessageSent(true);
      }
    } catch (error) {
      console.log(error);
    }
  }

  const inferChatName = async (text, answer) => {
    // const combined_text = text.concat(answer);
    // console.log("infer chat");
    // try {
    //   const response = await fetcher("infer-chat-name", {
    //     method: "POST",
    //     headers: {
    //       Accept: "application/json",
    //       "Content-Type": "application/json",
    //     },
    //     body: JSON.stringify({
    //       messages: combined_text,
    //       chat_id: props.selectedChatId ?? 1,
    //     }),
    //   });
    //   const response_data = await response.json();
    //   console.log("response data 123", response_data.chat_name);
    //   props.setCurrChatName(response_data.chat_name);
    //   console.log(props.currChatName)
    //   props.handleForceUpdate();
    // } catch (error) {
    //   console.error("Error loading chat messages:", error);
    props.setCurrChatName(text);
    props.handleForceUpdate();
  };

  // const resetServer = async () => {
  //   const response = await fetcher("reset-chat", {
  //     method: "POST",
  //     headers: {
  //       Accept: "application/json",
  //       "Content-Type": "application/json",
  //     },
  //     body: JSON.stringify({
  //       chat_id: props.selectedChatId,
  //       delete_docs: true,
  //     }),
  //   });
  //   const response_data = await response;
  //   props.handleForceUpdate();
  // };

  return (
    <div
      className={`md:pt-16 py-2 px-5 h-full w-full ${
        props.menu ? "md:pl-7 md:blur-none blur" : "m"
      }`}
    >
      <div className={`w-full items-center flex justify-center`}>
        <span className="md:hidden rounded py-2 px-4 ">
          {props.currChatName}
        </span>
      </div>
      <div
        ref={isScrolledToBottom}
        className={`h-3/4 rounded overflow-auto  ${
          messages.length > 0 ? "block" : "hidden"
        }`}
      >
        <div className=" py-3 flex-col mt-4  px-4 flex gap-3">
          {messages.map((message) => (
            <div
              key={`${message.chat_id}-${message.id}`}
              className={`flex items-center gap-4 ${
                message.role === "user" ? "justify-end" : ""
              }`}
            >
              <p className="bg-bc-red/15 rounded-lg p-2 whitespace-pre-wrap">
                {message.content}
              </p>
            </div>
          ))}
        </div>
      </div>
      <div
        className={
          messages.length === 0
            ? "h-5/6 w-full flex items-center gap-2 flex-col justify-center"
            : "block"
        }
      >
        <div
          className={`${
            messages.length === 0
              ? "w-full animate-typing overflow-hidden whitespace-nowrap flex items-center justify-center font-bold text-2xl"
              : "hidden"
          }`}
        >
          What can I help you with?
        </div>
        <form
          id="chat-form"
          className={
            "w-full  mt-2 shadow-lg py-2 flex  px-4 bg-gray-50 overflow-hidden rounded-xl  border-gray-200 transition-all duration-200"
          }
          onSubmit={handleTryMessage}
        >
          <div className="w-full">
            <textarea
              className="w-full  border-none resize-none text-lg px-2 focus:ring-0 focus:outline-none text-gray-700 placeholder:text-gray-500 bg-transparent"
              type="text"
              maxLength={1872}
              rows={messages.length === null ? 1 : 2}
              cols={8}
              placeholder="Type a question to explore your document..."
              value={message}
              required={message === null}
              onChange={(e) => {
                e.preventDefault();
                setMessage(e.target.value);
              }}
              ref={inputRef}
            />

            <div className="flex justify-start items-center">
              <div className="w-full gap-2 flex">
                <div className="border rounded-xl py-1">
                  <button
                    onClick={(e) => e}
                    type="button"
                    className="px-2 flex gap-1 text-center"
                  >
                    <FontAwesomeIcon icon={faDownload} />
                    <span className="text-sm">Attach</span>
                  </button>
                </div>
                <div className="border rounded-xl py-1">
                  <button type="button" className="px-2 flex gap-1 text-center">
                    <span className="text-sm">agents</span>
                  </button>
                </div>
              </div>
              <button
                form="chat-form"
                type="submit"
                disabled={!message}
                className="hover:text-blue-500 disabled:hover:text-gray-700 text-gray-400 transition-colors"
              >
                <FontAwesomeIcon icon={faPaperPlane} />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );

  //             <div className="flex flex-row justify-between">
  //               <FontAwesomeIcon
  //                 icon={faUndoAlt}
  //                 onClick={resetServer}
  //                 className="reset-icon"
  //               />
  //               <div className="text-white font-bold">{props.currChatName}</div>
  //               <div className="download-button send-button">
  //                 <FontAwesomeIcon
  //                   icon={faFileDownload}
  //                   onClick={handleDownload}
  //                   className="file-upload"
  //                 />
  //               </div>
  //             </div>
  //             <hr />
  //             <div className="flex flex-col mt-4 space-y-2 h-[70vh] overflow-y-scroll relative">
  //               {messages.map((msg, index) => (
  //                 <div
  //                   key={index}
  //                   className={`message ${msg.direction === "incoming" ? "incoming" : "outgoing"
  //                     }`}
  //                 >
  //                   <div className="message-content">
  //                     <div
  //                       className="message-text"
  //                       style={{
  //                         color:
  //                           msg.direction === "incoming"
  //                             ? responseColor
  //                             : userColor,
  //                       }}
  //                     >
  //                       {msg.message}
  //                     </div>
  //                     {msg.direction === "incoming" && index != 0 && (
  //                       <FontAwesomeIcon
  //                         style={{
  //                           height: "13px",
  //                           cursor: "pointer",
  //                           marginLeft: "10px",
  //                         }}
  //                         icon={faEye}
  //                         onClick={() => togglePopup(index)}
  //                         className="eye-icon text-black"
  //                       />
  //                     )}

  //                     {props.activeMessageIndex === index && (
  //                       <div
  //                         style={{
  //                           position: "absolute",
  //                           border: "1px solid #ccc",
  //                           padding: "10px",
  //                           borderRadius: "5px",
  //                           boxShadow: "0 2px 10px rgba(0,0,0,0.2)",
  //                           width: "70%",
  //                           height: "30%",
  //                           overflowY: "auto",
  //                           whiteSpace: "pre-wrap",
  //                         }}
  //                         className="bg-[#141414] text-white"
  //                       >
  //                         {console.log(
  //                           "active message index",
  //                           props.activeMessageIndex,
  //                           index
  //                         )}
  //                         {console.log("xyz is", msg.relevant_chunks)}
  //                         {props.setRelevantChunk(msg.relevant_chunks)}
  //                         <p>{msg.relevant_chunks}</p>
  //                       </div>
  //                     )}
  //                   </div>
  //                 </div>
  //               ))}
  //               <div ref={messagesEndRef} /> {/* Empty div for scrolling */}
  //             </div>
  //             <div className="absolute bottom-7 flex items-center w-[95%] mx-auto ">
  //               <div className="mr-4 bg-gradient-to-r from-[#28b2fb] to-[#28b2fb] rounded-xl p-2 cursor-pointer text-black">
  //                 <PDFUploader
  //                   className=""
  //                   chat_id={props.selectedChatId}
  //                   handleForceUpdate={props.handleForceUpdate}
  //                 />
  //               </div>
  //               <input
  //                 className="w-full rounded-xl bg-[#3A3B41] border-none focus:ring-0 focus:border-white text-white placeholder:text-gray-300"
  //                 type="text"
  //                 placeholder="Ask your document a question"
  //                 ref={inputRef} // Assign the input ref
  //                 onKeyPress={(e) => {
  //                   if (e.key === "Enter") {
  //                     const text = e.target.value;
  //                     handleTryMessage(
  //                       text,
  //                       props.selectedChatId,
  //                       props.isPrivate
  //                     );
  //                   }
  //                 }}
  //               />
  //               <div
  //                 className="text-white bg-[#28b2fb] p-2 rounded-xl ml-4 cursor-pointer"
  //                 onClick={() => {
  //                   const text = inputRef.current.value; // Get the input value
  //                   handleTryMessage(text, props.selectedChatId, props.isPrivate);
  //                 }}
  //               >
  //                 <FontAwesomeIcon className="w-8" icon={faPaperPlane} />
  //               </div>
  //             </div>

  //return (
  //     <>
  //       <div className=" mt-2 relative bg-[#141414]
  //  p-4 w-full rounded-2xl border-[#9B9B9B] border-2">
  //         {props.currChatName ? (
  //           <>
  //             <div className="flex flex-row justify-between">
  //               <FontAwesomeIcon
  //                 icon={faUndoAlt}
  //                 onClick={resetServer}
  //                 className="reset-icon"
  //               />
  //               <div className="text-white font-bold">{props.currChatName}</div>
  //               <div className="download-button send-button">
  //                 <FontAwesomeIcon
  //                   icon={faFileDownload}
  //                   onClick={handleDownload}
  //                   className="file-upload"
  //                 />
  //               </div>
  //             </div>
  //             <hr />
  //             <div className="flex flex-col mt-4 space-y-2 h-[70vh] overflow-y-scroll relative">
  //               {messages.map((msg, index) => (
  //                 <div
  //                   key={index}
  //                   className={`message ${msg.direction === "incoming" ? "incoming" : "outgoing"
  //                     }`}
  //                 >
  //                   <div className="message-content">
  //                     <div
  //                       className="message-text"
  //                       style={{
  //                         color:
  //                           msg.direction === "incoming"
  //                             ? responseColor
  //                             : userColor,
  //                       }}
  //                     >
  //                       {msg.message}
  //                     </div>
  //                     {msg.direction === "incoming" && index != 0 && (
  //                       <FontAwesomeIcon
  //                         style={{
  //                           height: "13px",
  //                           cursor: "pointer",
  //                           marginLeft: "10px",
  //                         }}
  //                         icon={faEye}
  //                         onClick={() => togglePopup(index)}
  //                         className="eye-icon text-black"
  //                       />
  //                     )}

  //                     {props.activeMessageIndex === index && (
  //                       <div
  //                         style={{
  //                           position: "absolute",
  //                           border: "1px solid #ccc",
  //                           padding: "10px",
  //                           borderRadius: "5px",
  //                           boxShadow: "0 2px 10px rgba(0,0,0,0.2)",
  //                           width: "70%",
  //                           height: "30%",
  //                           overflowY: "auto",
  //                           whiteSpace: "pre-wrap",
  //                         }}
  //                         className="bg-[#141414] text-white"
  //                       >
  //                         {console.log(
  //                           "active message index",
  //                           props.activeMessageIndex,
  //                           index
  //                         )}
  //                         {console.log("xyz is", msg.relevant_chunks)}
  //                         {props.setRelevantChunk(msg.relevant_chunks)}
  //                         <p>{msg.relevant_chunks}</p>
  //                       </div>
  //                     )}
  //                   </div>
  //                 </div>
  //               ))}
  //               <div ref={messagesEndRef} /> {/* Empty div for scrolling */}
  //             </div>
  //             <div className="absolute bottom-7 flex items-center w-[95%] mx-auto ">
  //               <div className="mr-4 bg-gradient-to-r from-[#28b2fb] to-[#28b2fb] rounded-xl p-2 cursor-pointer text-black">
  //                 <PDFUploader
  //                   className=""
  //                   chat_id={props.selectedChatId}
  //                   handleForceUpdate={props.handleForceUpdate}
  //                 />
  //               </div>
  //               <input
  //                 className="w-full rounded-xl bg-[#3A3B41] border-none focus:ring-0 focus:border-white text-white placeholder:text-gray-300"
  //                 type="text"
  //                 placeholder="Ask your document a question"
  //                 ref={inputRef} // Assign the input ref
  //                 onKeyPress={(e) => {
  //                   if (e.key === "Enter") {
  //                     const text = e.target.value;
  //                     handleTryMessage(
  //                       text,
  //                       props.selectedChatId,
  //                       props.isPrivate
  //                     );
  //                   }
  //                 }}
  //               />
  //               <div
  //                 className="text-white bg-[#28b2fb] p-2 rounded-xl ml-4 cursor-pointer"
  //                 onClick={() => {
  //                   const text = inputRef.current.value; // Get the input value
  //                   handleTryMessage(text, props.selectedChatId, props.isPrivate);
  //                 }}
  //               >
  //                 <FontAwesomeIcon className="w-8" icon={faPaperPlane} />
  //               </div>
  //             </div>
  //           </>
  //         ) : (
  //           <div className="text-white">
  //             Create a new chat from left sidebar
  //           </div>
  //         )}
  //       </div>
  //     </>
  //   );
};

export default Chatbot;
