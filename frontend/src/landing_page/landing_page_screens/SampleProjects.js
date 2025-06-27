import SampleProject from "../landing_page_components/SampleProject";
import "../landing_page_styles/LandingPageSampleProjects.css";

function SampleProjects() {

  // var subtitle4 = (
  //   <div>
  //     <h4 className="LP-TutorialSubTitle">
  //       Capability - Personalized On-Premise GPT Assistant
  //     </h4>
  //   </div>
  // );
  // var subheader4 = (
  //   <div>
  //     <h3 className="LP-TutorialSubHeader">
  //       Sector - AI-Powered Document Interactions
  //     </h3>
  //   </div>
  // );
  // var description4 = (
  //   <div>
  //     <h6 className="LP-TutorialText">
  //       Anote Private Chatbotis an advanced solution that allows enterprises to
  //       utilize generative AI while ensuring data privacy and security. Acting
  //       as a personalized AI assistant, Anote Private Chatbot becomes the chief
  //       artificial intelligence officer for organizations, providing valuable
  //       insights from their own data without compromising confidentiality.
  //       Members of the organization can interact with their documents through
  //       natural language queries, and the Private Chatbot system can promptly
  //       provide accurate and relevant responses, all while keeping the data
  //       local, on premise, and secure.
  //     </h6>
  //     <h6 className="LP-TutorialText">
  //       The key features of Anote Private Chatbotinclude operating entirely within
  //       the user's local environment, secure document storage in a Chroma vector
  //       store, privacy-preserving retrieval of documents, privacy-aware language
  //       models, and query-response privacy. By prioritizing user control and
  //       consent, Anote Private Chatbotensures that users have full authority over
  //       their documents and data, enabling them to manage interactions based on
  //       their preferences. With AnotePrivate Chatbot, enterprises can confidently
  //       leverage the power of AI for document interactions while maintaining
  //       complete control and security over their sensitive data.
  //     </h6>
  //   </div>
  // );

  return (
    <div className="LP-FAQs bg-[#141414]">
      <div className="FAQ ">
        <div class={"LP-Sample-Projects bg-[#141414]"}>
          <h1 className="mb-6 text-3xl text-center font-bold">
            Panacea Video Demo
          </h1>
          <div className="LP-Contact">
            <SampleProject
              // title={"Privacy Preserving LLMs"}
              // description={description4}
              // capability={subtitle4}
              // sector={subheader4}
              type={"Nonprofit - Text Classification"}
              videoUrl={"https://www.youtube.com/embed/SW6itfZ2nmg"}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default SampleProjects;
