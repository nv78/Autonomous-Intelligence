import React from "react";

const Languages = () => {
  return (
    <section className="min-h-screen text-gray-100 body-font overflow-hidden">
      {/* Title */}
      <div className="flex flex-col text-center w-full mt-10">
        <h1 className="sm:text-5xl text-4xl font-extrabold title-font bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent w-fit mx-auto px-4 py-2">
          Languages
        </h1>
        <p className="text-sm text-gray-400 mt-4 max-w-xl mx-auto">
          Explore our multilingual models across various tasks and evaluations. Choose a language to see detailed benchmarks and model performance.
        </p>
      </div>

      {/* Language Options */}
      <div className="container px-5 py-20 mx-auto flex flex-wrap justify-center gap-12">
        {/* Example Language Card */}
        {["English", "Spanish", "French", "Chinese"].map((lang) => (
          <div
            key={lang}
            className="bg-gray-800 rounded-2xl p-6 w-72 text-center shadow-md hover:shadow-xl transition-shadow"
          >
            <h2 className="text-xl font-semibold mb-2">{lang}</h2>
            <p className="text-gray-300 text-sm mb-4">
              Benchmarks, tasks, and model comparisons available.
            </p>
            <button className="btn-black py-2 px-6">Explore</button>
          </div>
        ))}
      </div>
    </section>
  );
};

export default Languages;
