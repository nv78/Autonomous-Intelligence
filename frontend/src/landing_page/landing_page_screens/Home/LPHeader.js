// import React, { useState, useEffect, Suspense, lazy } from "react";

// function LPHeader(props) {
//   const [text, setText] = useState("Chat With Your");
//   const [animation, setAnimation] = useState("slideIn");
//   const urlObject = new URL(window.location.origin);
//   var hostname = urlObject.hostname;
//   if (hostname.startsWith("www.")) {
//     hostname = hostname.substring(4);
//   }
//   urlObject.hostname = `dashboard.${hostname}`;

//   var startPath = urlObject.toString();
//   return (

//     <section className="mt-24 pt-10 lg:mb-60">
//       <div className="container mx-auto flex px-5 lg:flex-row flex-col items-center lg:items-start">
//         <div className="lg:flex-grow lg:w-2/3 pt-12 lg:pr-24 md:pr-16 flex flex-col lg:items-start lg:text-left lg:mb-0 items-center text-center">
//           {!props.open && (
//             <h1
//               className={`font-urbanist text-[36px] font-extralight leading-[43.2px] tracking-[0.05em] text-left bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent`}
//             >
//               panacea
//             </h1>
//           )}
//           <h1 className={`font-urbanist text-[64px] font-extralight leading-[76.8px] tracking-[0.05em] text-left`}>
//             autonomous AI agents
//           </h1>
//           <br class="inline-block"></br>
//           <div className="flex flex-col sm:flex-row justify-center">
//         <button
//           className="btn-yellow mb-4 sm:mb-0 sm:mr-4 w-full sm:w-auto flex justify-center items-center"
//           onClick={() => {
//             window.location.assign(startPath);
//           }}
//         >
//           Get Started
//         </button>
//         <button
//           className="btn-black w-full sm:w-auto flex justify-center items-center"
//           onClick={() => {
//             window.location.assign("https://calendly.com/natanvidra/anote");
//           }}
//         >
//           Schedule Demo
//         </button>
//       </div>
//         </div>
//         <div className="flex-auto">
//           <div className="md:w-1/2 md:h-1/2 ml-auto">
//           <img
//             src="/landing_page_assets/panacearighticon.png"
//             loading="lazy"
//           />
//           </div>
//         </div>
//       </div>
//     </section>
//   );
// }

// export default LPHeader;

import React, { useState, useEffect } from "react";

function LPHeader(props) {
  const [text, setText] = useState("Chat With Your");
  const [animation, setAnimation] = useState("slideIn");
  const urlObject = new URL(window.location.origin);
  let hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `dashboard.${hostname}`;
  const startPath = urlObject.toString();

  return (
    <section className="mt-24 pt-10 lg:mb-60">
      <div className="container mx-auto flex px-5 lg:flex-row flex-col items-center lg:items-start">
        <div className="lg:flex-grow lg:w-2/3 pt-12 lg:pr-24 md:pr-16 flex flex-col lg:items-start items-center text-center">
          {!props.open && (
            <h1 className="font-urbanist text-[36px] font-extralight leading-[43.2px] tracking-[0.05em] text-left bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">
              panacea
            </h1>
          )}
          <h1 className="font-urbanist text-[30px] md:text-[64px] font-extralight leading-tight tracking-[0.05em] text-center lg:text-left">
            autonomous AI agents
          </h1>
          <br className="inline-block" />
          <div className="flex flex-col sm:flex-row justify-center pb-8">
            <button
              className="btn-yellow mb-4 sm:mb-0 sm:mr-4 w-full sm:w-auto flex justify-center items-center"
              onClick={() => window.location.assign(startPath)}
            >
              Get Started
            </button>
            <button
              className="btn-black w-full sm:w-auto flex justify-center items-center"
              onClick={() => window.location.assign("https://calendly.com/natanvidra/anote")}
            >
              Schedule Demo
            </button>
          </div>
        </div>
        {/* Hide image on mobile view */}
        <div className="hidden md:flex flex-auto">
          <div className="md:w-1/2 md:h-1/2 ml-auto">
            <img
              src="/landing_page_assets/panacearighticon.png"
              loading="lazy"
              alt="Panacea Icon"
            />
          </div>
        </div>
      </div>
    </section>
  );
}

export default LPHeader;
