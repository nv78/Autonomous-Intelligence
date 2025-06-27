import React, { useState, useEffect } from "react";
import fetcher from "../../../http/RequestConfig";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

import {
    faFileUpload,
    faPaperPlane,
    faTimes,
    faCheck,
    faPen,
} from "@fortawesome/free-solid-svg-icons";

function FinanceReports() {
    const [tickers, setTickers] = useState([]);
    const [ticker, setTicker] = useState("");
    const [isValidTicker, setIsValidTicker] = useState(false);
    const [questions, setQuestions] = useState([]);
    const [currentQuestion, setCurrentQuestion] = useState("");
    const [pdfContent, setPdfContent] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [files, setFiles] = useState([]);
    const [showConfirmPopup, setShowConfirmPopup] = useState(false);
    const [showRenameModal, setShowRenameModal] = useState(false);
    const [workflowIdToRename, setWorkflowIdToRename] = useState(null);
    const [newWorkflowName, setNewWorkflowName] = useState("");
    const [workflowName, setWorkflowName] = useState("");
    const [workflowId, setWorkflowId] = useState(0);


    useEffect(() => {
      console.log("Initializing workflow");

      const createNewWorkflow = async () => {
        console.log("createNewWorkflow");
        const response = await fetcher("create-new-workflow", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },

          body: JSON.stringify(""),

        }).catch((e) => {
          console.error("Error creating workflow:", e);
        });

        const response_data = await response.json();
        console.log("WORKFLOW SUCCESSFULLY CREATED. ID:", response_data.workflow_id);
        setWorkflowId(response_data.workflow_id);

        return response_data.workflow_id;
      };

        const workflow_name = "Untitled Workflow (" + workflowId.toString() +")";
        setWorkflowName(workflow_name);
        console.log(workflow_name);
    }, []);

    const handleRenameWorkflow = async (workflowId) => {
      console.log("handleRenameWorkflow");
      setWorkflowIdToRename(workflowId);
      console.log("HANDLE RENAME WORKFLOW FOR WORKFLOW ", workflowId)
      setNewWorkflowName("");
      setShowRenameModal(true);
    };

    const confirmRenameWorkflow = () => {
      console.log("new workflow name", newWorkflowName);
      renameWorkflow(workflowIdToRename, newWorkflowName);
      setWorkflowName(newWorkflowName);
      setShowRenameModal(false);
    };

    const cancelRenameWorkflow = () => {
        setShowRenameModal(false);
    };

    const renameWorkflow = async (workflowId, new_name) => {
      console.log("New name: ", new_name, " & workflow id: ", workflowId)

      const response = await fetcher("/update-workflow-name", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          workflow_id: workflowId,
          workflow_name: new_name,
        }),
      }).catch((e) => {
        console.error(e);
      });
    };

    const renameModal = showRenameModal ? (
      <>
      {console.log("renameModal")}
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.4)",
            zIndex: 999,
          }}
        />
        {" "}
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
 text-white "
        >
          <div style={{ position: "relative" }}>
            <div>
              <div className="my-2">Enter new workflow name</div>
              <input
                type="text"
                className="rounded-xl bg-[#3A3B41] border-none focus:ring-0 focus:border-white text-white placeholder:text-gray-300"
                onChange={(e) => setNewWorkflowName(e.target.value)}
                value={newWorkflowName}
              />
            </div>
            <div className="w-full flex justify-between mt-4">
              <button
                onClick={cancelRenameWorkflow}
                className="w-1/2 mx-2 py-2 bg-gray-700 rounded-lg hover:bg-[#141414]
"
              >
                Cancel
              </button>
              <button
                onClick={confirmRenameWorkflow}
                className="w-1/2 mx-2 py-2 bg-gray-700 rounded-lg hover:bg-[#141414]
"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      </>
    ) : null;

    const handleTickerChange = (e) => {
        console.log("handleTickerChange");
        const inputTicker = e.target.value.toUpperCase();
        setTicker(inputTicker);
        setIsValidTicker(checkTickerValidity(inputTicker));
    };

    const handleAddTicker = (e) => {
        if (isValidTicker && !tickers.includes(ticker) && e.key === "Enter") {
            console.log("handleAddTicker");
            setTickers([...tickers, ticker]);
            setTicker("");
            setIsValidTicker(false);
            console.log("Tickers:", tickers);
        }
    };

    const handleRemoveTicker = (removedTicker) => {
        console.log("handleRemoveTicker");
        const updatedTickers = tickers.filter((t) => t !== removedTicker);
        setTickers(updatedTickers);
        console.log("Tickers:", tickers);
    };

    const handleRemoveFile = (removedFile) => {
        console.log("handleRemoveFile");
        // Filter out the removed file from the files state
        const updatedFiles = files.filter((file) => file !== removedFile);
        setFiles(updatedFiles);
        console.log("Files:", updatedFiles);
    };

    const handleFileChange = (e) => {
        console.log("handleFileChange");
        const selectedFiles = e.target.files;

        // Update the files state with the selected files
        setFiles([...files, ...selectedFiles]);

        // Optionally, you can clear the file input value to allow selecting the same file again
        e.target.value = null;
    };

    const handleQuestionChange = (e) => {
        console.log("handleQuestionChange");
        setCurrentQuestion(e.target.value);
    };

    const askQuestion = () => {
        console.log("askQuestion");
        if (currentQuestion.trim() !== "") {
            setQuestions([...questions, currentQuestion]);
            setCurrentQuestion("");
        }
    };

    const handleRemoveQuestion = (removedQuestion) => {
        console.log("handleRemoveQuestion");
        const updatedQuestions = questions.filter((q) => q !== removedQuestion);
        setQuestions(updatedQuestions);
    };

    const checkTickerValidity = async (inputTicker) => {
        console.log("checkTickerValidity");
        const response = await fetcher("check-valid-ticker", {
            method: "POST",
            headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ ticker: inputTicker }),
        });

        const data = await response.json();
        console.log("ticker abc", inputTicker);
        console.log("data is", data.isValid);
        setIsValidTicker(data.isValid);
    };

    const generatePDF = async () => {
        try {
            console.log("Requesting PDF generation...");
            // Make a fetch request to your Flask backend endpoint
            const response = await fetcher("/generate_financial_report", {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    tickers: tickers,
                    questions: questions,
                    workflowId: workflowId,
                }),
            });

            if (response.ok) {
                // If the response is successful, retrieve the blob
                const blob = await response.blob();

                // Create a URL pointing to the blob
                const pdfDataUrl = URL.createObjectURL(blob);

                // Set the PDF content in the state
                setPdfContent(pdfDataUrl);

                console.log("PDF generated successfully");
            } else {
                console.error("Failed to generate or download PDF");
                // Handle error scenarios
            }
        } catch (error) {
            console.error("Error generating or downloading PDF", error);
        }
    };

    return (
        <div className="p-10">
            <div className="grid grid-cols-2 space-x-8">
                <div className="">
                    <div className="text-white text-l my-1.5">
                        Workflows{" "}
                        <span className=" text-[#28b2fb]">
                            / Financial Report
                        </span>
                    </div>
                    <div className="flex items-center my-2">
                        <div className="text-3xl text-white font-bold">
                            {workflowName}
                        </div>
                        <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRenameWorkflow(workflowId);
                            }}
                            className="ml-2 text-lg text-white"
                          >
                            <FontAwesomeIcon icon={faPen} />
                        </button>
                    </div>
                    {renameModal}
                    <div className="bg-[#141414]
 py-4 px-6 my-2 h-[70vh] max-h-[70vh] overflow-y-scroll">
                        <div className="mb-6 ">
                            <label
                                htmlFor="ticker"
                                className="text-white font-semibold text-lg"
                            >
                                Enter Tickers
                            </label>
                            <div
                                style={{
                                    position: "relative",
                                    display: "flex",
                                    flexDirection: "row",
                                    marginTop: "5px",
                                    width: "100%",
                                }}
                            >
                                <input
                                    type="text"
                                    id="ticker-input"
                                    placeholder="e.g. AAPL"
                                    value={ticker}
                                    onChange={handleTickerChange}
                                    onKeyPress={handleAddTicker}
                                    className="w-1/2 rounded-lg py-2 px-3 mr-2 bg-[#141414]
 text-white border-none focus:ring-1 focus:ring-[#28b2fb]
"
                                />
                            </div>

                            {/* Display tickers below the input box */}
                            {tickers.length > 0 && (
                                <div className="flex my-2 flex-wrap">
                                    {tickers.map((t, index) => (
                                        <div
                                            key={index}
                                            className="flex w-max px-3 text-white items-center bg-[#141414]
 mx-2 my-1"
                                        >
                                            <span className="mr-4">{t}</span>
                                            <FontAwesomeIcon
                                                className="cursor-pointer"
                                                icon={faTimes}
                                                onClick={() =>
                                                    handleRemoveTicker(t)
                                                }
                                            />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* File Input */}
                        <label
                            htmlFor="file"
                            className=" text-white font-semibold text-lg"
                        >
                            Upload Documents
                        </label>
                        <div className="mb-6 mt-2">
                            <div className="rounded-xl border-2 border-gray-500 bg-[#141414]
">
                                <div className="text-center w-full py-20">
                                    <FontAwesomeIcon
                                        icon={faFileUpload}
                                        style={{
                                            fontSize: "24px",
                                            cursor: "pointer",
                                            color: "#59788E", // Adjust the color as needed
                                        }}
                                        className=""
                                        onClick={() => {
                                            // Trigger the file input programmatically
                                            document
                                                .getElementById("file")
                                                .click();
                                        }}
                                    />
                                    <div className="w-full text-gray-400">
                                        Browse Files
                                    </div>
                                </div>
                                {/* Hidden file input */}
                                <input
                                    type="file"
                                    id="file"
                                    onChange={handleFileChange}
                                    style={{
                                        display: "none", // Hide the default file input
                                    }}
                                />
                            </div>
                            {/* Display uploaded files */}
                            {files.length > 0 && (
                                <div>
                                    {files.map((file, index) => (
                                        <div className="flex w-max px-3 text-white items-center bg-[#141414]
 mx-2 my-1">
                                            <span className="mr-3">
                                                {file.name}
                                            </span>
                                            <FontAwesomeIcon
                                                icon={faTimes}
                                                className="cursor-pointer"
                                                onClick={() =>
                                                    handleRemoveFile(file)
                                                }
                                            />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Question Input and List */}
                        <div>
                            <label
                                htmlFor="question"
                                className="text-white font-semibold text-lg"
                            >
                                Ask any Questions
                            </label>
                            <div className="flex items-center mb-3 mt-2">
                                <input
                                    type="text"
                                    id="question"
                                    placeholder="Enter Question"
                                    value={currentQuestion}
                                    onChange={handleQuestionChange}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter") {
                                            askQuestion();
                                        }
                                    }}
                                    className="flex-grow rounded-lg py-2 px-3 mr-2 bg-[#141414]
 text-white border-none focus:ring-1 focus:ring-[#28b2fb]"
                                />
                                <div
                                    className="text-white bg-[#141414]
 px-4 py-2 rounded-lg cursor-pointer"
                                    onClick={askQuestion}
                                >
                                    <FontAwesomeIcon icon={faPaperPlane} />
                                </div>
                            </div>
                            {questions.length > 0 && (
                                <div className="">
                                    {questions.map((q, index) => (
                                        <div
                                            key={index}
                                            className="flex w-full justify-between px-3 py-2 rounded-lg text-white items-center bg-[#141414]
 mb-1"
                                        >
                                            <span>{q}</span>
                                            <FontAwesomeIcon
                                                icon={faTimes}
                                                className="cursor-pointer mx-3"
                                                onClick={() =>
                                                    handleRemoveQuestion(q)
                                                }
                                            />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                    <div>
                        <div className="w-[20%] mt-2"></div>
                        <button
                            onClick={generatePDF}
                            className="bg-gradient-to-r from-[#2E5C82] to-[#40C6FF] text-white font-bold rounded-lg px-4 py-2 mt-2 hover:bg-[#28b2fb]"
                        >
                            Generate Report
                        </button>
                    </div>
                </div>
                {/* Column 2: Generate PDF Button and Display PDF */}

                {/* Display PDF on the screen */}
                {pdfContent ? (
                    <div className="my-2">
                        <object
                            data={pdfContent}
                            type="application/pdf"
                            className="w-full min-h-[85vh]"
                        >
                            <div class="flex justify-center items-center my-2 w-[95%] h-[85vh] text-white bg-[#141414]
">
                                <div class="font-bold">
                                    No Report Generated Yet
                                </div>
                            </div>
                        </object>
                    </div>
                ) : (
                    <div class="flex justify-center items-center my-2 w-[95%] h-[85vh] text-white bg-[#141414]
">
                        <div class="font-bold">No Report Generated Yet</div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default FinanceReports;
