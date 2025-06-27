// import React from "react";
// import LPProductValueAdd from "./Home/LPProductValueAdd";
// import LPHighLevel from "./Home/LPHighLevel";

// function FinanceGPT() {
//   return (
//     <div className="text-white max-w-screen">
//       <div className="w-screen">
//         <div className="w-full md:w-3/4 mx-auto my-10">
//           <div className="flex flex-col-reverse md:flex-row items-center">
//             <img
//               src="/landing_page_assets/IsPrivate.png"
//               className="w-11/12 md:w-3/5 rounded-xl"
//               alt="Agent Registry Illustration"
//             />
//             <div className="px-10 mb-5">
//               <div className="text-2xl font-semibold py-5">
//                 Explore the Agent Registry
//               </div>
//               <div className="text-lg">
//                 Access a curated registry of closed-source agents, each designed for specialized tasks. These agents run privately within your environment, ensuring data remains secure and accessible only to authorized users. Run your agents in private, functioning autonomously within your local infrastructure, never transmitting data outside your secure network.
//               </div>
//             </div>
//           </div>
//         </div>

//         <div className="mx-5 lg:mx-2 mt-24">
//           <div className="text-3xl sm:text-4xl lg:text-5xl my-15 text-center font-medium lg:font-bold">
//             Your Agentic AI System
//           </div>
//           <div className="p-10 grid grid-cols-1 sm:grid-cols-1 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-3 gap-5">
//             <LPHighLevel
//               image="/landing_page_assets/privatewhite.png"
//               title="Personal"
//               description="Access to user interface for personal agent use, including basic file uploads and chat capabilities."
//             />
//             <LPHighLevel
//               image="/landing_page_assets/accuratewhite.png"
//               title="Developer"
//               description="API access for developers needing flexible and customizable agent deployments."
//             />
//             <LPHighLevel
//               image="/landing_page_assets/citationswhite.png"
//               title="Enterprise"
//               description="Scalable private solutions tailored for enterprise environments, with support for custom models and agents."
//             />
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// }

// export default FinanceGPT;

import React from "react";
import LPProductValueAdd from "./Home/LPProductValueAdd";
import LPHighLevel from "./Home/LPHighLevel";

function FinanceGPT() {
  return (
    <div className="text-white max-w-screen">
      <div className="w-screen">
        <div className="w-full md:w-3/4 mx-auto my-10">
          <div className="flex flex-col-reverse md:flex-row items-center">
            <img
              src="/landing_page_assets/registrynew.png"
              className="w-11/12 md:w-3/5 rounded-xl"
              alt="Agent Registry"
            />
            <div className="px-10 mb-5">
              <h2 className="text-2xl font-semibold py-5">
                Explore the Agent Registry
              </h2>
              <p className="text-lg">
                Access a curated registry of closed-source agents, each designed for specialized tasks. These agents run securely within your environment, ensuring data remains protected and accessible only to authorized users. Operate your agents autonomously within your local, private infrastructure.
              </p>
            </div>
          </div>
        </div>

        <div className="mx-5 lg:mx-2 mt-24">
          <h1 className="text-3xl sm:text-4xl lg:text-5xl my-15 text-center font-medium lg:font-bold">
            Your Agentic AI System
          </h1>
          <div className="p-10 grid grid-cols-1 sm:grid-cols-1 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-3 gap-5">
            <LPHighLevel
              image="/landing_page_assets/citationswhite.png"
              title="Personal"
              description="User interface access for personal agents, enabling file uploads and chat features."
            />
            <LPHighLevel
              image="/landing_page_assets/accuratewhite.png"
              title="Developer"
              description="Flexible API access for developers needing customizable agent deployments."
            />
            <LPHighLevel
              image="/landing_page_assets/privatewhite.png"
              title="Enterprise"
              description="Scalable private solutions tailored for enterprise needs, supporting custom models and agents."
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default FinanceGPT;
