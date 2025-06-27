import React from 'react';

const BusinessModel = () => {
  return (
    <div style={{"margin-top": "80px", "margin-left": "10%"}}>
    <h2 className="FAQ-Header">Business Model</h2>
    <ul className="EllipseList" style={{"listStyle": "none"}}>
      <li>
        <h5 className="FAQ-Paragraph-Ellipse"><span id="neon-yellow-span">&#9679;</span>Charge Per Use Case - One means of obtaining revenue is to charge businesses a fixed price per use cases specific task. For instance, for Text classification for Financial Documents, you could charge $X for Y rows of text data. Assuming you charge $1 per row of annotated financial document text classification data, if you annotated $10M rows of that would amount to $10M in ROI.
        As far as the unit economics behind this business model: <br></br>
        - Total Gain = Cost Per Annotating Row of Data x Number of Rows in Dataset  <br></br>
- Total Loss = Cost of Manual Annotators + Cost of Subject Matter Experts + Technical Cost Per Project + Training Cost + Reviewer Cost + Staffing Cost
<br></br> <br></br>
What we have seen on the market is that many businesses charge cheaper annotation costs per row of data than is economically sustainable in order to attempt to get a higher market share.
Some businesses charge expensive costs per row of data, sacrificing market share.
        </h5>
        </li>
        <li>
        <h5 className="FAQ-Paragraph-Ellipse"><span id="white-span">&#9679;</span>Selling High Quality Labeled Datasets - Annotate datasets of unstructured text data that could not be analyzed before, and sell these proprietary, static datasets as IP to companies.
Assuming you sell each dataset at an average cost of $25,000, if you were able to license out 40,000 datasets, that would be the equivalent of $1B ROI.

On our product, we have a dataset hub, where you can view these "locked datasets" and analyze their schema / content. At any time, you can purchase these static datasets at a fixed cost per dataset.

On Anote, annotate a fixed number (1000) rows of these datasets for free. At this point, data annotators have to option to keep labeling at a variable price per annotation.</h5>
        </li>
        <li>
          <h5 className="FAQ-Paragraph-Ellipse"><span id="pink-span">&#9679;</span>Identifying and Fixing Mislabels in Structured, Tabular Datasets - Even the datasets that are "benchmarks" for many AI/ML problems are riddled with label errors. We could charge companies a fixed price to clean mislabels in datasets: Sentiment Analysis - $X for Y rows of Amazon Reviews.</h5>
        </li>
        <li>
          <h5 className="FAQ-Paragraph-Ellipse"><span id="green-span">&#9679;</span>Freemium model for domain specific modeling services - We can provide our few shot learning models which get users 80% there for free for free, and can charge for our domain specific modeling capabilities which handle edge cases in data labeling (the last 20%). We can charge a per month payment of ~$50 for access to these domain specific models, as part of a freemium version of our product.</h5>
        </li>
        </ul>
        </div>
  )};

  export default BusinessModel;