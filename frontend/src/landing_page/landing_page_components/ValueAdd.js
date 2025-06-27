import { React } from "react";

function ValueAdd(props) {
  return (
    <div className="flex flex-row justify-start text-center mb-10 md:w-3/4 mx-auto">
      <img className="w-10 h-10 mr-5" src={props.image} loading="lazy" />
      <div class="flex flex-col text-start justify-center">
        <p class="text-2xl font-bold text-yellow-500">{props.keyValue}</p>
        <p class="">{props.valueDescription}</p>
      </div>
    </div>
  );
}

export default ValueAdd;
