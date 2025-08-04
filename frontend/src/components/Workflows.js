import { React, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faFileCsv,
  faFilePen,
  faHardDrive,
} from "@fortawesome/free-solid-svg-icons";
import { AiFillDatabase } from "react-icons/ai";
import { LuMonitorDown } from "react-icons/lu";
import { BiGridAlt } from "react-icons/bi";
import { useNavigate } from "react-router-dom";
import { financialReportsPath, governmentProposalsPath, selectWorkflowsPath } from "../constants/RouteConstants";
import fetcher from "../http/RequestConfig";

function Workflows({
  props,
  onButtonClick,
  dataChooserIndex,
  setDataChooserIndex,
}) {
  const navigate = useNavigate();

  function getActiveClass(index) {
    if (index == dataChooserIndex) {
      return "Active";
    } else {
      return "NotActive";
    }
  }
  
  return (
    <div className="w-1/2 sm:w-3/4 xl:w-1/2 mx-auto my-10">
      <div className="text-4xl text-center text-white font-bold my-4">
        My Workflows
      </div>
      <ul className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-y-12 my-10 justify-between mx-auto">
        <li
          key="1"
          onClick={() => {
            navigate(financialReportsPath)
          }}
        >
          {/* <button className={"ButtonTypeCreate " + getActiveClass(1)}> */}
          <button className="pl-2 pr-2 border-2 flex flex-col space-y-2 items-center rounded-xl w-48 h-48 hover:border-yellow-500 hover:scale-105 duration-200">
            <div className="mb-1 pt-3">
              {/* <img
                src={UploadUnstructuredIcon}
                alt="Upload Unstructured Icon"
              /> */}
              <FontAwesomeIcon
                className="w-12 h-12 text-sky-500 ml-5"
                icon={faFilePen}
              />
            </div>
            <div className="text-xl leading-tight text-white font-bold ">
              Financial Reports
            </div>
            <div className="text-xs leading-tight text-white">
              Create a one page financial report of stock from EDGAR API
            </div>
          </button>
        </li>
        <li
          key="2"
          onClick={() => {
            navigate(governmentProposalsPath)
          }}
        >
          <button className="pl-2 pr-2 border-2 flex flex-col space-y-2 items-center rounded-xl w-48 h-48 hover:border-yellow-500 hover:scale-105 duration-200">
            <div className="mb-1.5 pt-4">
              {/* <img src={UploadStructuredIcon} alt="Upload Structured Icon" /> */}
              <FontAwesomeIcon
                className="w-11 h-11 text-sky-500 ml-5"
                icon={faFileCsv}
              />
            </div>
            <div className="text-xl leading-tight text-white font-bold ">
              Government Proposal
            </div>
            <div className="text-xs leading-tight text-white">
              Generate your own SBIR grant to apply for federal funding
            </div>
          </button>
        </li>
        {/* </ul> */}
        {/* <ul className="row"> */}
        <li
          key="3"
          onClick={() => {
            navigate("/myWorkflows");
          }}
        >
          <button className="pl-3 pr-2 border-2 flex flex-col space-y-2 items-center rounded-xl w-48 h-48 hover:border-yellow-500 hover:scale-105 duration-200">
            <div className="mb-1 pt-3">
              {/* <img src={DatasetHubIcon} alt="Dataset Hub Icon" /> */}
              <FontAwesomeIcon
                className="w-12 h-12 text-sky-500"
                icon={faHardDrive}
              />
            </div>
            <div className="text-xl leading-tight text-white font-bold ">
              Load My Workflows
            </div>
            <div className="text-xs leading-tight text-white">
              Load Your Existing Workflows
            </div>
          </button>
        </li>
      </ul>
    </div>
  );
}

export default Workflows;
