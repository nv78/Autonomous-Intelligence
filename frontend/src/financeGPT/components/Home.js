import React, { Component, useState, useEffect } from "react";
import Navbarchatbot from "./NavbarChatbot";
import Chatbot from "./Chatbot";
import "../styles/Chatbot.css";
import SidebarChatbot from "./SidebarChatbot";
import fetcher from "../../http/RequestConfig";
import ChatbotEdgar from "./chatbot_subcomponents/ChatbotEdgar";

function HomeChatbot({ isLoggedIn }) {
  const [selectedChatId, setSelectedChatId] = useState(null);
  const [forceUpdate, setForceUpdate] = useState(0);
  const [isPrivate, setIsPrivate] = useState(0);
  const [currChatName, setCurrChatName] = useState("");
  const [currTask, setcurrTask] = useState(0); //0 is file upload, 1 EDGAR, 2 mySQL db; have 0 be the default
  const [ticker, setTicker] = useState("");
  const [showChatbot, setShowChatbot] = useState(false);
  const [isEdit, setIsEdit] = useState(0); //for whether you can currently edit the ticker or not
  const [activeMessageIndex, setActiveMessageIndex] = useState(null);
  const [relevantChunk, setRelevantChunk] = useState('');

  const [confirmedModelKey, setConfirmedModelKey] = useState("");

  const handleChatSelect = (chatId) => {
    if (!isLoggedIn) return;
    setSelectedChatId(chatId);
  };

  const handleForceUpdate = () => {
    setForceUpdate((prev) => prev + 1);
  };

  const createNewChat = async () => {
    if (!isLoggedIn) {
      alert("Please sign in to create new chats.")
      return;
    }

    const response = await fetcher("create-new-chat", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ chat_type: currTask, model_type: isPrivate }),
    }).catch((e) => {
      console.error(e.error);
    });

    const response_data = await response.json();
    handleChatSelect(response_data.chat_id);

    return response_data.chat_id;
  };

  const testClick = () => {
    fetcher("temp-test", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
    }).catch((e) => {
      console.error(e.error);
    });
  };

  useEffect(() => {
  if (!isLoggedIn) {
    // starting a temporary chat for guest
    setSelectedChatId(0);
    setCurrChatName("Guest Session");
  }
  }, [isLoggedIn]);


  return (
    
    <div className="flex flex-row mt-2">

      
      {isLoggedIn && (
        <div className="w-[20%]">
          <Navbarchatbot
            selectedChatId={selectedChatId}
            onChatSelect={handleChatSelect}
            handleForceUpdate={handleForceUpdate}
            isPrivate={isPrivate}
            setIsPrivate={setIsPrivate}
            setcurrTask={setcurrTask}
            setTicker={setTicker}
            currTask={currTask}
            setConfirmedModelKey={setConfirmedModelKey}
            confirmedModelKey={confirmedModelKey}
            setCurrChatName={setCurrChatName}
            setIsEdit={setIsEdit}
            setShowChatbot={setShowChatbot}
            createNewChat={createNewChat}
            handleChatSelect={handleChatSelect}
            forceUpdate={forceUpdate}
          />
        </div>
      )}
      
       <div className={`${isLoggedIn ? "w-[60%] mx-4" : "w-full"}`}>
        {currTask === 0 && (
          <Chatbot
            chat_type={currTask}
            selectedChatId={selectedChatId}
            handleChatSelect={handleChatSelect}
            handleForceUpdate={handleForceUpdate}
            forceUpdate={forceUpdate}
            isPrivate={isPrivate}
            currChatName={currChatName}
            confirmedModelKey={confirmedModelKey}
            setCurrChatName={setCurrChatName}
            activeMessageIndex={activeMessageIndex}
            setActiveMessageIndex={setActiveMessageIndex}
            setRelevantChunk={setRelevantChunk}
          />
        )}
        {currTask === 1 && (
          <ChatbotEdgar
            chat_type={currTask}
            selectedChatId={selectedChatId}
            createNewChat={createNewChat}
            handleChatSelect={handleChatSelect}
            handleForceUpdate={handleForceUpdate}
            forceUpdate={forceUpdate}
            isPrivate={isPrivate}
            currChatName={currChatName}
            ticker={ticker}
            setTicker={setTicker}
            showChatbot={showChatbot}
            setShowChatbot={setShowChatbot}
            isEdit={isEdit}
            setIsEdit={setIsEdit}
            confirmedModelKey={confirmedModelKey}
            setCurrChatName={setCurrChatName}
            activeMessageIndex={activeMessageIndex}
            setActiveMessageIndex={setActiveMessageIndex}
            setRelevantChunk={setRelevantChunk}
          />
        )}
      </div>

      {isLoggedIn && (
        <div className="w-[20%] mt-2">
          <SidebarChatbot
            selectedChatId={selectedChatId}
            chat_type={currTask}
            createNewChat={createNewChat}
            onChatSelect={handleChatSelect}
            handleForceUpdate={handleForceUpdate}
            forceUpdate={forceUpdate}
            setIsPrivate={setIsPrivate}
            setCurrChatName={setCurrChatName}
            setcurrTask={setcurrTask}
            setTicker={setTicker}
            setShowChatbot={setShowChatbot}
            setIsEdit={setIsEdit}
            setConfirmedModelKey={setConfirmedModelKey}
            relevantChunk={relevantChunk}
            activeMessageIndex={activeMessageIndex}
          />
        </div>
      )}
    </div>
  );
}

export default HomeChatbot;
