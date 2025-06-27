import React, { useState, useEffect } from "react";
//import NavLinks from "./NavLinksChatbot"; Changed from using nav to showing all on same page
import Switch from "react-switch";
import fetcher from "../../http/RequestConfig";
import ChatHistory from "./ChatHistory";
import { useNavigate } from 'react-router-dom';

function NavbarChatbot(props) {

  const navigate = useNavigate();

  const urlObject = new URL(window.location.origin);
  var hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `dashboard.${hostname}`;

  return (
    <>
      <nav className="flex flex-col h-screen text-white">
        <div className="flex-1 overflow-y-auto">
          <div>
            <ChatHistory
              onChatSelect={props.onChatSelect}
              setIsPrivate={props.setIsPrivate}
              setTicker={props.setTicker}
              setConfirmedModelKey={props.setConfirmedModelKey}
              setcurrTask={props.setcurrTask}
              setCurrChatName={props.setCurrChatName}
              setIsEdit={props.setIsEdit}
              setShowChatbot={props.setShowChatbot}
              handleForceUpdate={props.handleForceUpdate}
              createNewChat={props.createNewChat}
              selectedChatId={props.selectedChatId}
              handleChatSelect={props.handleChatSelect}
              forceUpdate={props.forceUpdate}
            />
          </div>
        </div>
      </nav>
    </>
  );
}

export default NavbarChatbot;
