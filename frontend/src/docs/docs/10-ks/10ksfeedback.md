<!-- For this example, we'll refer to John, a financial analyst tasked with analyzing 10-K documents for a major corporation. John's goal was to extract key insights from these documents to assess the company's financial health and make informed investment recommendation. To tackle this project, John needed to develop a system that could automatically process and extract relevant information from a large number (millions) of 10-K documents. Let's say John's first financial document is Apple's 10-K.

<center>
<img src="../assets/private_gpt_interface_2.png" alt="Q&A Example" width="700px" />
</center>

John can initiate a chat session with the document, using his own set of questions or a predefined template. In this example, he will utilize a set of essential questions typically asked when analyzing financial documents. -->

## Prompt Inventory and Human Adjustment

When dealing with domain-specific documents, such as financial statements, the language model may sometimes provide incorrect or inaccurate answers for specific questions. For instance, when you ask about the major drivers of revenue and profit growth or decline, you may find the model's response to be too general, lacking specific information from the company's financial statements.

<center>
<img src="../assets/10K_example_1.png" width="700px" />
</center>

To address this issue and improve the accuracy of responses, we offer user-specific prompt inventories. This means that you can create and store all the relevant questions related to financial documents in your own inventories. For example, you can modify the query to be more specific, such as asking about the major drivers of revenue and profit growth or decline for a particular company. This approach helps to enhance the precision and relevance of the model's responses, enabling you to obtain more specific and insightful information from the financial statements.

Let's revise this question and add more content specific prompt: What are the major drivers of revenue and profit growth or decline of **this company**?

<center>
<img src="../assets/user_prompting_inventory.jpg" alt="Q&A Example" width="700px" />
</center>


As we can see, the revised response provides more direct and relevant information tailored to the specific company.

| Query | Response |
| --- | --- |
|What are the major drivers of revenue and profit growth or decline of **this company**? |  Major drivers of revenue and profit growth or decline of this company include seasonal holiday demand, new product and service introductions, demand for a single product, competitive global markets, economic conditions, and product pricing pressures.

Once you have a prompt that returns the best answer, you can update, delete, or add new prompts to your prompt inventories. This functionality allows you to conveniently manage and organize your prompt inventories, making it easy to access relevant materials and quickly retrieve queries that yield the best results. These capabilities save time and increase productivity in analyzing domain-specific documents.

As you refine your prompt inventories, you can now apply your best prompts to completely new documents. In the following examples, you apply your improved prompt inventories to analyze Apple's financial document using enhanced prompts:

| Query | Response |
| --- | --- |
| How does the company generate its revenue? What are its main products or services? | The Company generates its revenue by selling its own products and services, as well as reselling third-party products, directly to consumers, small and mid-sized businesses, and education, enterprise and government customers through its retail and online stores and its direct sales force. Its main products and services include electronic devices and media content. |
| Does the company operate in multiple geographic regions or industries? | Yes, the company operates in multiple geographic regions, including the Americas, Europe, Greater China, Japan, and Rest of Asia Pacific. |
| Are there any significant changes or developments in the company's business model, strategy, or competitive landscape? | Yes, the company is subject to rapid change and the development of new business models and the entry of new and well-funded competitors. |
| What were the company's revenues and net income for the past few years, and how have they changed over time? | The company's revenues for 2020, 2021, and 2022 were $48.7 billion, $67.1 billion, and $48.7 billion respectively. The company's net income for 2020, 2021, and 2022 were $91.2 million, $108.9 million, and $119.4 million respectively. The company's revenues and net income have increased over time. |
| What are the major drivers of revenue and profit growth or decline of this company? | Major drivers of revenue and profit growth or decline of this company include seasonal holiday demand, new product and service introductions, demand for a single product, competitive global markets, economic conditions, and product pricing pressures. |
| Are there any significant trends or patterns in the company's financial statements? | It is not possible to answer this question without reviewing the financial statements. |
| Who are the company's key executives and board members? What is their experience and track record? | The company's key executives and board members are Jeffrey P. Bezos (Executive Chair), Andrew R. Jassy (President and Chief Executive Officer), Douglas J. Herrington (CEO Worldwide Amazon Stores), Keith B. Alexander (CEO, President, and Chair of IronNet, Inc.), Edith W. Cooper (Former Executive Vice President, Goldman Sachs Group, Inc.), Jamie S. Gorelick (Partner, Wilmer Cutler Pickering Hale and Dorr LLP), Daniel P. Huttenlocher (Dean, MIT Schwarzman College of Computing), Judith A. McGrath (Former Chair and CEO, MTV Networks), Indra K. Nooyi (Former Chief Executive Officer, PepsiCo, Inc.), Jonathan J. Rubinstein (Former co-CEO, Bridgewater Associates, LP), Patricia Q. Stonesifer (Former President and Chief Executive Officer, Martha's Table), and Wendell P. Weeks (Chief Executive Officer, Corning Incorporated). Their experience and track record can be found in the company's SEC filings. |
| Are there any related-party transactions or potential conflicts of interest? | No, there are no related-party transactions or potential conflicts of interest mentioned in the context. |
| Does the company have effective internal controls and risk management procedures in place? | It is not possible to answer this question definitively based on the given context. The context indicates that the company has internal controls and risk management procedures in place, but it is not clear if they are effective. |
| What is the company's overall financial health, including its liquidity, solvency, and capital structure? | It is difficult to say without more information. The context provided suggests that the company is exposed to a variety of risks that could affect its financial health, including changes in liquidity, credit deterioration, market and economic conditions, political risk, sovereign risk, and interest rate fluctuations. Additionally, the company has been adversely affected by the COVID-19 pandemic, which could have further impacts on its business, results of operations, financial condition, and stock price. |
| How much debt does the company have, and what are the terms and conditions? | The company has outstanding fixed-rate notes with varying maturities for an aggregate principal amount of 67,651 as of September 24, 2022, and 72,968 as of September 25, 2021. The notes are senior unsecured obligations and interest is payable in arrears. |
| Are there any contingent liabilities or off-balance-sheet arrangements that could impact the company's financial position? | Yes, there are commitments and contingencies mentioned in the context that could impact the company's financial position. |


Once you're finished, you can easily download the resulting CSV file. Here's an excerpt of the actual result from the Apple Financial Statement chat. Please note that the displayed content has been truncated for brevity, but it provides a glimpse of the valuable information available to you.

| Query | Response | Source Document | Source Content |
| --- | --- | --- | --- |
| How does the company generate its revenue? What are its main products or services? | The Company generates its revenue by selling its own products and services, as well as reselling third-party products, directly to consumers, small and mid-sized businesses, and education, ... | source_documents\aapl-10-k.pdf | "The Company distributes its products and certain of its services through cellular network carriers, wholesalers, retailers and resellers, many of which distribute products and services from competitors ... "|
| Does the company operate in multiple geographic regions or industries? | Yes, the company operates in multiple geographic regions, including the Americas, Europe, Greater China, Japan, and Rest of Asia Pacific. | source_documents\aapl-10-k.pdf | "The Company manages its business primarily on a geographic basis. The Company's reportable segments consist of the Americas, Europe, Greater China, Japan and Rest of Asia Pacific. Americas includes both North and South America. Europe includes European countries ..." |