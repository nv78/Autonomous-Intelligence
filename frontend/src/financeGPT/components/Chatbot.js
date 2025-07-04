import React, { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDownload, faPaperPlane } from "@fortawesome/free-solid-svg-icons";
import "../styles/Chatbot.css";
import fetcher from "../../http/RequestConfig";
import { useLocation, useNavigate, useParams } from "react-router-dom";

const Chatbot = (props) => {
  const [message, setMessage] = useState("");
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { id } = useParams();
  const location = useLocation();
  const [isFirstMessageSent, setIsFirstMessageSent] = useState(false);
  const [messages, setMessages] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const fileInputRef = useRef(null);
  const [fileModalOpen, setFileModalOpen] = useState(false);
  const [currentFile, setCurrentFile] = useState(null);
  const [fileContent, setFileContent] = useState(null);
  const [loadingFile, setLoadingFile] = useState(false);
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [docsViewerOpen, setDocsViewerOpen] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [availableAgents, setAvailableAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);
  const [agentDropdownPosition, setAgentDropdownPosition] = useState({ top: 0, left: 0, width: 0 });
  const [loadingAgents, setLoadingAgents] = useState(false);

  const agentButtonRef = useRef(null);

  // Load existing chat messages
  const handleLoadChat = useCallback(async () => {
    if (!id) return;

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

      // If no messages, this could be a new chat or a chat still processing
      if (!response_data.messages?.length) {
        // Check for pending message from navigation state or localStorage
        const pendingMessage = location.state?.message || localStorage.getItem(`pending-message-${id}`);
        
        if (pendingMessage) {
          const userMessage = {
            id: "user-content",
            chat_id: id,
            role: "user",
            content: pendingMessage,
          };
          const thinkingMessage = {
            id: `temp-thinking-${Date.now()}`,
            chat_id: id,
            role: "assistant",
            content: "Thinking...",
          };
          setMessages([userMessage, thinkingMessage]);
          setIsFirstMessageSent(false);
          
          // Store in localStorage for refresh persistence
          if (location.state?.message) {
            localStorage.setItem(`pending-message-${id}`, location.state.message);
          }
        } else {
          // No messages and no pending message - empty chat
          setMessages([]);
          setIsFirstMessageSent(false);
        }
        return;
      }

      // We have messages, so clear any pending message
      localStorage.removeItem(`pending-message-${id}`);

      const transformedMessages = response_data.messages.map((item) => ({
        id: item.id,
        chat_id: id,
        content: item.message_text,
        role: item.sent_from_user === 1 ? "user" : "assistant",
        relevant_chunks: item.relevant_chunks,
      }));
      console.log(transformedMessages);
      setMessages(transformedMessages);
      setIsFirstMessageSent(transformedMessages.length > 0);
    } catch (error) {
      console.error("Error loading chat:", error);
    }
  }, [id, location.state?.message]);

  // Load uploaded documents for the current chat
  const handleLoadDocs = useCallback(async () => {
    if (!id) return;

    setLoadingDocs(true);
    try {
      const response = await fetcher("retrieve-current-docs", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          chat_id: id,
        }),
      });

      const response_data = await response.json();
      if (response_data.doc_info) {
        const previousCount = uploadedDocs.length;
        console.log(response_data.doc_info);
        setUploadedDocs(response_data.doc_info);

        // Auto-open documents viewer when first document is uploaded
        if (previousCount === 0 && response_data.doc_info.length > 0) {
          setDocsViewerOpen(true);
        }
      }
    } catch (error) {
      console.error("Error loading documents:", error);
      setUploadedDocs([]);
    }
    setLoadingDocs(false);
  }, [id, uploadedDocs.length]);

  // Load available agents for the user
  const handleLoadAgents = useCallback(async () => {
    setLoadingAgents(true);
    try {
      const response = await fetcher("get-user-agents", {
        method: "GET",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
      });

      if (response.ok) {
        const response_data = await response.json();
        setAvailableAgents(response_data.agents || []);
        
        // Set default agent if none selected and agents available
        if (!selectedAgent && response_data.agents?.length > 0) {
          setSelectedAgent(response_data.agents[0]);
        }
      } else {
        console.error("Failed to load agents");
        setAvailableAgents([]);
      }
    } catch (error) {
      console.error("Error loading agents:", error);
      setAvailableAgents([]);
    }
    setLoadingAgents(false);
  }, [selectedAgent]);

  // Load chat when component mounts or ID changes
  useEffect(() => {
    if (id) {
      handleLoadChat();
      handleLoadDocs();
      handleLoadAgents();
    } else {
      setMessages([]);
      setIsFirstMessageSent(false);
      setUploadedDocs([]);
    }
  }, [id, handleLoadChat, handleLoadDocs, handleLoadAgents]);

  // Close agent dropdown when clicking outside or scrolling
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (agentDropdownOpen && 
          !agentButtonRef.current?.contains(event.target) &&
          !event.target.closest('[data-agent-dropdown]')) {
        setAgentDropdownOpen(false);
      }
    };

    const handleScroll = () => {
      if (agentDropdownOpen) {
        setAgentDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('scroll', handleScroll, true);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [agentDropdownOpen]);

  // Main message sending function
  const handleSendMessage = async (event) => {
    event.preventDefault();

    // Only prevent submission if there's no message text (files are handled separately)
    if (!message || message.trim() === "") return;

    const currentPath = window.location.pathname;
    const currentMessage = message;
    const currentFiles = [...selectedFiles]; // Copy files before clearing

    // Clear input and files immediately
    setMessage("");
    setSelectedFiles([]);

    // If we're on root path or base chat path, create new chat first
    let targetChatId = id;
    if (currentPath === "/" || currentPath === "/chat" || !id) {
      try {
        // Create new chat first
        targetChatId = await props.createNewChat();
        // Navigate to new chat URL
        navigate(`/chat/${targetChatId}`, { state: { message: currentMessage }});
      } catch (error) {
        console.error("Error creating new chat:", error);
        // Restore message and files on failure
        setMessage(currentMessage);
        setSelectedFiles(currentFiles);
        return;
      }
    }

    // Upload files with valid chat ID if any (files will be stored in documents for context)
    if (currentFiles.length > 0) {
      try {
        await handleFileUpload(currentFiles, targetChatId);
        // Files are now uploaded and available for chat context
      } catch (error) {
        console.error("File upload failed:", error);
        // Restore message and files on failure
        setMessage(currentMessage);
        setSelectedFiles(currentFiles);
        return;
      }
    }

    // Add user message and thinking placeholder immediately (no file attachments in message)
    const thinkingId = `temp-thinking-${Date.now()}`;
    const newMessages = [
      {
        id: `temp-user-${Date.now()}`,
        chat_id: targetChatId,
        role: "user",
        content: currentMessage,
        agent: selectedAgent, // Include selected agent info
        // No files attached to message - they're stored as documents for context
      },
      {
        id: thinkingId,
        chat_id: targetChatId,
        role: "assistant",
        content: "Thinking...",
        agent: selectedAgent, // Include selected agent info for response
      },
    ];

    // Store the message in localStorage for refresh persistence
    localStorage.setItem(`pending-message-${targetChatId}`, currentMessage);

    if (currentPath === "/" || currentPath === "/chat" || !id) {
      // New chat - set messages directly
      setMessages(newMessages);
    } else {
      // Existing chat - append to existing messages
      setMessages((prev) => [...prev, ...newMessages]);
    }

    // Send to API (files are already uploaded as documents)
    await sendToAPI(
      currentMessage,
      targetChatId,
      currentFiles.length > 0,
      thinkingId
    );
  };

  // Send message to API and handle response
  const sendToAPI = async (
    messageText,
    chatId,
    hadFiles = false,
    thinkingId = null
  ) => {
    try {
      const response = await fetcher("process-message-pdf", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: messageText,
          chat_id: Number(chatId),
          model_type: props.isPrivate,
          model_key: props.confirmedModelKey,
          agent_id: selectedAgent?.id || null,
          agent_name: selectedAgent?.name || null,
          // Files are handled as uploaded documents, not attached to messages
        }),
      });

      const response_data = await response.json();
      const answer = response_data.answer;

      // Replace the specific "Thinking..." message with actual response
      setMessages((messages) => {
        // Find the specific thinking message by its ID
        const thinkingIndex = messages.findIndex(
          (msg) => msg.id === thinkingId
        );

        if (thinkingIndex !== -1) {
          // Replace the found "Thinking..." message
          const updatedMessages = [...messages];
          updatedMessages[thinkingIndex] = {
            ...updatedMessages[thinkingIndex],
            id: response_data.id,
            content: answer,
            agent: selectedAgent, // Preserve agent info
          };
          return updatedMessages;
        }

        // Fallback: find first "Thinking..." message for this chat if thinkingId doesn't match
        const fallbackIndex = messages.findIndex(
          (msg) =>
            msg.content === "Thinking..." && msg.chat_id === Number(chatId)
        );

        if (fallbackIndex !== -1) {
          const updatedMessages = [...messages];
          updatedMessages[fallbackIndex] = {
            ...updatedMessages[fallbackIndex],
            id: response_data.id,
            content: answer,
            agent: selectedAgent, // Preserve agent info
          };
          return updatedMessages;
        }

        // If no "Thinking..." message found, just add the new response
        return [
          ...messages,
          {
            id: response_data.id,
            chat_id: Number(chatId),
            role: "assistant",
            content: answer,
            agent: selectedAgent, // Include agent info
          },
        ];
      });

      // Update chat name for first message
      if (!isFirstMessageSent) {
        props.setCurrChatName?.(messageText);
        setIsFirstMessageSent(true);
        props.handleForceUpdate?.();
      }

      // Clear any pending message from localStorage since we got a response
      localStorage.removeItem(`pending-message-${chatId}`);

      // Refresh documents list if files were uploaded
      if (hadFiles) {
        // Add a slight delay to ensure backend processing is complete
        setTimeout(() => {
          handleLoadDocs();
        }, 1000);
      }
    } catch (error) {
      console.error("Error sending message:", error);

      // Replace the specific "Thinking..." message with error message
      setMessages((messages) => {
        // Find the specific thinking message by its ID
        const thinkingIndex = messages.findIndex(
          (msg) => msg.id === thinkingId
        );

        if (thinkingIndex !== -1) {
          // Replace the found "Thinking..." message
          const updatedMessages = [...messages];
          updatedMessages[thinkingIndex] = {
            ...updatedMessages[thinkingIndex],
            content:
              "Sorry, I couldn't connect to the server. Please check your connection and try again.",
          };
          return updatedMessages;
        }

        // Fallback: find first "Thinking..." message for this chat if thinkingId doesn't match
        const fallbackIndex = messages.findIndex(
          (msg) =>
            msg.content === "Thinking..." && msg.chat_id === Number(chatId)
        );

        if (fallbackIndex !== -1) {
          const updatedMessages = [...messages];
          updatedMessages[fallbackIndex] = {
            ...updatedMessages[fallbackIndex],
            content:
              "Sorry, I couldn't connect to the server. Please check your connection and try again.",
          };
          return updatedMessages;
        }

        // If no "Thinking..." message found, add a new error message
        return [
          ...messages,
          {
            id: `error-${Date.now()}`,
            chat_id: Number(chatId),
            role: "assistant",
            content:
              "Sorry, I couldn't connect to the server. Please check your connection and try again.",
          },
        ];
      });

      // Don't clear localStorage on error - keep the pending message for potential retry
    }
  };

  // Handle Enter key press
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  // File upload handlers
  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files);
    // Add new files to existing selection instead of replacing
    setSelectedFiles((prev) => [...prev, ...files]);
    // Clear the input value so the same file can be selected again if needed
    event.target.value = "";
  };

  // Reset file viewer when no files are selected
  React.useEffect(() => {
    if (selectedFiles.length === 0) {
      // Files cleared, no additional state to reset
    }
  }, [selectedFiles.length]);

  const handleFileUpload = async (
    filesToUpload = selectedFiles,
    chatId = id
  ) => {
    if (filesToUpload.length === 0) return null;

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      // Use the same format as the backend expects: files[]
      filesToUpload.forEach((file) => {
        formData.append("files[]", file);
      });
      formData.append("chat_id", chatId);

      // Use XMLHttpRequest for real progress tracking with correct endpoint
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded * 100) / event.total);
            setUploadProgress(progress);
          }
        };

        xhr.onload = () => {
          if (xhr.status === 200) {
            try {
              // We don't need to parse the result since we're not using it
              setIsUploading(false);
              setUploadProgress(100);

              // Clear progress after a short delay
              setTimeout(() => {
                setUploadProgress(0);
              }, 1000);

              // Return file info for display in chat
              const uploadedFiles = filesToUpload.map((file, index) => ({
                name: file.name,
                size: file.size,
                type: file.type,
                id: `uploaded-${Date.now()}-${index}`,
              }));

              // Auto-refresh documents list after successful upload
              setTimeout(() => {
                if (id) {
                  handleLoadDocs();
                }
              }, 500);

              resolve(uploadedFiles);
            } catch (e) {
              setIsUploading(false);
              setUploadProgress(0);
              reject(new Error("Invalid response format"));
            }
          } else {
            setIsUploading(false);
            setUploadProgress(0);
            reject(new Error(`Upload failed with status: ${xhr.status}`));
          }
        };

        xhr.onerror = () => {
          setIsUploading(false);
          setUploadProgress(0);
          reject(new Error("Network error during upload"));
        };

        // Use the existing ingest-pdf endpoint
        xhr.open(
          "POST",
          `${process.env.REACT_APP_BACK_END_HOST || ""}/ingest-pdf`
        );

        // Add authentication headers using the same pattern as fetcher
        const accessToken = localStorage.getItem("accessToken");
        const sessionToken = localStorage.getItem("sessionToken");

        if (accessToken) {
          xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);
        } else if (sessionToken) {
          xhr.setRequestHeader("Authorization", `Bearer ${sessionToken}`);
        }

        xhr.send(formData);
      });
    } catch (error) {
      console.error("File upload error:", error);
      setIsUploading(false);
      setUploadProgress(0);
      throw error; // Re-throw to handle in calling function
    }
  };

  const removeFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  // Handle deleting an uploaded document
  const handleDeleteDoc = async (docId) => {
    console.log("here");
    try {
      await fetcher("delete-doc", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          doc_id: docId,
        }),
      });

      setUploadedDocs((prev) => prev.filter((doc) => doc.doc_id !== docId));

      // Automatically refresh the documents list after successful deletion
      handleLoadDocs();
    } catch (error) {
      console.error("Error deleting document:", error);
      // Still try to refresh in case the deletion actually worked
      handleLoadDocs();
    }
  };

  // Handle viewing uploaded documents
  const handleViewUploadedDoc = async (doc) => {
    try {
      setCurrentFile(doc);
      setFileModalOpen(true);
      setLoadingFile(true);
      setFileContent(null);

      // Try to fetch actual document content
      try {
        const response = await fetcher("get-doc-content", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            doc_id: doc.doc_id,
          }),
        });

        if (response.ok) {
          const docData = await response.json();
          setFileContent({
            type: "document-content",
            name: docData.document_name,
            content: docData.document_text,
            uploadDate: doc.upload_date,
            docId: doc.doc_id,
            isUploaded: true,
          });
        } else {
          // Fallback to document info if content fetch fails
          setFileContent({
            type: "document-info",
            name: doc.doc_name,
            uploadDate: doc.upload_date,
            docId: doc.doc_id,
            isUploaded: true,
            error: "Could not load document content",
          });
        }
      } catch (contentError) {
        console.error("Error fetching document content:", contentError);
        // Fallback to document info
        setFileContent({
          type: "document-info",
          name: doc.doc_name,
          uploadDate: doc.upload_date,
          docId: doc.doc_id,
          isUploaded: true,
          error: "Could not load document content",
        });
      }

      setLoadingFile(false);
    } catch (error) {
      console.error("Error viewing uploaded document:", error);
      setLoadingFile(false);
      setFileContent({ error: "Error loading document" });
    }
  };

  const handleFileClick = async (file) => {
    try {
      setCurrentFile(file);
      setFileModalOpen(true);
      setLoadingFile(true);
      setFileContent(null);

      // File URL resolution strategies
      const urlStrategies = [
        { key: "url", getValue: (f) => f.url },
        { key: "download_url", getValue: (f) => f.download_url },
        {
          key: "path",
          getValue: (f) =>
            f.path
              ? `${process.env.REACT_APP_BACK_END_HOST || ""}/files/${f.path}`
              : null,
        },
        {
          key: "id",
          getValue: (f) =>
            f.id
              ? `${process.env.REACT_APP_BACK_END_HOST || ""}/download-file/${
                  f.id
                }`
              : null,
        },
        {
          key: "name",
          getValue: (f) => {
            const fileName = f.name || f.filename;
            return fileName
              ? `${
                  process.env.REACT_APP_BACK_END_HOST || ""
                }/download-file?name=${encodeURIComponent(fileName)}`
              : null;
          },
        },
      ];

      const fileUrl = urlStrategies
        .find((strategy) => strategy.getValue(file))
        ?.getValue(file);

      if (!fileUrl) {
        setLoadingFile(false);
        setFileContent({ error: "File URL not available" });
        return;
      }

      // File type handlers configuration
      const fileName = file.name || file.filename || "";
      const fileExtension = fileName.split(".").pop()?.toLowerCase();

      const fileTypeHandlers = {
        image: {
          extensions: ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
          handler: async (url, name) => ({
            type: "image",
            url,
            name,
          }),
        },
        pdf: {
          extensions: ["pdf"],
          handler: async (url, name) => ({
            type: "pdf",
            url,
            name,
          }),
        },
        text: {
          extensions: ["txt", "md", "csv"],
          handler: async (url, name) => {
            try {
              const response = await fetch(url);
              if (response.ok) {
                const text = await response.text();
                return { type: "text", content: text, name };
              } else {
                return { type: "download", url, name };
              }
            } catch (error) {
              return { type: "download", url, name };
            }
          },
        },
        download: {
          extensions: [], // Default handler for all other types
          handler: async (url, name) => ({
            type: "download",
            url,
            name,
          }),
        },
      };

      // Find appropriate handler
      const handlerEntry = Object.entries(fileTypeHandlers).find(
        ([_, config]) => config.extensions.includes(fileExtension)
      );

      const handler = handlerEntry
        ? handlerEntry[1]
        : fileTypeHandlers.download;
      const content = await handler.handler(fileUrl, fileName);

      setFileContent(content);
      setLoadingFile(false);
    } catch (error) {
      console.error("Error opening file:", error);
      setLoadingFile(false);
      setFileContent({ error: "Error loading file" });
    }
  };

  const handleLocalFileClick = (file) => {
    try {
      setCurrentFile(file);
      setFileModalOpen(true);
      setLoadingFile(true);
      setFileContent(null);

      // For local files, we need to create a blob URL
      const fileUrl = URL.createObjectURL(file);
      const fileName = file.name || "";
      const fileExtension = fileName.split(".").pop()?.toLowerCase();

      setTimeout(() => {
        if (
          ["jpg", "jpeg", "png", "gif", "bmp", "webp"].includes(fileExtension)
        ) {
          // Image file
          setFileContent({
            type: "image",
            url: fileUrl,
            name: fileName,
            isLocal: true,
          });
          setLoadingFile(false);
        } else if (fileExtension === "pdf") {
          // PDF file
          setFileContent({
            type: "pdf",
            url: fileUrl,
            name: fileName,
            isLocal: true,
          });
          setLoadingFile(false);
        } else if (["txt", "md", "csv"].includes(fileExtension)) {
          // Text file - read content
          const reader = new FileReader();
          reader.onload = (e) => {
            setFileContent({
              type: "text",
              content: e.target.result,
              name: fileName,
              isLocal: true,
            });
            setLoadingFile(false);
          };
          reader.onerror = () => {
            setFileContent({
              type: "download",
              url: fileUrl,
              name: fileName,
              isLocal: true,
            });
            setLoadingFile(false);
          };
          reader.readAsText(file);
        } else {
          // Other file types - show info but can't preview
          setFileContent({
            type: "download",
            url: fileUrl,
            name: fileName,
            isLocal: true,
            size: file.size,
            lastModified: file.lastModified,
          });
          setLoadingFile(false);
        }
      }, 100); // Small delay to show loading state
    } catch (error) {
      console.error("Error opening local file:", error);
      setLoadingFile(false);
      setFileContent({ error: "Error loading file" });
    }
  };

  // Clean up blob URLs when modal closes
  const closeModal = () => {
    if (fileContent?.isLocal && fileContent?.url) {
      URL.revokeObjectURL(fileContent.url);
    }
    setFileModalOpen(false);
    setCurrentFile(null);
    setFileContent(null);
  };

  return (
    <div
      className={`md:pt-16 py-2 px-5 h-full w-full flex flex-col  ${
        props.menu ? "md:pl-7 md:blur-none blur" : ""
      }`}
    >
      {/* Chat title for mobile */}
      <div className="w-full bg-transparent md:py-0 py-4 md:shadow-none shadow-lg border-b-2 items-center flex justify-center  flex-shrink-0">
        <span className="md:hidden rounded py-2 px-4">
          {props.currChatName}
        </span>
      </div>
      {/* Messages container */}
      <div
        ref={(ref) =>
          ref && ref.scrollTo({ top: ref.scrollHeight, behavior: "smooth" })
        }
        className={`flex-1 bg-gray-100  rounded overflow-auto ${
          messages.length > 0 ? "block" : "hidden"
        } my-4`}
      >
        <div className="py-3 flex-col mt-4 px-4 flex gap-3">
          {messages.map((msg, index) => (
            <div
              key={`${msg.chat_id}-${msg.id || index}`}
              className={`flex items-center gap-4 ${
                msg.role === "user" ? "justify-end" : ""
              }`}
            >
              <div
                className={`rounded-lg p-3 max-w-[80%] ${
                  msg.role === "user"
                    ? "bg-blue-500 text-white ml-auto"
                    : "bg-gray-100 text-gray-800"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {/* Show agent info for assistant messages */}
                {msg.role === "assistant" && msg.agent && (
                  <div className="mt-1 text-xs text-gray-500">
                    🤖 {msg.agent.name}
                  </div>
                )}

                {msg.files && msg.files.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {msg.files.map((file, fileIndex) => (
                      <div key={fileIndex} className="text-xs">
                        <button
                          onClick={() => handleFileClick(file)}
                          className="flex items-center gap-1 text-blue-300 hover:text-blue-100 hover:underline cursor-pointer transition-colors p-1 rounded hover:bg-blue-500/10"
                          title={`Click to view: ${
                            file.name ||
                            file.filename ||
                            `File ${fileIndex + 1}`
                          }`}
                        >
                          📎{" "}
                          {file.name ||
                            file.filename ||
                            `File ${fileIndex + 1}`}
                          <span className="ml-1 text-blue-200">↗</span>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      {/* Welcome message and input */}
      <div
        className={`flex-shrink-0 border bg-gray-50 rounded-xl ${
          messages.length === 0
            ? "flex-1 flex items-center gap-2 flex-col justify-center"
            : ""
        }`}
      >
        {/* Welcome message */}
        {messages.length === 0 && (
          <div className="w-full animate-typing overflow-hidden whitespace-nowrap flex items-center justify-center font-bold text-2xl mb-4">
            What can I help you with?
          </div>
        )}

        {/* Uploaded Documents Viewer */}
        {id && uploadedDocs.length > 0 && (
          <div
            className={`bg-gray-50 ${
              uploadedDocs.length > 0 ? "rounded-t-lg" : ""
            } shadow-sm border border-gray-200`}
          >
            <div className="p-3 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => setDocsViewerOpen(!docsViewerOpen)}
                  className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
                >
                  <span>
                    📚 Uploaded Documents{" "}
                    {uploadedDocs.length > 0 && `(${uploadedDocs.length})`}
                    {loadingDocs && (
                      <span className="ml-1 text-xs text-blue-600">↻</span>
                    )}
                  </span>
                  <span
                    className={`transform transition-transform ${
                      docsViewerOpen ? "rotate-90" : ""
                    }`}
                  >
                    ▶
                  </span>
                </button>
              </div>
            </div>

            {docsViewerOpen && (
              <div className="p-3 max-h-64 overflow-y-auto">
                {loadingDocs ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="text-gray-500">Loading documents...</div>
                  </div>
                ) : uploadedDocs.length === 0 ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="text-gray-500">
                      No documents uploaded yet
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {uploadedDocs.map((doc, index) => (
                      <div
                        key={doc.doc_id || index}
                        className="flex items-center justify-between p-3 rounded-lg border border-gray-200 hover:border-gray-300 bg-gray-50 hover:bg-gray-100 transition-all"
                      >
                        <div className="flex items-center min-w-0 flex-1">
                          <div className="flex items-center gap-3">
                            <span className="text-lg">📄</span>
                            <div className="flex flex-col min-w-0 flex-1">
                              <div className="text-sm font-medium text-gray-700 truncate">
                                {doc.doc_name || `Document ${index + 1}`}
                              </div>
                              {doc.upload_date && (
                                <div className="text-xs text-gray-500">
                                  Uploaded:{" "}
                                  {new Date(
                                    doc.upload_date
                                  ).toLocaleDateString()}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 ml-2">
                          <button
                            onClick={() => handleViewUploadedDoc(doc)}
                            className="p-1 text-gray-500 hover:text-blue-600 transition-colors"
                            title="View document info"
                          >
                            👁️
                          </button>
                          <button
                            onClick={() => handleDeleteDoc(doc.doc_id)}
                            className="p-1 text-gray-500 hover:text-red-600 transition-colors"
                            title="Delete document"
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Input form */}
        <form
          id="chat-form"
          className={`w-full shadow-lg py-2 flex px-4 bg-gray-50 overflow-hidden ${
            uploadedDocs.length > 0 ? "" : "rounded-xl"
          }  border-gray-200 transition-all duration-200`}
          onSubmit={handleSendMessage}
        >
          <div className="w-full">
            {/* File upload progress bar */}
            {isUploading && (
              <div className="mb-2">
                <div className="text-xs text-gray-600 mb-1">
                  Uploading files...
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
              </div>
            )}

            {/* Selected files preview */}
            {selectedFiles.length > 0 && (
              <div className="mb-2">
                <div className="flex items-center justify-between mb-1">
                  <div className="text-xs text-gray-600">
                    {selectedFiles.length} file
                    {selectedFiles.length > 1 ? "s" : ""} selected
                  </div>
                  {selectedFiles.length > 1 && (
                    <button
                      type="button"
                      onClick={() => setSelectedFiles([])}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Clear all
                    </button>
                  )}
                </div>
                <div className="space-y-1 max-h-24 overflow-y-auto">
                  {selectedFiles.map((file, index) => (
                    <div
                      key={`${file.name}-${index}`}
                      className="flex items-center justify-between bg-blue-50 p-2 rounded text-sm"
                    >
                      <div className="flex items-center min-w-0 flex-1">
                        <button
                          type="button"
                          onClick={() => handleLocalFileClick(file)}
                          className="flex items-center min-w-0 flex-1 text-left hover:text-blue-600 transition-colors"
                          title="Click to preview file"
                        >
                          <span className="text-gray-700 truncate">
                            📎 {file.name}
                          </span>
                          <span className="text-gray-500 ml-2 text-xs flex-shrink-0">
                            ({(file.size / 1024 / 1024).toFixed(2)} MB)
                          </span>
                          <span className="ml-1 text-blue-400 text-xs">👁</span>
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="text-red-500 hover:text-red-700 ml-2 flex-shrink-0"
                        title="Remove file"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Textarea */}
            <textarea
              className="w-full border-none resize-none text-lg px-2 focus:ring-0 focus:outline-none text-gray-700 placeholder:text-gray-500 bg-transparent min-h-[2.5rem] max-h-32"
              rows={2}
              placeholder="Type a message..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              ref={inputRef}
            />

            {/* Hidden file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              multiple
              accept="image/*,.pdf,.doc,.docx,.txt"
              className="hidden"
            />

            {/* Action buttons */}
            <div className="flex justify-between items-center mt-2">
              <div className="flex gap-2">
                {/* Attach button */}
                <button
                  type="button"
                  onClick={openFileDialog}
                  disabled={isUploading}
                  className={`border rounded-xl py-1 px-2 flex gap-1 text-center hover:bg-gray-100 disabled:opacity-50 flex-shrink-0 transition-colors ${
                    selectedFiles.length > 0
                      ? "bg-blue-50 border-blue-300 text-blue-700"
                      : "hover:bg-gray-100"
                  }`}
                >
                  <FontAwesomeIcon icon={faDownload} />
                  <span className="text-sm">
                    {selectedFiles.length > 0
                      ? `Files (${selectedFiles.length})`
                      : "Attach"}
                  </span>
                </button>

                {/* Agents dropdown */}
                <div className="relative">
                  <button
                    ref={agentButtonRef}
                    type="button"
                    onClick={() => {
                      if (!agentDropdownOpen) {
                        // Calculate position when opening - position above the button
                        const rect =
                          agentButtonRef.current.getBoundingClientRect();
                        setAgentDropdownPosition({
                          top: rect.top + window.scrollY - 280, // Position well above the button
                          left: rect.left + window.scrollX,
                          width: Math.max(rect.width, 200),
                        });
                      }
                      setAgentDropdownOpen(!agentDropdownOpen);
                    }}
                    className="border rounded-xl py-1 px-2 flex gap-1 text-center hover:bg-gray-100 flex-shrink-0 transition-colors"
                  >
                    <span className="text-sm">
                      {selectedAgent ? selectedAgent.name : "Agents"}
                      {loadingAgents && " ↻"}
                    </span>
                    <span
                      className={`text-xs transform transition-transform ${
                        agentDropdownOpen ? "rotate-180" : ""
                      }`}
                    >
                      ▼
                    </span>
                  </button>
                </div>
              </div>

              {/* Send button */}
              <button
                type="submit"
                disabled={!message || message.trim() === "" || isUploading}
                className="hover:text-blue-500 disabled:hover:text-gray-400 disabled:text-gray-400 text-gray-600 transition-colors p-2 flex-shrink-0"
              >
                <FontAwesomeIcon icon={faPaperPlane} />
              </button>
            </div>
          </div>
        </form>
      </div>
      {/* File Modal */}
      {fileModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75"
          onClick={closeModal}
        >
          <div
            className="bg-white rounded-lg max-w-4xl max-h-[90vh] w-full mx-4 flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold truncate">
                {currentFile?.name || currentFile?.filename || "File Preview"}
                {fileContent?.isLocal && (
                  <span className="text-sm text-gray-500 ml-2">
                    (Local File)
                  </span>
                )}
              </h3>
              <button
                onClick={closeModal}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 p-4 overflow-auto">
              {loadingFile ? (
                <div className="flex items-center justify-center h-32">
                  <div className="text-gray-500">Loading file...</div>
                </div>
              ) : fileContent?.error ? (
                <div className="flex items-center justify-center h-32">
                  <div className="text-red-500">{fileContent.error}</div>
                </div>
              ) : fileContent?.type === "image" ? (
                <div className="flex justify-center">
                  <img
                    src={fileContent.url}
                    alt={fileContent.name}
                    className="max-w-full max-h-[60vh] object-contain"
                  />
                </div>
              ) : fileContent?.type === "pdf" ? (
                <iframe
                  src={fileContent.url}
                  className="w-full h-[60vh] border-0"
                  title={fileContent.name}
                />
              ) : fileContent?.type === "text" ? (
                <div className="bg-gray-50 p-4 rounded border">
                  <pre className="whitespace-pre-wrap text-sm text-gray-800 max-h-[50vh] overflow-auto">
                    {fileContent.content}
                  </pre>
                </div>
              ) : fileContent?.type === "download" ? (
                <div className="flex flex-col items-center justify-center h-32 space-y-4">
                  <div className="text-gray-600 text-center">
                    <div className="text-2xl mb-2">📄</div>
                    <div>
                      {fileContent.isLocal
                        ? "File ready for upload"
                        : "Preview not available for this file type"}
                    </div>
                    <div className="text-sm text-gray-500">
                      {fileContent.name}
                    </div>
                    {fileContent.isLocal && fileContent.size && (
                      <div className="text-xs text-gray-400 mt-1">
                        Size: {(fileContent.size / 1024 / 1024).toFixed(2)} MB
                        {fileContent.lastModified && (
                          <span className="ml-2">
                            Modified:{" "}
                            {new Date(
                              fileContent.lastModified
                            ).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  {!fileContent.isLocal && (
                    <button
                      onClick={() => window.open(fileContent.url, "_blank")}
                      className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors"
                    >
                      Download File
                    </button>
                  )}
                </div>
              ) : fileContent?.type === "document-info" ? (
                <div className="flex flex-col items-center justify-center h-64 space-y-4">
                  <div className="text-gray-600 text-center">
                    <div className="text-4xl mb-4">📄</div>
                    <div className="text-lg font-medium text-gray-800 mb-2">
                      Uploaded Document
                    </div>
                    <div className="text-sm text-gray-500 mb-4">
                      {fileContent.name}
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg border space-y-2 text-left max-w-md">
                      <div className="flex justify-between">
                        <span className="font-medium">Document ID:</span>
                        <span className="text-gray-600">
                          {fileContent.docId}
                        </span>
                      </div>
                      {fileContent.uploadDate && (
                        <div className="flex justify-between">
                          <span className="font-medium">Upload Date:</span>
                          <span className="text-gray-600">
                            {new Date(
                              fileContent.uploadDate
                            ).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="font-medium">Status:</span>
                        <span className="text-green-600">✓ Processed</span>
                      </div>
                    </div>

                    <div className="text-xs text-gray-400 mt-4">
                      This document has been uploaded and processed for
                      chatting. The content is available for questions and
                      analysis.
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-32">
                  <div className="text-gray-500">Unable to load file</div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            {fileContent && !fileContent.error && (
              <div className="border-t p-4 flex justify-between items-center">
                <div className="text-sm text-gray-500">
                  {fileContent.name}
                  {fileContent.isLocal && (
                    <span className="ml-2 text-blue-500">
                      (Ready to upload)
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {fileContent.url && !fileContent.isLocal && (
                    <>
                      <button
                        onClick={() => window.open(fileContent.url, "_blank")}
                        className="text-blue-500 hover:text-blue-700 text-sm"
                      >
                        Open in New Tab
                      </button>
                      <button
                        onClick={() => {
                          const link = document.createElement("a");
                          link.href = fileContent.url;
                          link.download = fileContent.name || "download";
                          link.click();
                        }}
                        className="text-blue-500 hover:text-blue-700 text-sm"
                      >
                        Download
                      </button>
                    </>
                  )}
                  {fileContent.isLocal && (
                    <span className="text-xs text-gray-400">
                      File will be uploaded when you send your message
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Chatbot;
