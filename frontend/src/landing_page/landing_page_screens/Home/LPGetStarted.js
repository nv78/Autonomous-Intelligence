import React from "react";

function LPGetStarted() {
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
        Use Panacea Today
      </div>
      <div className="text-center">
        <button
          onClick={() => {
            window.location.assign("https://calendly.com/natanvidra/anote");
          }}
          class="btn-yellow"
        >
          Schedule a Demo
        </button>
      </div>
    </div>
  );
}

export default LPGetStarted;
