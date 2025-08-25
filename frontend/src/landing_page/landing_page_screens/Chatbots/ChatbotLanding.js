import React from "react";
import { Link } from "react-router-dom";
import {

    languages,
    companies,
    evaluations,

} from "../../../constants/RouteConstants";

const ChatbotLanding = () => {
  return (
    <section className="text-gray-100 body-font overflow-hidden min-h-screen">
      {/* Header */}
      <div className="flex flex-col text-center w-full mt-10">
        <h1 className="sm:text-5xl text-4xl font-extrabold title-font bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent w-fit mx-auto px-4 py-2">
          Chatbots
        </h1>
        <p className="text-sm text-gray-400 mt-4">
          These are our private chatbots. Some promotional blurb.
        </p>
      </div>

      {/* First Row: Languages / Companies */}
      <div className="container px-5 pt-16 mx-auto flex flex-wrap justify-center gap-y-16">
        {/* Languages Section */}
        <div className="p-6 md:w-1/2 w-full flex flex-col items-center text-center">
          <h2 className="text-2xl font-semibold title-font mb-3">Languages</h2>
          <Link to={languages} className="btn-black py-2 px-6 mb-4">Try Now</Link>
          <p className="text-xl text-white font-bold"></p>
        </div>

        {/* Companies Section */}
        <div className="p-6 md:w-1/2 w-full flex flex-col items-center text-center">
          <h2 className="text-2xl font-semibold title-font mb-3">Companies</h2>
          <Link to={companies} className="btn-black py-2 px-6 mb-4">Try Now</Link>
          
        </div>
      </div>

      {/* Spacer between rows */}
      <div className="my-12" />

      {/* Second Row: (if more features are needed, example below) */}
      <div className="container px-5 pb-16 mx-auto flex flex-wrap justify-center gap-y-16">
        {/* Optional additional block */}
        <div className="p-6 md:w-1/2 w-full flex flex-col items-center text-center">
          <h2 className="text-2xl font-semibold title-font mb-3">Model Leaderboard</h2>
          <Link to={companies} className="btn-black py-2 px-6 mb-4">Try Now</Link>
         
        </div>

        <div className="p-6 md:w-1/2 w-full flex flex-col items-center text-center">
          <h2 className="text-2xl font-semibold title-font mb-3">Evaluation Leaderboard</h2>
          <Link to={evaluations} className="btn-black py-2 px-6 mb-4">Try Now</Link>

          
        </div>
      </div>
    </section>
  );
};

export default ChatbotLanding;
