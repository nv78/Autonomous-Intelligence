import React from "react";

const Ellipse = () => {
  return (
    <div style={{ "margin-top": "80px", "margin-left": "10%" }}>
      <h2 className="FAQ-Header">Market Opportunity</h2>
      <div>
        <svg class="ellipse-container" width="70%" height="400px">
          <rect id="square" x="0" y="0" width="70%" height="100%" />
          <ellipse id="white-ellipse" cx="50%" cy="50%" rx="49%" ry="49%" />
          <ellipse id="pink-ellipse" cx="50%" cy="50%" rx="47%" ry="47%" />
          <ellipse id="green-ellipse" cx="50%" cy="50%" rx="44.5%" ry="44.5%" />
          <ellipse
            id="light-purple-ellipse"
            cx="50%"
            cy="50%"
            rx="42%"
            ry="42%"
          />
          <ellipse
            id="light-blue-ellipse"
            cx="50%"
            cy="50%"
            rx="38%"
            ry="38%"
          />
          <ellipse id="yellow-ellipse" cx="50%" cy="50%" rx="34%" ry="34%" />
          <ellipse id="gray-ellipse" cx="50%" cy="50%" rx="31%" ry="31%" />
          <ellipse id="indigo-ellipse" cx="50%" cy="50%" rx="18%" ry="18%" />
          <ellipse id="red-ellipse" cx="50%" cy="50%" rx="8%" ry="8%" />
          <ellipse id="orange-ellipse" cx="50%" cy="50%" rx="6%" ry="6%" />
          <ellipse id="light-pink-ellipse" cx="50%" cy="50%" rx="2%" ry="2%" />
          <ellipse id="blue-ellipse" cx="50%" cy="50%" rx=".5%" ry=".5%" />
        </svg>
      </div>
      <ul className="EllipseList" style={{ listStyle: "none" }}>
        <li>
          <span id="neon-yellow-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            The massive market (TAM) for Artificial Intelligence is $87.4B. This
            market is growing at a CAGR of 38.1% to reach a projected 1,597B by
            2030, and will continue to expand with the advent of Generative AI{" "}
          </h5>
        </li>
        <li>
          <span id="white-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            The ever-growing universe of data out there. Data is the fuel that
            powers AI, and is an essential component to the massive market of
            AI. This data is largely unlabeled, and not in a usable state.
          </h5>
        </li>
        <li>
          <span id="pink-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            100% - The data that businesses care about. This data is required to
            be labeled for nearly all AI, machine learning and data analytics
            projects. AI and Machine learning is pervading across all
            industries, changing the way things are done.
          </h5>
        </li>
        <li>
          <span id="green-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            90% - The percentage of AI projects that fail (Gartner). A large
            reason these projects fail is due to a lack of high quality, labeled
            training data to successfully complete AI projects.
          </h5>
        </li>
        <li>
          <span id="light-purple-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            87.5% - The percentage of data that is text data in businesses, as
            opposed to images, audio, video, etc. These can in the format of
            PDFs, Documents, Powerpoints, Emails, Conversations, Websites or
            Social Media Posts, and are usually of the unstructured format{" "}
          </h5>
        </li>
        <li>
          <span id="light-blue-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            85% - The percentage of data that is unstructured, unlabeled and not
            ready to use. This corresponds to just 20% of the revenue in the AI
            market
          </h5>
        </li>
        <li>
          <span id="yellow-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            80% - The percentage of data annotations are still being done
            manually, as compared to AI-based data annotations (Grand View
            Research). Manually labeling data is a massive undertaking. For many
            tasks, there are teams of hundreds of data annotators labeling
            millions of rows of data, each defined by a set of language
            criteria, including rules, key words and entities. These training
            datasets are tedious, costly, and time consuming to manually label,
            especially in industries where data is private.
          </h5>
        </li>
        <li>
          <span id="gray-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            75% - The percentage of time that Data Scientists spend curating,
            cleaning, preprocessing and labeling their datasets, while only
            spending 25% of their time building ML models. Oftentimes, the
            entire data annotation process falls on their shoulders.
          </h5>
        </li>
        <li>
          <span id="indigo-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            35% - The percentage of ROI that text labeling generates today, as
            opposed to image and audio data. Text data generates the highest
            ROI.
          </h5>
        </li>
        <li>
          <span id="red-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            15% - The percentage of data that is structured. Though small, this
            corresponds to over 80% of the revenue in the AI market
          </h5>
        </li>
        <li>
          <span id="orange-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            10% - The percentage of structured data that has label errors. Most
            AI models score ~10-15% below their potential accuracy due to these
            label errors pervading even the most high quality, benchmark
            datasets out there.
          </h5>
        </li>
        <li>
          <span id="light-pink-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            5% - The percentage of labeling tasks that are actually able to be
            done by existing companies today via AI, rather than a manual
            approach. The data labeling process is very complex and often
            extremely customizable to each use case.
          </h5>
        </li>
        <li>
          <span id="blue-span" className="span-style">
            &#9679;
          </span>
          <h5 className="FAQ-Paragraph-Ellipse mt-11">
            .001% - The amount of data that businesses require to be labeled
            that is currently labeled today. Getting High Quality, Labeled data
            is the biggest blocker to successful AI development. Right now, as
            Carl Sagan would say, we are just a pale blue dot.
          </h5>
        </li>
      </ul>
    </div>
  );
};

export default Ellipse;
