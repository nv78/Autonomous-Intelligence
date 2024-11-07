import React from "react";
import "../../landing_page_styles/LandingPageGPT.css";
import Chatbot from "../../landing_page_components/Chatbot/Chatbot";

const LPPrivateGPT = () => {
  return (
    <div className="mx-5 lg:mx-24">
      <div className="text-3xl sm:text-4xl lg:text-5xl my-10 text-center font-medium lg:font-bold">
        Build Your Private Financial Chatbot
      </div>
      <div className="text-white bg-[#141414]
">
        <div className="grid grid-cols-1 lg:grid-cols-2 pb-10">
          <div className=" w-9/12 mx-auto md:w-10/12">
            <div className="text-2xl lg:text-4xl my-4 text-center md:text-left font-semibold lg:font-extrabold text-[#40C6FF]">
              Your Own AI Assistant
            </div>
            <div className="w-full md:w-3/4 text-base md:text-lg text-center md:text-left">
              <p>
                Chat with your financial documents such as 10-Ks, 10-Qs,
                Earnings Call Transcripts and Annual Reports. Choose either the Llama2 or Mistral private LLMs, or import a fine tuned
                model into your chat to get more accurate answers to your questions. Converse with your documents to get a better understanding.
              </p>
            </div>
            <div className="text-2xl lg:text-4xl my-4 text-center md:text-left font-semibold lg:font-extrabold text-[#40C6FF]">
              Citations and References
            </div>
            <div className="w-full md:w-3/4 text-base md:text-lg text-center md:text-left">
              To mitigate the effects of hallucinations, view the relevant chunk of text, as well as the specific document and page number from where the model obtained it's answer.
            </div>
            <div className="my-4 text-center md:text-left">
              <button
                className="btn-yellow"
                onClick={() => {
                  window.open("https://privatechatbot.ai/", "_blank");
                }}
                style={{ marginTop: "20px", textDecoration: "none" }}
              >
                Try Panacea Now
              </button>
            </div>
          </div>
          <div className="border-[#9B9B9B] border-[4px] w-11/12 mx-auto md:w-10/12 rounded-2xl">
            <Chatbot />
          </div>
        </div>
      </div>
    </div>
  );
};

export default LPPrivateGPT;