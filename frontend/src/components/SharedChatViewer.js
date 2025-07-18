import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import SharedChatbot from "../financeGPT/components/SharedChatbot.js";
import fetcher from "../http/RequestConfig";

const SharedChatViewer = () => {
  const { shareUuid } = useParams();

  const [error, setError] = useState(null);
  const [newChatId, setNewChatId] = useState(null);
  const [currChatName, setCurrChatName] = useState("");
  const [forceUpdate, setForceUpdate] = useState(0);
  const [context, setContext] = useState()

  useEffect(() => {
    const importSharedChat = async () => {
      try {
        setError(null);
        const response = await fetcher(`playbook/${shareUuid}`, {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          credentials: "include",
        });

        //check if the response was successful
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("Shared chat not found");
          } else if (response.status === 500) {
            throw new Error("Server error while importing");
          } else {
            throw new Error("Failed to import shared chat");
          }
        }

        //parse the response

        const data = await response.json();
        console.log("helol", data);
        if (data.chat_info.chat_id) {
          // setNewChatId(data.new_chat_id);
          // setCurrChatName("Shared Chat");
          setContext(data)
          setNewChatId(data.chat_info.chat_id)
        }
      } catch (err) {
        console.error("Error importing the chat:", err);
        setError(err.message);
      }
    };

    if (shareUuid) {
      importSharedChat();
    } else {
      setError("No UUID provided");
    }
  }, [shareUuid]); //rerun if the uuid changes

  const handleForceUpdate = () => {
    setForceUpdate((prev) => prev + 1);
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-red-500 text-xl mb-4">Error: {error}</div>
          <div className="text-gray-400 mb-6">
            This shared chat link may be invalid there was an issue loading it.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full rounded md:mt-8 overflow-auto  justify-center">
      <div className="max-w-6xl h-full mx-auto">
        {/* Chat section  */}
        {newChatId && (
          <SharedChatbot context={context}/>
        )}

        {/* Footer */}
        <div className="mt-6 text-center text-gray-500 text-sm">
          <p>This is a shared conversation.</p>
        </div>
      </div>
    </div>
  );
};

export default SharedChatViewer;
