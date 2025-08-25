import { React, useState, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronDown,
  faChevronUp,
} from "@fortawesome/free-solid-svg-icons";

function Sources(props) {
  const [sourcesInfo, setSourcesInfo] = useState([]);
  const [expandedIndex, setExpandedIndex] = useState(null);

  const toggleExpansion = (index) => {
    // If the same index is clicked again, collapse it, otherwise expand the new one
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  useEffect(() => {
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


  return (
    <div className="flex flex-col px-4 bg-anoteblack-800 py-2  overflow-y-scroll">
      <div className="flex flex-row justify-between items-center">
        <h2 className="text-[#FFFFFF] uppercase tracking-wide font-semibold text-s mb-2">
          Sources
        </h2>
      </div>
      <div className="border h-48 rounded-xl bg-anoteblack-900 border-gray-500">
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
                <span className="text-white">{info.docName}</span>
                {expandedIndex === index ? (
                  <FontAwesomeIcon icon={faChevronUp} className="text-white" />
                ) : (
                  <FontAwesomeIcon
                    icon={faChevronDown}
                    className="text-white"
                  />
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
    </div>
  );
}

export default Sources;
