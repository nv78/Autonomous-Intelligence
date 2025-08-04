import React from "react";

function LPAIDay() {
  const urlObject = new URL(window.location.origin);
  var hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `dashboard.${hostname}`;

  var startPath = urlObject.toString();
  return (
    <div className="mb-24">
      <div className="text-3xl sm:text-4xl lg:text-5xl my-10 text-center font-medium lg:font-bold">
        Join Enterprise AI Leaders at our Primers of AI Day Summit!
      </div>
      <div className="text-center">
        <button
          onClick={() => {
            window.location.assign(startPath);
          }}
          class="btn-yellow"
        >
          Get Started
        </button>
      </div>
    </div>
  );
}

export default LPAIDay;
