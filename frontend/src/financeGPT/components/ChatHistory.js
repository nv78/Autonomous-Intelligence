import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import fetcher from "../../http/RequestConfig";
import { Link, useParams } from "react-router-dom";
import { Dropdown } from "flowbite-react";

function ChatHistory(props) {
  const [chats, setChats] = useState([]);
  const [chatIdToDelete, setChatIdToDelete] = useState(null);
  const [chatToDelete, setChatToDelete] = useState("");
  const [showConfirmPopupChat, setShowConfirmPopupChat] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [chatIdToRename, setChatIdToRename] = useState(null);
  const [newChatName, setNewChatName] = useState("");
  const { id } = useParams();
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

  const handleDeleteChat = async (chat_id) => {
    const chatToDelete =
      chats.find((chat) => chat.id === chat_id)?.chat_name || "Chat";
    setChatToDelete(chatToDelete);
    setChatIdToDelete(chat_id);
    setShowConfirmPopupChat(true);
  };

  const confirmDeleteChat = async () => {
    try {
      const response = await fetcher("delete-chat", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_id: chatIdToDelete }),
      });

      if (response.ok) {
        setShowConfirmPopupChat(false);
        await retrieveAllChats();
        // If deleted chat was selected, clear selection
        if (Number(id) === chatIdToDelete) {
          // Navigate to a different chat or home
          window.location.href = "/chat";
        }
      }
    } catch (e) {
      console.error("Error during chat deletion", e);
    }
  };

  const cancelDeleteChat = () => {
    setShowConfirmPopupChat(false);
    setChatIdToDelete(null);
    setChatToDelete("");
  };

  const handleRenameChat = async (chat_id) => {
    const currentName =
      chats.find((chat) => chat.id === chat_id)?.chat_name || "";
    setNewChatName(currentName);
    setChatIdToRename(chat_id);
    setShowRenameModal(true);
  };

  const confirmRenameChat = async () => {
    if (!newChatName.trim()) return;

    try {
      const response = await fetcher("update-chat-name", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          chat_id: chatIdToRename,
          chat_name: newChatName,
        }),
      });

      if (response.ok) {
        setShowRenameModal(false);
        await retrieveAllChats();
      }
    } catch (e) {
      console.error("Error during chat rename", e);
    }
  };

  const cancelRenameChat = () => {
    setShowRenameModal(false);
    setChatIdToRename(null);
    setNewChatName("");
  };

  return (
    <>
      {/* Delete Confirmation Modal - Rendered outside parent */}
      {showConfirmPopupChat &&
        createPortal(
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[9999]">
            <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 shadow-2xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                Delete Chat
              </h3>
              <p className="text-gray-600 mb-8 text-lg">
                Are you sure you want to delete "
                <span className="font-semibold">{chatToDelete}</span>"? This
                action cannot be undone.
              </p>
              <div className="flex space-x-4">
                <button
                  onClick={cancelDeleteChat}
                  className="flex-1 px-6 py-3 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDeleteChat}
                  className="flex-1 px-6 py-3 text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors font-medium"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      {/* Rename Modal - Rendered outside parent */}
      {showRenameModal &&
        createPortal(
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[9999]">
            <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4 shadow-2xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">
                Rename Chat
              </h3>
              <input
                type="text"
                value={newChatName}
                onChange={(e) => setNewChatName(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 mb-8 text-lg"
                placeholder="Enter new chat name"
                autoFocus
                onKeyPress={(e) => {
                  if (e.key === "Enter") {
                    confirmRenameChat();
                  }
                }}
              />
              <div className="flex space-x-4">
                <button
                  onClick={cancelRenameChat}
                  className="flex-1 px-6 py-3 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmRenameChat}
                  className="flex-1 px-6 py-3 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors font-medium"
                  disabled={!newChatName.trim()}
                >
                  Save
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}

      <div className="px-3 mt-12">
        <h2
          className={`text-xl text-anoteblack-100 ${
            chats.length === 0 ? "hidden" : ""
          } font-bold`}
        >
          Chat History
        </h2>
        <ul className="flex-col py-2 justify-around w-full h-full flex overflow-y-auto">
          {[...chats].reverse().map((chat, index) => (
            <li
              key={index}
              className={`group hover:bg-softBlue/80  mb-1 ${
                chat.id === Number(id) ? "bg-softBlue/30" : ""
              } flex w-full items-center rounded-md px-2 py-1 text-gray-800`}
            >
              <span className="cursor-pointer w-5/6 truncate max-w-2xl">
                <Link
                  onClick={async () => {
                    props.handleChatSelect(chat.id);
                    await retrieveAllChats();
                  }}
                  className="w-full text-turquoise-200 block"
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
                <Dropdown.Item onClick={() => handleRenameChat(chat.id)}>
                  Rename
                </Dropdown.Item>
                <Dropdown.Item onClick={() => handleDeleteChat(chat.id)}>
                  Delete
                </Dropdown.Item>
              </Dropdown>
            </li>
          ))}
        </ul>
      </div>
    </>
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
