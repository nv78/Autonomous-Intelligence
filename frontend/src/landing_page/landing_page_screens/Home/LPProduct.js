import React from "react";
import { useNavigate } from "react-router-dom";

function LPProduct({ image, title, description, route }) {
  const navigate = useNavigate();


  return (

    <div
      class="rounded mb-8 overflow-hidden shadow-lg md:hover:scale-110 transition-all duration-500 cursor-pointer"
    >
      <img class="w-full" src={image} alt={title} loading="lazy" />
      <div class="px-6 py-4 bg-gradient-to-b from-[#181818] to-[#343F5C] ">
        <div class="font-bold text-xl mb-2">{title}</div>
        <p class="text-gray-300 text-base">{description}</p>
      </div>
    </div>
  );
}

export default LPProduct;
