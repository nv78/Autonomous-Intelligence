import React from "react";
import { useNavigate } from "react-router-dom";

function Customer({ image, title, industry, description, route }) {
  const navigate = useNavigate();
  const handleClick = () => {
    window.location.href = "#top";
    let docUrl = "https://privatechatbot.ai"; // Default document URL
    switch (title) {
      case "10k":
        docUrl = "https://drive.google.com/file/d/1zl1GhjVn_OnGv4EARbc5cCKKFVHMeiUA/view?usp=sharing";
        break;
      case "Know Your Customer":
        docUrl = "https://drive.google.com/file/d/11BLc4R4icAtExeJJzwqDphzdbIsJAhH-/view?usp=sharing";
        break;
      case "Workflows":
        docUrl = "https://drive.google.com/file/d/1c8EHLIPXzEAcAzbmFb6D4NNMK184MxOC/view?usp=sharing";
        break;
      default:
        docUrl = "https://privatechatbot.ai";
    }
    navigate('/customercasestudy', { state: { docUrl: docUrl } });
  };
  return (
    <div
      class="bg-gray-950 py-8 rounded overflow-hidden shadow-lg hover:shadow-2xl md:hover:scale-110 transition-all duration-500 cursor-pointer relative group"
      onClick={handleClick}
      >
      <img class="mx-auto w-[100%] h-[75%] group-hover:hidden" src={image} alt={title} loading="lazy" />

      <div class="px-6 py-4">
        <p class="text-gray-300 text-base"><strong class="text-gray-100 text-base">Sector: </strong>{industry}</p>
        <p class="text-gray-300 text-base"><strong class="text-gray-100 text-base">Task Type: </strong>{description}</p>
      </div>

      <div class="opacity-0 group-hover:opacity-100 transition-opacity duration-250 hover:cursor-pointer absolute inset-0 flex justify-center items-center bg-gray-950 group-hover:flex">
        <span class="text-white text-lg">View Case Study</span>
      </div>
    </div>
  );
}

export default Customer;