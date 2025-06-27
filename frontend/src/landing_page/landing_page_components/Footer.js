import React from "react";
import { Link } from "react-router-dom";

function Footer() {
  return (
    <footer className="text-gray-200 bg-[#141414]
">
      <div className="container px-5 py-24 mx-auto flex md:items-center lg:items-start md:flex-row md:flex-nowrap flex-wrap flex-col">
        <div className="md:w-1/12 lg:w-1/6 flex-shrink-0 md:mx-0 mx-auto text-center md:text-left">
          <nav className="list-none mb-10">
            <li className="mb-3">
              <a className="flex title-font font-medium items-center md:justify-start justify-center text-gray-900">
                <img
                  src="/logo.png"
                  alt="logo"
                  className="h-10 w-10"
                  loading="lazy"
                />
                <span className=" text-2xl text-white font-semibold font-['Helvetica_Neue']">
                  Anote
                </span>
              </a>
            </li>
            <li className="mb-3">
              {" "}
              <a
                className="mt-2 text-sm text-anoteblack-100 hover:text-turquoise-300 hover:cursor-pointer"
                href="https://docs.anote.ai/anew/anotecentricai.html"
                target="_blank"
              >
                Human Centered AI
              </a>
            </li>
            <li className="mb-3">
              <a
                className="mt-2 text-sm text-anoteblack-100 hover:text-turquoise-300 hover:cursor-pointer"
                href={"mailto:nvidra@anote.ai"}
                target="_blank"
              >
                nvidra@anote.ai
              </a>
            </li>
          </nav>
        </div>
        <div className="flex-grow flex flex-wrap md:pl-20 -mb-10 md:mt-0 mt-10 md:text-left text-center">
          <div className="lg:w-1/5 md:w-1/2 w-full px-4">
            <h2 className="font-medium text-yellow-500 text-base lg:text-xl mb-3 font-['Helvetica_Neue']">
              Products
            </h2>
            <nav className="list-none mb-10">
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] +
                        "/labels#Classify"
                    )
                  }
                >
                  Data Labeler
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    // window.location.assign(
                    //   window.location["origin"] + "/privategpt#Private Chatbot"
                    // )
                    window.location.assign(
                      window.location["origin"] + "/privategpt#Build"
                    )
                  }
                >
                  {/* Private Chatbot*/}
                  Panacea
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  // href="https://docs.anote.ai/api/anoteapi.html"
                  // target="_blank"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/modelinference#Hallucinate"
                    )
                  }
                >
                  {/* APIs */}
                  Model Inference
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  href="https://upreach.ai"
                  target="_blank"
                >
                  Upreach
                </a>
              </li>
              {/* <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  href="https://nwsltr.ai"
                  target="_blank"
                >
                  AI Newsletter
                </a>
              </li> */}
            </nav>
          </div>
          <div className="lg:w-1/5 md:w-1/2 w-full px-4">
            <h2
              style={{ fontFamily: "Helvetica Neue" }}
              className="font-medium text-yellow-500 text-base lg:text-xl mb-3"
            >
              Industries
            </h2>
            <nav className="list-none mb-10">
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/Industries#Finance"
                    )
                  }
                >
                  Finance
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/Industries#Healthcare"
                    )
                  }
                >
                  Healthcare
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/Industries#LegalTech"
                    )
                  }
                >
                  Legal
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/Industries#NonProfit"
                    )
                  }
                >
                  Non Profit
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/Industries#Research"
                    )
                  }
                >
                  Research
                </a>
              </li>
            </nav>
          </div>
          <div className="lg:w-1/5 md:w-1/2 w-full px-4">
            <h2
              style={{ fontFamily: "Helvetica Neue" }}
              className="font-medium text-yellow-500 text-base lg:text-xl mb-3"
            >
              Technology
            </h2>
            <nav className="list-none mb-10 ">
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  href="https://docs.anote.ai/active/classification.html"
                  target="_blank"
                >
                  Text Classification
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  href="https://docs.anote.ai/ner/namedentityrecognition.html"
                  target="_blank"
                >
                  Named Entity Recognition
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  href="https://docs.anote.ai/prompting/questionanswering.html"
                  target="_blank"
                >
                  Question and Answering
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  href="https://docs.anote.ai/structured/identifying.html"
                  target="_blank"
                >
                  Data Validation
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  href="https://docs.anote.ai/fewshot/fewshotlearning.html"
                  target="_blank"
                >
                  Few Shot Learning
                </a>
              </li>
            </nav>
          </div>
          <div className="lg:w-1/5 md:w-1/2 w-full px-4">
            <h2
              style={{ fontFamily: "Helvetica Neue" }}
              className="font-medium text-yellow-500 text-base lg:text-xl mb-3"
            >
              Case Studies
            </h2>
            <nav className="list-none mb-10">
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/CaseStudies#OpenAds"
                    )
                  }
                >
                  OpenAds
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] +
                        "/CaseStudies#Harvard Medical School"
                    )
                  }
                >
                  Harvard Med
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/CaseStudies#Abstractive Health"
                    )
                  }
                >
                  Abstractive Health
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/CaseStudies#Hardy Riggings"
                    )
                  }
                >
                  Hardy Riggings
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/CaseStudies#MPressed"
                    )
                  }
                >
                  MPressed
                </a>
              </li>
            </nav>
          </div>
          <div className="lg:w-1/5 md:w-1/2 w-full px-4">
            <h2
              style={{ fontFamily: "Helvetica Neue" }}
              className="font-medium text-yellow-500 text-base lg:text-xl mb-3"
            >
              Company
            </h2>
            <nav className="list-none mb-10">
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  href="https://anote-ai.medium.com/"
                  target="_blank"
                >
                  Blog
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/faqs#FAQs"
                    )
                  }
                >
                  Labeling FAQs
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  href="https://www.youtube.com/watch?v=7I_pBLjMNzs"
                  target="_blank"
                >
                  Press
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/contact#Contact"
                    )
                  }
                >
                  Contact
                </a>
              </li>
              <li className="mb-3">
                <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/careers#Careers"
                    )
                  }
                >
                  Careers
                </a>
              </li>
            </nav>
          </div>
        </div>
      </div>
      <div className="bg-[#141414]
">
        <div className="container mx-auto py-4 px-5 flex flex-wrap flex-col sm:flex-row">
          <p className="text-anoteblack-100 text-sm text-center sm:text-left">
            © 2023 Anote —
            <a
              href="https://twitter.com/knyttneve"
              rel="noopener noreferrer"
              className="text-anoteblack-100 ml-1"
              target="_blank"
            >
              All rights reserved -
            </a>
          <span className="px-400">
          <a
                  className="text-gray-300 hover:text-turquoise-300 hover:cursor-pointer"
                  onClick={() =>
                    window.location.assign(
                      window.location["origin"] + "/privacypolicy#Privacy Policy"
                    )
                  }
                >
                    - Privacy Policy
                </a>
                </span>
          </p>
          <span className="inline-flex sm:ml-auto sm:mt-0 mt-2 justify-center sm:justify-start">
            <a
              className="text-anoteblack-100 cursor-pointer"
              href="https://anote-ai.medium.com/"
              target="_blank"
            >
              <img
                className="w-5 h-5"
                src="/landing_page_assets/social/medium.svg"
                loading="lazy"
              />
            </a>
            <a
              className="ml-3 text-anoteblack-100 cursor-pointer"
              href="https://www.linkedin.com/company/anote-ai"
              target="_blank"
            >
              <svg
                fill="currentColor"
                stroke="currentColor"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="0"
                className="w-5 h-5"
                viewBox="0 0 24 24"
              >
                <path
                  stroke="none"
                  d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z"
                ></path>
                <circle cx="4" cy="4" r="2" stroke="none"></circle>
              </svg>
            </a>
          </span>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
