import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  useAPIKeys,
  generateAPIKey,
  deleteAPIKey,
  getAPIKeys,
} from "../../redux/UserSlice";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faTrash,
  faCopy,
  faArrowLeft,
} from "@fortawesome/free-solid-svg-icons";
import copy from "copy-to-clipboard";
import "../../styles/APIKeyDashboard.css";
import { Button, Table } from "flowbite-react";
import { useNavigation, useLocation } from "react-router-dom";

export function APISKeyDashboard() {
  const dispatch = useDispatch();
  const apiKeys = useAPIKeys();

  const handleGenerateAPIKeys = () => {
    dispatch(generateAPIKey());
  };

  const handleDeleteAPIKey = (apiKeyId) => {
    dispatch(deleteAPIKey(apiKeyId));
  };

  const handleCopyAPIKey = (apiKey) => {
    copy(apiKey);
    // Handle the success or error notification for copying if required
  };

  // useEffect(() => {
  //   dispatch(getAPIKeys());
  // }, [dispatch]);

  // unused func 
  const lastUsedDisplay = (lastUsed) => {
    return lastUsed ? lastUsed : "Never";
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-card w-1/2 bg-[#141414]
 border-2">
        <div className="relative">
          <Button
            color="gray"
            outline
            className="absolute left-10"
            onClick={() => window.history.back()}
          >
            <div className="flex items-center">
              <FontAwesomeIcon className="w-4 h-4 mr-1" icon={faArrowLeft} />
              <span className="font-semibold">Back</span>
            </div>
          </Button>
          <h1 className="dashboard-title font-bold">API Key Dashboard</h1>
        </div>
        <div className="button-container">
        </div>
          <div onClick={handleGenerateAPIKeys} className="button-container">
      
            Create New API Key
         
        </div>
        <div className="api-keys-container overflow-auto max-h-96">
          {apiKeys.length > 0 && (
            <Table className="api-keys-table" hoverable>
              <Table.Head>
                {/* Update these headers as required. I've used the headers you commented out as a reference */}
                {/* <Table.HeadCell>Key Name</Table.HeadCell> */}
                <Table.HeadCell>API Key</Table.HeadCell>
                <Table.HeadCell>Created</Table.HeadCell>
                {/* <Table.HeadCell>Last Used</Table.HeadCell> */}
                <Table.HeadCell>
                  Actions
                </Table.HeadCell>
              </Table.Head>
              <Table.Body className="divide-y">
                {apiKeys.map((apiKey) => (
                  <Table.Row
                    key={apiKey.id}
                    className="bg-white dark:border-gray-700 dark:bg-[#141414]
"
                  >
                    {/* <Table.Cell className="whitespace-nowrap font-medium text-gray-900 dark:text-white">{apiKey.key_name}</Table.Cell> */}
                    <Table.Cell key={apiKey.id} className="whitespace-nowrap font-medium dark:text-white">
                      {apiKey.key}
                    </Table.Cell>
                    <Table.Cell>{apiKey.created}</Table.Cell>
                    {/* <Table.Cell>{lastUsedDisplay(apiKey.last_used)}</Table.Cell> */}
                    <Table.Cell>
                      <button
                        className="font-medium text-[#40C6FF] hover:underline dark:text-[#40C6FF] trashButton"
                        onClick={() => handleDeleteAPIKey(apiKey.id)}
                      >
                        <FontAwesomeIcon icon={faTrash} />
                      </button>
                      <button
                        className="copy-key-button ml-3"
                        onClick={() => handleCopyAPIKey(apiKey.key)}
                      >
                        <FontAwesomeIcon icon={faCopy} />
                      </button>
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table>
          )}
          {apiKeys.length === 0 && (
            <p className="text-white">No API keys found.</p>
          )}
          {/* <a
            className="border-cyan-600 text-cyan-600 hover:bg-cyan-600 hover:text-white px-4 py-2 rounded transition duration-300"
            href={"https://docs.anote.ai/api/anoteapi.html"}
          >
            Docs
          </a> */}
        </div>
      </div>
    </div>
  );
}
