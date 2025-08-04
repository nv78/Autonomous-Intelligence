import React from "react";

const Research = () => {
  return (
    <div className="text-white max-w-screen">
      <div className="flex flex-col text-center w-full mt-6">
          <h1 className="sm:text-4xl text-3xl font-medium title-font text-gray-100">
            Generative AI Research in Finance
          </h1>
        </div>
        <div className="w-full md:w-3/4 mx-auto mt-14">
          <div className="flex flex-col-reverse md:flex-row items-center">
            <div className="px-10 order-2 md:order-1 mb-5">
            <div className="text-2xl font-semibold py-5">
              Improving Retrieval for Financial LLMs
            </div>
            <div className="text-lg">
              More accurate retrieval of chunks of text within documents, for improved citations and enhanced model responses
              <br></br>
              <br></br>
              <strong>Models Covered:</strong> Recursive Chunking, FLARE, Query Expansions, Metadata Filtering, Reranking Algorithms, HyDE
              </div>
              <div className="my-4">
              <button
                className="btn-yellow"
                onClick={() => {
                  window.open("https://arxiv.org/abs/2404.07221", "_blank");
                }}
                style={{ marginTop: "20px", textDecoration: "none" }}
              >
                View Research Paper
              </button>
            </div>
            </div>
            <img
              src="/landing_page_assets/retrieval-new.png"
              className="order-1 md:order-2 w-11/12 md:w-2/3 rounded-xl border-1 border-white"
            ></img>

          </div>
        </div>

        <div className="w-full md:w-3/4 mx-auto my-10 mt-20">
          <div className="flex flex-col-reverse md:flex-row items-center">
            <img
                src="/landing_page_assets/qa-new.png"
                className="w-11/12 md:w-2/3 rounded-xl border-1 border-white"
            ></img>
            <div className="px-10 mb-5">
              <div className="text-2xl font-semibold py-5">
                Benchmarking for Question Answering
              </div>
              <div className="text-lg">
                More Accurate, Domain Specific and Reliable Answers to Questions in the Financial Domain
                <br></br>
                <br></br>
                <strong>Models Benchmarked:</strong> GPT-4, Claude, GPT4All, Llama2<br></br>
                <strong>Datasets Benchmarked:</strong> FinanceBench, Rag Instruct<br></br>
            </div>
            <div className="my-4">
              <button
                className="btn-yellow"
                onClick={() => {
                  window.open("https://arxiv.org/abs/2402.01722", "_blank");
                }}
                style={{ marginTop: "20px", textDecoration: "none" }}
              >
                View Research Paper
              </button>
            </div>
          </div>
        </div>
        </div>
    </div>
    );
  }

export default Research;
