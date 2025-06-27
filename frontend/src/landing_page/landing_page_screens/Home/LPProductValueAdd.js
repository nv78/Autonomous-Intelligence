import React from "react";

function LPProductValueAdd({ image, title, description }) {
  return (
    <div
      class="bg-gray-700 rounded mb-8 overflow-hidden shadow-lg transition-all duration-500"
    >
      <img class="w-full" src={image} alt={title} loading="lazy" />
      <div class="px-6 py-4 ">
        <div class="font-bold text-xl mb-2">{title}</div>
        <p class="text-gray-300 text-base">{description}</p>
      </div>
    </div>
  );
}

export default LPProductValueAdd;