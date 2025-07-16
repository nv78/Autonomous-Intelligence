import React, { useState, useEffect } from "react";
//import NavLinks from "./NavLinksChatbot"; Changed from using nav to showing all on same page
import Switch from "react-switch";
import fetcher from "../../http/RequestConfig";
import ChatHistory from "./ChatHistory";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faBars,
  faHome,
  faUser,
  faCog,
  faTimes,
} from "@fortawesome/free-solid-svg-icons";

function NavbarChatbot(props) {
  const urlObject = new URL(window.location.origin);
  var hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `dashboard.${hostname}`;
  const navigate = useNavigate();

  return (
    <nav
      className={`md:relative transition-all bg-anoteblack-800 duration-300 ease-in-out ${
        props.menu ? "fixed inset-0" : "absolute"
      } left-0 z-50`}
    >
      <button
        onClick={() => props.handleMenu()}
        className={` md:p-3 p-5   ${props.menu ? "hidden" : ""}`}
      >
        <svg
          width="24px"
          height="24px"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M3.17157 4.17157C2 5.34315 2 7.22876 2 11V13C2 16.7712 2 18.6569 3.17157 19.8284C4.34315 21 6.22876 21 10 21H14C14.0843 21 14.1676 21 14.25 21L14.25 3C14.1676 2.99999 14.0843 3 14 3H10C6.22876 3 4.34315 3 3.17157 4.17157ZM15.75 3.00559L15.75 20.9944C18.3859 20.9668 19.8541 20.8028 20.8284 19.8284C22 18.6569 22 16.7712 22 13V11C22 7.22876 22 5.34315 20.8284 4.17157C19.8541 3.19724 18.3859 3.03321 15.75 3.00559Z"
            fill="#1C274C"
          />
        </svg>
      </button>
      <div
        className={` h-full  transition-all duration-300 ease-in-out ${
          props.menu
            ? "w-52 overflow-auto md:relative top-0 inset-0 left-0 shadow-lg z-50 relative backdrop-blur rounded-r-xl opacity-100"
            : "w-0 h-0 overflow-hidden md:relative top-0 inset-0 left-0 z-50 hidden  opacity-0 pointer-events-none "
        } md:max-w-none`}
      >
        <div className="flex items-center bg-anoteblack-800 w-full  fixed top-0 ">
          <div className="h-10 w-10  bg-center bg-contain bg-[url('../public/logonew.png')] dark:bg-[url('../public/logonew.png')]"></div>
          <div className="text-anoteblack-100 font-bold text-xl">Panacea</div>
          <button
            onClick={() => props.handleMenu()}
            className={`flex md:p-3 p-5 ml-auto cursor-w-resize ${
              !props.menu ? "hidden" : ""
            }`}
          >
            <svg
              width="24px"
              height="24px"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M3.17157 4.17157C2 5.34315 2 7.22876 2 11V13C2 16.7712 2 18.6569 3.17157 19.8284C4.34315 21 6.22876 21 10 21H14C14.0843 21 14.1676 21 14.25 21L14.25 3C14.1676 2.99999 14.0843 3 14 3H10C6.22876 3 4.34315 3 3.17157 4.17157ZM15.75 3.00559L15.75 20.9944C18.3859 20.9668 19.8541 20.8028 20.8284 19.8284C22 18.6569 22 16.7712 22 13V11C22 7.22876 22 5.34315 20.8284 4.17157C19.8541 3.19724 18.3859 3.03321 15.75 3.00559Z"
                fill="#1C274C"
              />
            </svg>
          </button>
        </div>
        <ChatHistory
          onChatSelect={props.onChatSelect}
          setIsPrivate={props.setIsPrivate}
          setTicker={props.setTicker}
          setConfirmedModelKey={props.setConfirmedModelKey}
          setcurrTask={props.setcurrTask}
          setCurrChatName={props.setCurrChatName}
          chats={props.chats}
          setIsEdit={props.setIsEdit}
          setShowChatbot={props.setShowChatbot}
          handleForceUpdate={props.handleForceUpdate}
          createNewChat={props.createNewChat}
          selectedChatId={props.selectedChatId}
          handleChatSelect={props.handleChatSelect}
          forceUpdate={props.forceUpdate}
        />
      </div>
    </nav>
  );
}

export default NavbarChatbot;
