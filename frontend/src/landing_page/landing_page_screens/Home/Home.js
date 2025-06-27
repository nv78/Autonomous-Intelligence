import React from "react";
import LPHeader from "./LPHeader";
import LPGetStarted from "./LPGetStarted";
import LPPrivateGPT from "./LPPrivateGPT";
import LPHighLevels from "./LPHighLevels";
import FinanceGPT from "../FinanceGPT";

function Home(props) {
  return (
    <div className="bg-[#141414]
 text-white flex flex-col justify-center">
      <LPHeader props={props}></LPHeader>
      <LPHighLevels></LPHighLevels>
      <LPPrivateGPT></LPPrivateGPT>
      <hr class="h-px my-8 bg-gray-200 border-0 dark:bg-gray-700 mx-auto"></hr>
      <FinanceGPT></FinanceGPT>
      <LPGetStarted></LPGetStarted>
    </div>
  );
}

export default Home;
