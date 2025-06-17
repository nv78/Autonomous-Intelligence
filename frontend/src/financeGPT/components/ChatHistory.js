import { React, useState, useEffect } from "react";
import fetcher from "../../http/RequestConfig";
import { Link, useLocation, useParams } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCommentDots,
  faPen,
  faPenToSquare,
  faTrashCan,
} from "@fortawesome/free-solid-svg-icons";
import { Dropdown } from "flowbite-react";
import Popout from "./Popout";

function ChatHistory(props) {
  const [chats, setChats] = useState([]);
  const { id } = useParams()
  const retrieveAllChats = async () => {
    console.log("i am in retrieve chats");
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
    }
  };
  useEffect(() => {
    retrieveAllChats();
  }, [props.chats]);

  //   const [chatIdToDelete, setChatIdToDelete] = useState(null);
  //   const [chatToDelete, setChatToDelete] = useState("");
  //   const [showConfirmPopupChat, setShowConfirmPopupChat] = useState(false);
  //   const [showRenameModal, setShowRenameModal] = useState(false);
  //   const [chatIdToRename, setChatIdToRename] = useState(null);
  //   const [newChatName, setNewChatName] = useState("");

  //   const handleDeleteChat = async (chat_id) => {
  //     const chatToDelete = chats.find(chat => chat.id === chat_id)?.chat_name || 'Chat';
  //     setChatToDelete(chatToDelete);
  //     setChatIdToDelete(chat_id);
  //     setShowConfirmPopupChat(true);
  //   };

  //   const confirmDeleteChat = () => {
  //     deleteChat(chatIdToDelete);
  //     setShowConfirmPopupChat(false);
  //     props.onChatSelect(null);
  //   };

  //   const cancelDeleteChat = () => {
  //     setShowConfirmPopupChat(false);
  //   };

  //   const handleRenameChat = async (chat_id) => {
  //     setChatIdToRename(chat_id);
  //     setShowRenameModal(true);
  //   };

  //   const confirmRenameChat = () => {
  //     console.log("new chat name", newChatName);
  //     renameChat(chatIdToRename, newChatName);
  //     setShowRenameModal(false);
  //   };

  //   const cancelRenameChat = () => {
  //     setShowRenameModal(false);
  //   };

  // useEffect(() => {
  //   console.log("???", props.chats)
  //   setChats(props.chats)
  //   console.log(chats)
  //   // const retrieveAllChats = async () => {
  //   //   console.log("i am in retrieve chats");
  //   //   try {
  //   //     const response = await fetcher("retrieve-all-chats", {
  //   //       method: "POST",
  //   //       headers: {
  //   //         Accept: "application/json",
  //   //         "Content-Type": "application/json",
  //   //       },
  //   //       body: JSON.stringify({ chat_type: props.chat_type }),
  //   //     });

  //   //     const response_data = await response.json();
  //   //     setChats(response_data.chat_info);
  //   //     console.log("retriving data", response_data);
  //   //   } catch (error) {
  //   //     console.error("Error fetching chats:", error);
  //   //   }
  //   // };

  //   // retrieveAllChats();
  // }, [props.chats]);

  //   const deleteChat = async (chat_id) => {
  //     try {
  //       const response = await fetcher("delete-chat", {
  //       method: "POST",
  //       headers: {
  //         Accept: "application/json",
  //         "Content-Type": "application/json",
  //       },
  //       body: JSON.stringify({ chat_id: chat_id }),

  //     });

  //     if (response.ok) {
  //       // If successful, proceed with the force update
  //       props.handleForceUpdate();

  //       try {
  //         const response = await fetcher("find-most-recent-chat", {
  //         method: "POST",
  //         headers: {
  //           Accept: "application/json",
  //           "Content-Type": "application/json",
  //         },
  //         body: JSON.stringify({}),
  //       });

  //         const response_data = await response.json();

  //         props.handleChatSelect(response_data.chat_info.id);
  //         props.setCurrChatName(response_data.chat_info.chat_name)

  //       } catch (e) {
  //         console.error("Error during chat deletion", e);
  //       }

  //     } else {
  //       // Handle server error
  //       console.error("Server responded with non-OK status");
  //     }
  //   } catch (e) {
  //     console.error("Error during chat deletion", e);
  //   }
  // };

  //   const renameChat = async (chat_id, new_name) => {
  //     const response = await fetcher("update-chat-name", {
  //       method: "POST",
  //       headers: {
  //         Accept: "application/json",
  //         "Content-Type": "application/json",
  //       },
  //       body: JSON.stringify({ chat_id: chat_id, chat_name: new_name }),
  //     }).catch((e) => {
  //       console.error(e.error);
  //     });
  //     retrieveAllChats();
  //   };
  //   console.log(chats)
  //   const deleteConfirmationPopupChat = showConfirmPopupChat ? (
  //     <div
  //       style={{
  //         position: "absolute",
  //         padding: 20,
  //         borderRadius: 5,
  //         boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
  //       }}
  //       className="bg-[#141414]
  //  text-white z-50"
  //     >
  //       <p>Are you sure you want to delete {chatToDelete}?</p>
  //       <div className="flex flex-row justify-between mt-2">
  //         <button
  //           onClick={confirmDeleteChat}
  //           className="bg-[#141414]
  //  w-1/2 mx-2 border-white border rounded-xl"
  //         >
  //           Yes
  //         </button>
  //         <button
  //           onClick={cancelDeleteChat}
  //           className="bg-[#141414]
  //  w-1/2 mx-2 border-white border rounded-xl"
  //         >
  //           No
  //         </button>
  //       </div>
  //     </div>
  //   ) : null;

  //   const renameModal = showRenameModal ? (
  //     <>
  //       <div
  //         style={{
  //           position: "fixed",
  //           top: 0,
  //           left: 0,
  //           right: 0,
  //           bottom: 0,
  //           backgroundColor: "rgba(0,0,0,0.4)",
  //           zIndex: 999,
  //         }}
  //       />{" "}
  //       <div
  //         style={{
  //           position: "fixed",
  //           top: "50%",
  //           left: "50%",
  //           transform: "translate(-50%, -50%)",
  //           zIndex: 1000,
  //           padding: 20,
  //           borderRadius: 5,
  //           boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
  //           textAlign: "center",
  //         }}
  //         className="bg-[#141414]
  //  text-white "
  //       >
  //         <div style={{ position: "relative" }}>
  //           <div>
  //             <div className="my-2">Enter new chat name</div>
  //             <input
  //               type="text"
  //               className="rounded-xl bg-[#3A3B41] border-none focus:ring-0 focus:border-white text-white placeholder:text-gray-300"
  //               onChange={(e) => setNewChatName(e.target.value)}
  //               value={newChatName}
  //             />
  //           </div>
  //           <div className="w-full flex justify-between mt-4">
  //             <button
  //               onClick={cancelRenameChat}
  //               className="w-1/2 mx-2 py-2 bg-gray-700 rounded-lg hover:bg-[#141414]
  // "
  //             >
  //               Cancel
  //             </button>
  //             <button
  //               onClick={confirmRenameChat}
  //               className="w-1/2 mx-2 py-2 bg-gray-700 rounded-lg hover:bg-[#141414]
  // "
  //             >
  //               Save
  //             </button>
  //           </div>
  //         </div>
  //       </div>
  //     </>
  //   ) : null;
  
  
  return (
    <div className="px-3 mt-2">
      <h2
        className={`text-base ${chats.length === 0 ? "hidden" : ""} font-bold`}
      >
        Chats
      </h2>
      <ul className="flex-col py-2 justify-around w-full h-full flex overflow-y-auto">
        {[...chats].reverse().map((chat, index) => (
          <li
            key={index}
            className={`group hover:bg-slate-200 mb-1 ${
              chat.id === Number(id) ? "bg-slate-300" : ""
            } flex w-full items-center rounded-md px-2 py-1 text-gray-800`}
          >
            <span className="cursor-pointer w-5/6 truncate max-w-2xl">
              <Link
                onClick={async () => {
                  props.handleChatSelect(chat.id);
                  await retrieveAllChats();
                }}
                className="w-full block"
                to={`/chat/${chat.id}`}
              >
                {chat.chat_name}
              </Link>
            </span>
            <Dropdown
              theme={{
                arrowIcon: "hidden",
              }}
              inline
              label="···"
              placement="left"
              className="ml-auto z-50  group-hover:inline rounded-xl text-white hover:text-gray-300"
            >
              <Dropdown.Item onClick={() => alert(`rename ${chat.chat_name}`)}>
                Rename
              </Dropdown.Item>
              <Dropdown.Item onClick={() => alert("a")}>Delete</Dropdown.Item>
            </Dropdown>
          </li>
        ))}
      </ul>
    </div>
  );
}
// <div className="flex flex-col px-4  rounded-xl py-4  h-[90vh] overflow-y-scroll">
//   {deleteConfirmationPopupChat}
//   {renameModal}
//   <div className="flex flex-row justify-between items-center">
//     <h2 className="text-black uppercase tracking-wide font-semibold text-s mb-2">
//       Chat history
//     </h2>
//     <button
//       className="rounded-full"
//       onClick={() => {
//         props
//           .createNewChat()
//           .then((newChatId) => {
//             console.log("new chat id", newChatId);
//             const chat_name = "Chat " + newChatId.toString();
//             props.setIsPrivate(0);
//             props.setCurrChatName(chat_name);
//             props.setTicker("");
//             props.setShowChatbot(false);
//             props.onChatSelect(newChatId);
//             props.handleForceUpdate();
//             props.setConfirmedModelKey("");
//             retrieveAllChats();
//           })
//           .catch((error) => {
//             console.error("Error creating new chat:", error);
//             // Handle any errors here
//           });
//       }}
//     >
//       <FontAwesomeIcon icon={faPenToSquare} />
//     </button>
//   </div>
//   {[...chats].slice(0, 3).reverse().map((chat) => (
//     <div
//       key={chat.id}
//       onClick={() => {
//         props.onChatSelect(chat.id);
//         props.setIsPrivate(chat.model_type);
//         props.setTicker(chat.ticker);
//         const custom_model_key = chat.custom_model_key || "";
//         console.log("custom model key", custom_model_key);
//         props.setConfirmedModelKey(custom_model_key);
//         if (chat.ticker) {
//           props.setIsEdit(0);
//           props.setShowChatbot(true);
//         }
//         props.setcurrTask(chat.associated_task);
//         props.setCurrChatName(chat.chat_name);
//         console.log("props selected chat id", props.selectedChatId, "and", chat.id)
//       }}
//       className={`flex-shrink-0 flex items-center justify-between hover:bg-[#3A3B41] pl-4 py-2 rounded cursor-pointer text-ellipsis whitespace-nowrap overflow-hidden ${
//         props.selectedChatId === chat.id ? "bg-[#3A3B41] bg-opacity-50" : ""
//       }`}
//     >
//     <div className="flex items-center p-1 text-[#9C9C9C] rounded-lg mr-2 text-ellipsis whitespace-nowrap overflow-hidden">
//         {chat.chat_name}
//       </div>
//       <div>
//         <button
//           onClick={(e) => {
//             e.stopPropagation();
//             handleRenameChat(chat.id);
//           }}
//           className="p-2 rounded-full "
//         >
//           <FontAwesomeIcon icon={faPen} />
//         </button>
//         <button
//           onClick={(e) => {
//             e.stopPropagation();
//             handleDeleteChat(chat.id);
//           }}
//           className="p-2 rounded-full"
//         >
//           <FontAwesomeIcon icon={faTrashCan} />
//         </button>
//       </div>
//     </div>
//   ))}
// </div>
// );
// }

export default ChatHistory;
