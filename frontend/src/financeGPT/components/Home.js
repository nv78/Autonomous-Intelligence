import React, { Component, useState, useEffect, useRef } from "react";
import Navbarchatbot from "./NavbarChatbot";
import Chatbot from "./Chatbot";
import "../styles/Chatbot.css";
import SidebarChatbot from "./SidebarChatbot";
import fetcher from "../../http/RequestConfig";
import ChatbotEdgar from "./chatbot_subcomponents/ChatbotEdgar";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import Popout from "./Popout";


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
  const [relevantChunk, setRelevantChunk] = useState("");
  const [menu, setMenu] = useState(false);
  const [chats, setChats] = useState([]);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const { id } = useParams();
  const location = useLocation();

  // Upload-related state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [triggerUpload, setTriggerUpload] = useState(false);
  const sidebarRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleMenu = () => {
    setMenu((prev) => !prev);
  };
  const [confirmedModelKey, setConfirmedModelKey] = useState("");

  const handleChatSelect = (chatId) => {
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

  // Handle upload trigger from chatbot - direct approach
  const handleUploadClick = (chatId) => {
    console.log("handleUploadClick called with chatId:", chatId);
    // If a chatId is provided, ensure selectedChatId is set
    if (chatId && chatId !== selectedChatId) {
      setSelectedChatId(chatId);
    }
    
    // Try direct file input first
    if (fileInputRef.current) {
      console.log("Triggering file input dialog");
      fileInputRef.current.click();
      return;
    }
    
    // Fallback to sidebar approach
    if (sidebarRef.current && sidebarRef.current.openFileDialog) {
      console.log("Using sidebar openFileDialog");
      sidebarRef.current.openFileDialog();
    } else {
      console.log("Using trigger upload fallback");
      // Fallback to trigger approach
      setTriggerUpload(true);
    }
  };

  // Reset upload trigger (called by sidebar after handling)
  const resetUploadTrigger = () => {
    setTriggerUpload(false);
  };

  // Handle file upload
  const handleFileUpload = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    if (!selectedChatId) {
      console.error("No chat selected for file upload");
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append("files[]", files[i]);
      }
      formData.append("chat_id", selectedChatId);

      console.log("Uploading files for chat:", selectedChatId);
      
      const response = await fetcher("ingest-pdf", {
        method: "POST",
        body: formData,
      });

      const responseData = await response.json();
      console.log("Upload response:", responseData);
      
      // Force update to refresh documents list
      handleForceUpdate();
      
    } catch (error) {
      console.error("File upload error:", error);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      // Clear the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  useEffect(() => {
    const retrieveAllChats = async () => {
      console.log("i am in retrieve chats");
      setLoading(true);
      try {
        const response = await fetcher("retrieve-all-chats", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ chat_type: 0 }),
        });

        const response_data = await response.json();
        setChats(response_data.chat_info);
        console.log("retriving data", response_data);
      } catch (error) {
        console.error("Error fetching chats:", error);
      } finally {
        setLoading(false);
      }
    };
    retrieveAllChats();
  }, [forceUpdate]);

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
            isLoggedIn={isLoggedIn}
            chat_type={currTask}
            selectedChatId={selectedChatId}
            handleChatSelect={handleChatSelect}
            handleMenu={handleMenu}
            chats={chats}
            createNewChat={createNewChat}
            menu={menu}
            handleForceUpdate={handleForceUpdate}
            forceUpdate={forceUpdate}
            isPrivate={isPrivate}
            currChatName={currChatName}
            confirmedModelKey={confirmedModelKey}
            setCurrChatName={setCurrChatName}
            activeMessageIndex={activeMessageIndex}
            setActiveMessageIndex={setActiveMessageIndex}
            setRelevantChunk={setRelevantChunk}
            isUploading={isUploading}
            uploadProgress={uploadProgress}
            onUploadClick={handleUploadClick}
          />
        )}
      </div>
      {isLoggedIn && (
        <div className="w-[20%] hidden lg:block">
          <SidebarChatbot

            ref={sidebarRef}
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
            triggerUpload={triggerUpload}
            resetUploadTrigger={resetUploadTrigger}
            setIsUploading={setIsUploading}
            setUploadProgress={setUploadProgress}
            onChatReady={(chatId) => navigate(`/chat/${chatId}`)}
          /> */}
        </div>
      )}
        {/* {currTask === 1 && (
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
        )} */}
      </div>
      
      {/* Hidden file input for direct upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".pdf,.doc,.docx,.txt,.csv"
        multiple
        style={{ display: 'none' }}
      />

    </div>
  );
}


export default HomeChatbot;
