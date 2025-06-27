import { useNavigate } from "react-router-dom";
import React, { useState, useEffect } from "react";
import fetcher from "../../http/RequestConfig";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPen,
  faTrashCan,
  faCommentDots,
  faPenToSquare,
} from "@fortawesome/free-solid-svg-icons";

import Sources from "./Sources";
import Select from "react-select";
import { SelectStyles } from "../../styles/SelectStyles";
import { Modal } from "flowbite-react";
import { FaDatabase } from "react-icons/fa";
import { connectorOptions } from "../../constants/RouteConstants";

function SidebarChatbot(props) {
  const [docs, setDocs] = useState([]);
  const [showConfirmPopup, setShowConfirmPopup] = useState(false);

  const [showConfirmModelKey, setShowConfirmModelKey] = useState(false);
  const [showErrorKeyMessage, setShowErrorKeyMesage] = useState(false);
  const [showConfirmResetKey, setShowConfirmResetKey] = useState(false);
  const [pendingModel, setPendingModel] = useState(props.isPrivate);
  const [modelKey, setModelKey] = useState("");

  const [showConfirmPopupDoc, setShowConfirmPopupDoc] = useState(false);
  const [docToDeleteName, setDocToDeleteName] = useState(null);
  const [docToDeleteId, setDocToDeleteId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTaskType, setSelectedTaskType] = useState("");

  const urlObject = new URL(window.location.origin);

  var hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `dashboard.${hostname}`;

  useEffect(() => {
    retrieveDocs();
  }, [props.selectedChatId, props.forceUpdate]);

  useEffect(() => {
    console.log("test");
    //changeChatMode(props.isPrivate);
    props.handleForceUpdate();
  }, [props.isPrivate]);

  useEffect(() => {
    setModelKey(props.confirmedModelKey);
    props.handleForceUpdate();
  }, [props.confirmedModelKey]);

  {
    /* Delete doc section */
  }
  const handleDeleteDoc = async (doc_name, doc_id) => {
    setDocToDeleteName(doc_name);
    setDocToDeleteId(doc_id);
    setShowConfirmPopupDoc(true);
  };

  const confirmDeleteDoc = () => {
    console.log("Deleting document:", docToDeleteName);

    deleteDoc(docToDeleteId);
    setShowConfirmPopupDoc(false);
  };

  const cancelDeleteDoc = () => {
    setShowConfirmPopupDoc(false);
  };

  {
    /* Delete chat section */
  }
  const handleModelKey = async () => {
    console.log("is private", props.isPrivate);
    //setChatIdToRename(chat_id);
    if (props.isPrivate === 1) {
      console.log("cow");
      setShowErrorKeyMesage(true);
    } else {
      setShowConfirmModelKey(true);
    }
  };

  const confirmModelKey = () => {
    resetChat();
    props.setConfirmedModelKey(modelKey);
    addModelKeyToDb(modelKey);
    setShowConfirmModelKey(false);
  };

  const cancelModelKey = () => {
    setShowConfirmModelKey(false);
  };

  const cancelErrorKeyMessage = () => {
    setShowErrorKeyMesage(false);
  };

  const handleResetModel = () => {
    setShowConfirmResetKey(true);
  };

  const confirmResetModel = () => {
    console.log("i am here");
    resetChat();
    addModelKeyToDb(null);
    props.setConfirmedModelKey("");
    setShowConfirmResetKey(false);
  };

  const cancelResetModel = () => {
    setShowConfirmResetKey(false);
  };

  const addModelKeyToDb = async (model_key_db) => {
    const response = await fetcher("add-model-key", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: props.selectedChatId,
        model_key: model_key_db,
      }),
    });
    props.handleForceUpdate();
  };

  const resetChat = async () => {
    const response = await fetcher("reset-chat", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ chat_id: props.selectedChatId, delete_docs: false }),
    });
    props.handleForceUpdate();
  };

  const changeChatMode = async (isPrivate) => {
    const response = await fetcher("change-chat-mode", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: props.selectedChatId,
        model_type: isPrivate,
      }), //model_type=1 when private, model_type=0 when public
    })
      .then((response) => {
        console.log("Chat mode changed successfully");

        //props.handleForceUpdate();
      })
      .catch((e) => {
        console.error(e.error);
      });

    //props.handleForceUpdate();
  };


  const retrieveDocs = async () => {
    const response = await fetcher("retrieve-current-docs", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ chat_id: props.selectedChatId }),
    }).catch((e) => {
      console.error(e.error);
    });

    const response_data = await response.json();
    setDocs(response_data.doc_info);
  };

  const deleteDoc = async (doc_id) => {
    const response = await fetcher("delete-doc", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ doc_id: doc_id }),
    }).catch((e) => {
      console.error(e.error);
    });
    props.handleForceUpdate(); //to force it to update
  };

  const deleteConfirmationPopupDoc = showConfirmPopupDoc ? (
    <div
      style={{
        position: "absolute",
        zIndex: 1000,
        color: "black",
        background: "white",
        padding: 20,
        borderRadius: 5,
        boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
      }}
    >
      <p>Are you sure you want to delete {docToDeleteName}?</p>
      <button
        onClick={confirmDeleteDoc}
        className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400 mr-5"
      >
        Yes
      </button>
      <button
        onClick={cancelDeleteDoc}
        className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400"
      >
        No
      </button>
    </div>
  ) : null;
  const handleSwitchChange = () => {
    setShowConfirmPopup(true);
  };

  const confirmSwitchChange = () => {
    props.setIsPrivate((prevState) => 1 - prevState); //toggle true or false
    changeChatMode(props.isPrivate);
    setShowConfirmPopup(false);
  };

  const cancelSwitchChange = () => {
    setShowConfirmPopup(false);
  };

  const confirmPopup = showConfirmPopup ? (
    <div
      style={{
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 1000,
        padding: 20,
        borderRadius: 5,
        boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
        textAlign: "center",
      }}
      className="bg-[#141414]
 text-white"
    >
      <p>
        Warning: You are changing the chat mode. This will reset your current
        chat and delete its history. Are you sure you want to proceed?
      </p>
      <div className="w-full flex justify-between mt-4">
        <button
          onClick={confirmSwitchChange}
          className="w-1/2 mx-2 py-2 bg-gray-700 rounded-lg hover:bg-[#141414]
"
        >
          Yes
        </button>
        <button
          onClick={cancelSwitchChange}
          className="w-1/2 mx-2 py-2 bg-gray-700 rounded-lg hover:bg-[#141414]
"
        >
          No
        </button>
      </div>
    </div>
  ) : null;

  const confirmModelPopup = showConfirmModelKey ? (
    <>
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)", // Semi-transparent black
          zIndex: 999, // Ensure it's below the modal but above everything else
        }}
      ></div>
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
          color: "black",
          backgroundColor: "white",
          padding: 20,
          borderRadius: 5,
          boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
          textAlign: "center",
        }}
      >
        <p>
          Warning: You are changing the OpenAI fine tuning model. This will
          reset your current chat and delete its history. Are you sure you want
          to proceed?
        </p>
        <button
          onClick={confirmModelKey}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400 mr-5"
        >
          Yes
        </button>
        <button
          onClick={cancelModelKey}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400"
        >
          No
        </button>
      </div>
    </>
  ) : null;

  const confirmResetModelPopup = showConfirmResetKey ? (
    <>
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)", // Semi-transparent black
          zIndex: 999, // Ensure it's below the modal but above everything else
        }}
      ></div>
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
          color: "black",
          backgroundColor: "white",
          padding: 20,
          borderRadius: 5,
          boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
          textAlign: "center",
        }}
      >
        <p>
          Warning: You are resetting the OpenAI fine tuning model. This will
          reset your current chat and delete its history. Are you sure you want
          to proceed?
        </p>
        <button
          onClick={confirmResetModel}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400 mr-5"
        >
          Yes
        </button>
        <button
          onClick={cancelResetModel}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400"
        >
          No
        </button>
      </div>
    </>
  ) : null;

  const errorKeyPopup = showErrorKeyMessage ? (
    <>
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)", // Semi-transparent black
          zIndex: 999, // Ensure it's below the modal but above everything else
        }}
      ></div>
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
          color: "black",
          backgroundColor: "white",
          padding: 20,
          borderRadius: 5,
          boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
          textAlign: "center",
        }}
      >
        <p>
          You cannot add your own fine-tuned model key when you are in private
          mode
        </p>
        <button
          onClick={cancelErrorKeyMessage}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400 mr-5"
        >
          Close
        </button>
      </div>
    </>
  ) : null;

  const overlayStyle = {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    zIndex: 999, // Ensure it's below the popup but above everything else
  };

  var modelOptions = [];
  modelOptions.push({ value: 0, label: "OpenAI" }, { value: 1, label: "Claude" });

  const taskoptions = [
    { value: 0, label: 'File Uploader' },
    { value: 1, label: '10-K Edgar' }
  ];

  // Function to handle when an option is selected
  const handleChange = (selectedOption) => {
    props.setcurrTask(selectedOption.value);
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };


const handleDatasetSelect = async (datasetName) => {
  // navigate to the filePath
  handleCloseModal(); // Close the modal after download
};

const filteredOptions = connectorOptions.filter(
  (option) =>
    selectedTaskType === "" || option.taskType === selectedTaskType
);

const onConnectorCardClick = (value) => {
  handleDatasetSelect(value);
};


  // Determine the current selected value based on props.currTask
  const selectedTaskValue = taskoptions.find(option => option.value === props.currTask);

  return (
    <>
    <div className="flex flex-col bg-[#141414]
 rounded-xl text-white">
      {deleteConfirmationPopupDoc}
      <div className="flex flex-col flex-grow">
        <div className="flex-1 bg-[#141414]
 my-2 rounded-xl">
            <ul className="my-4">
              <div className="mx-4 my-2">
                <h2 className="text-[#9C9C9C] uppercase tracking-wide font-semibold text-xs">
                  Agent Selection
                </h2>
              </div>
              <div className="mx-4 my-2">
                <Select
                  className="text-black" // Adjust this class to style the select dropdown as needed
                  value={selectedTaskValue}
                  onChange={handleChange}
                  options={taskoptions}
                  styles={SelectStyles}
                  isSearchable={false}
                />
              </div>
            </ul>
          </div>
          <div className="bg-[#141414] rounded-xl">
            <h2 className="text-[#9C9C9C] uppercase tracking-wide font-semibold text-xs px-4">
              Model Selection
            </h2>
            {showConfirmPopup && <div style={overlayStyle}></div>}
            {confirmPopup}
            {errorKeyPopup}
            {confirmModelPopup}
            {confirmResetModelPopup}
            <div className="rounded py-3 mx-4">
              <div className="flex-1 bg-[#141414] rounded-xl">
              <ul className="">
                <Select
                  name="publicOptions"
                  id="publicOptions"
                  className="bg-[#3A3B41] rounded-lg focus:ring-0 hover:ring-0 hover:border-white border-none text-white cursor-pointer"
                  onChange={handleSwitchChange}
                  options={modelOptions}
                  styles={SelectStyles}
                  isSearchable={false}
                  // value={props.isPrivate === 0 ? "OpenAI" : "Claude"}
                >
                </Select>
                </ul>
              </div>
            </div>
            <div className="">
              {/* <div className="px-4">Your own fine-tuned model key:</div>
              <div className="flex items-center mx-5">
                <input
                  type="text"
                  className="w-full mr-2 mt-2 rounded-xl bg-[#3A3B41] border-none focus:ring-0 focus:border-white text-white placeholder:text-gray-300"
                  placeholder="Model key"
                  onChange={(e) => setModelKey(e.target.value)}
                  value={modelKey}
                />
                {modelKey && (
                  <button
                    onClick={handleModelKey}
                    disabled={!modelKey}
                    style={{
                      marginTop: "4px",
                      padding: "1px",
                      paddingRight: "3px",
                      paddingLeft: "3px",
                      backgroundColor: "green",
                      color: "white",
                      borderRadius: "5px",
                      cursor: "pointer",
                    }}
                  >
                    &#10003;
                  </button>
                )}
              </div> */}
              {/* <div className="px-4">
              <a href="#" className="underline text-sm text-yellow-500" onClick={handleOpenModal}>
            Select Organization
          </a>
          </div> */}
              {props.confirmedModelKey && (
                <button
                  class="bg-gray-700 hover:bg-gray-600 text-white font-bold py-1 px-2 rounded ml-4 mt-3 text-sm"
                  onClick={handleResetModel}
                >
                  Reset model key
                </button>
              )}
            </div>
          </div>
        <div className="flex flex-col px-4 mt-4">
          <h2 className="text-[#FFFFFF] uppercase tracking-wide font-semibold text-s mb-2">
            Uploaded Files
          </h2>
          {/* Map through docs */}
          <div className="bg-black min-h-[30vh] h-[30vh] overflow-y-auto">
          {docs.map((doc) => (
            <div
              key={doc.document_name}
              className="flex items-center justify-between mx-4 my-2 bg-[#141414]
 hover:bg-[#3A3B41] rounded-xl overflow-x-scroll"
            >
              <button
                key={doc.document_name}
                className="flex items-center p-2 my-1 rounded-lg "
              >
                <span className="text-lg">📄</span>{" "}
                {/* Replace with actual icon */}
                <span className="ml-2">{doc.document_name}</span>
              </button>
              <button
                onClick={() => handleDeleteDoc(doc.document_name, doc.id)}
                className="p-2 ml-4 rounded-full "
              >
                <FontAwesomeIcon icon={faTrashCan} />
              </button>
            </div>
          ))}
        </div>
        </div>
      </div>
    </div>
    <div className="mt-4 min-h-[30vh] h-[30vh] overflow-y-auto">
      <Sources
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
        relevantChunk={props.relevantChunk}
        activeMessageIndex={props.activeMessageIndex}
      />
  </div>
  {isModalOpen && (
        <Modal
          size="3xl"
          show={isModalOpen}
          onClose={handleCloseModal}
          theme={{
            root: {
              show: {
                on: "flex bg-[#141414] bg-opacity-50 dark:bg-opacity-80",
              },
            },
            content: {
              base: "relative h-full w-full p-4 md:h-auto",
              inner: "relative rounded-lg shadow bg-gray-950 flex flex-col max-h-[90vh] text-white",
            },
          }}
        >
          <Modal.Header className="border-b border-gray-600 pb-1 text-center">
            <div className="flex justify-center items-center w-full text-center">
              <h2 className="font-bold text-xl text-center text-white ml-[70vh]">Organization Chatbots</h2>
            </div>
          </Modal.Header>
          <Modal.Body className="w-full overflow-y-auto">

            <div className="text-center mb-4 text-sm">
              Supported organization datasets include enterprise or individual fine tuned chatbots.
            </div>

            <div className="flex justify-center space-x-4 mb-6">
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${selectedTaskType === "Classification"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                  }`}
                onClick={() => setSelectedTaskType("Organization")}
              >
                Organization
              </button>
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${selectedTaskType === "Chatbot"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                  }`}
                onClick={() => setSelectedTaskType("Individual")}
              >
                Individual
              </button>
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${selectedTaskType === ""
                  ? "bg-blue-600 text-white"
                  : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                  }`}
                onClick={() => setSelectedTaskType("")}
              >
                All
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {filteredOptions.map((option, index) => (
                <div
                  key={index}
                  className={`p-4 border rounded-lg shadow-md cursor-pointer transition-all duration-300 hover:shadow-xl bg-gray-700 text-gray-200 hover:bg-gray-600
                    }`}
                  onClick={() => onConnectorCardClick(option.value)}
                >
                  <div className="flex flex-col items-center text-center">
                    <FaDatabase className="mb-2" size={20} />
                    <div className="text-sm font-semibold mb-1">{option.label}</div>
                    <div className="text-xs text-gray-300">{option.taskType}</div>
                  </div>
                </div>
              ))}
            </div>

          </Modal.Body>
        </Modal>
 )}
  </>
  );
}

export default SidebarChatbot;
