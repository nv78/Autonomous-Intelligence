import { React, useState, useEffect } from "react";
import fetcher from "../../http/RequestConfig";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronDown,
  faChevronUp,
  faCommentDots,
  faPen,
  faPenToSquare,
  faTrashCan,
} from "@fortawesome/free-solid-svg-icons";

function Sources(props) {
  const [sourcesInfo, setSourcesInfo] = useState([]);
  const [expandedIndex, setExpandedIndex] = useState(null);

  const toggleExpansion = (index) => {
    // If the same index is clicked again, collapse it, otherwise expand the new one
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  useEffect(() => {
    console.log("relevant chunk is", props.relevantChunk);
    const extractedInfo = extractDocumentInfo(props.relevantChunk);
    setSourcesInfo(extractedInfo);
  }, [props.relevantChunk]);

  const extractDocumentInfo = (text) => {
    const regex = /Document:\s*([^:]+):\s*([^]*?)(?=Document:|$)/gi;
    let match;
    const results = [];

    while ((match = regex.exec(text)) !== null) {
      const docName = match[1].trim(); // Trim to remove leading/trailing whitespace
      const paragraph = match[2].trim(); // Trim to remove leading/trailing whitespace
      results.push({ docName, paragraph });
    }

    return results;
  };

  //{docs.map((doc) => (
  //  <div
  //    key={doc.document_name}
  //    className="flex items-center justify-between px-4 hover:bg-[#3A3B41] rounded-xl"
  //  >
  //    <button
  //      key={doc.document_name}
  //      className="flex items-center p-2 my-1 rounded-lg "
  //    >
  //      <span className="text-lg">📄</span>{" "}
  //      {/* Replace with actual icon */}
  //      <span className="ml-2">{doc.document_name}</span>
  //    </button>
  //    <button
  //      onClick={() => handleDeleteDoc(doc.document_name, doc.id)}
  //      className="p-2 ml-4 rounded-full "
  //    >
  //      <FontAwesomeIcon icon={faTrashCan} />
  //    </button>
  //  </div>
  //))}

  return (
    <div className="flex flex-col px-4 mt-4 bg-[#141414]
 rounded-xl py-4 my-4 min-h-[35vh] h-[35vh] overflow-y-scroll">
      <div className="flex flex-row justify-between items-center">
        <h2 className="text-[#FFFFFF] uppercase tracking-wide font-semibold text-s mb-2">
          Sources
        </h2>
      </div>
      {props.activeMessageIndex &&
        sourcesInfo.map((info, index) => (
          <div
            key={index}
            className="mb-2 bg-[#3A3B41] rounded-lg border border-gray-500"
          >
            <div
              onClick={() => toggleExpansion(index)}
              className="flex items-center p-2 my-1 justify-between hover:bg-[#3A3B41] rounded-xl cursor-pointer"
            >
              <span className="text-white">
                {info.docName}
              </span>
              {expandedIndex === index ? (
                <FontAwesomeIcon icon={faChevronUp} className="text-white" />
              ) : (
                <FontAwesomeIcon icon={faChevronDown} className="text-white" />
              )}
            </div>
            {expandedIndex === index && (
              <div className="text-white  p-2 rounded-xl">
                <p>{info.paragraph}</p>
              </div>
            )}
          </div>
        ))}
    </div>
  );
}

export default Sources;
