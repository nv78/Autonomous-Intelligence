import { faArrowRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React from "react";

function Banner({ open }) {
  return (
    <div
      className={` ${
        open ? "hidden" : ""
      } flex items-center font-medium justify-around bg-[#141414]
`}
    >
      <div className="flex items-center justify-around bg-[#141414]
 py-2.5 px-6 cursor:pointer">
        <a
          onClick={() => {
            window.open("https://form.jotform.com/233498501418055", "_blank");
          }}
          className="text-white text-xs md:text-sm lg:text-base lg:font-medium m-0"
          style={{ cursor: "pointer" }}
        >
          View Presentations on Generative AI and LLMs from Anote's AI Day Summit!
        </a>
        <a
          className="text-[#40C6FF] text-xs md:text-sm lg:text-base ml-4 hover:underline cursor-pointer"
          onClick={() => {
            window.open(window.location["origin"] + "/aiday", "_blank");
          }}
        >
          Watch Now
          <FontAwesomeIcon
            className="ml-3 text-[#40C6FF]"
            icon={faArrowRight}
          />
        </a>
      </div>
    </div>
  );
}

export default Banner;
