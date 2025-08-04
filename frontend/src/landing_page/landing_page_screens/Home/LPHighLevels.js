import React from "react";
import LPHighLevel from "./LPHighLevel";
import LPProduct from "./LPProduct";

function LPHighLevels() {
  return (
    <div className="mx-5 lg:mx-24 mb-10">
      <div className="text-3xl sm:text-4xl lg:text-5xl text-center font-semibold md:font-bold">
        Our Solution
      </div>
      <h2 className="text-center pt-3">
        A platform to create, deploy, and monitor autonomous multi-agent systems.
      </h2>
      <div className="p-10 grid grid-cols-1 md:grid-cols-3 gap-5">
        <LPProduct
          image="/new_assets/d.png"
          title="Build Autonomous Agents"
          description="Develop agents equipped with memory, reasoning, and tool capabilities. Each agent is designed to operate independently, handling tasks and managing state within a multi-agent environment."
        />
        <LPProduct
          image="/new_assets/e.png"
          title="Coordinate Agent Teams"
          description="Orchestrate interactions between agents as they collaborate on complex tasks. Panacea’s system enables seamless communication, task handoff, and dynamic adjustment within agent teams."
        />
        <LPProduct
          image="/new_assets/f.png"
          title="Monitor and Optimize"
          description="Track agent performance through detailed metrics and logs. Optimize behavior in real-time, adjusting parameters and workflows to improve efficiency and achieve goals with minimal supervision."
        />
      </div>
    </div>
  );
}

export default LPHighLevels;
