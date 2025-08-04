import SideNavBar from "../landing_page_components/SideNavBar";

function FAQs() {
  const entries = [
    "What is Panacea?",
    "What problem are you solving?",
    "How does Panacea work?",
    "How is it Private?",
    "What tasks does Panacea support?",
    "How do you mitigate hallucinations?",
  ];
  const title = "FAQs";

  return (
    <div className="bg-[#141414]">
      <SideNavBar title={title} entries={entries} />
      <div className="w-4/5 mx-auto md:w-7/12 md:ml-20 lg:ml-36 pt-12 lg:pt-20">
        <div className="pt-14">
          <h2 className="text-2xl lg:text-4xl font-['Helvetica_Neue'] font-semibold lg:font-bold text-white">
            Frequently Asked Questions
          </h2>

          {/* What is Panacea? */}
          <h2
            className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent text-2xl lg:text-2xl mb-4 font-['Helvetica_Neue'] Applications-Header"
            id="WhatisPanacea"
          >
            What is Panacea?
          </h2>
          <p className="text-white font-['Helvetica_Neue'] text-xl leading-relaxed mb-6">
            Panacea is a platform for building autonomous agentic systems. Use Panacea to:
            <br /><br />
            - <span className="font-bold">Build Agents with memory, tools, and reasoning</span> for state management and task handling.
            <br />
            - <span className="font-bold">Engage with Agents</span> using a user-friendly interface for local execution and session control.
            <br />
            - <span className="font-bold">Coordinate Teams</span> of agents for seamless collaboration and task handoff.
            <br />
            - <span className="font-bold">Monitor and optimize Agent performance</span> with tracking metrics and logs.
            <br />
            - <span className="font-bold">Integrate with local and cloud infrastructure</span> to support APIs and databases.
          </p>

          <hr className="h-px mt-10 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] border-0 mx-auto" />

          {/* What problem are you solving? */}
          <h2
            className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent text-2xl lg:text-2xl mb-4 font-['Helvetica_Neue'] Applications-Header"
            id="Whatproblemareyousolving"
          >
            What problem are you solving?
          </h2>
          <p className="text-white font-['Helvetica_Neue'] text-xl leading-relaxed mb-6">
            Organizations need scalable, secure, and autonomous systems to handle complex workflows and data management. Traditional AI systems struggle to coordinate multiple tasks autonomously, limiting their potential. Panacea solves this by enabling robust autonomous agents that can operate independently, collaborate, and manage private data securely within a controlled environment.
          </p>

          <hr className="h-px mt-10 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] border-0 mx-auto" />

          {/* How does Panacea work? */}
          <h2
            className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent text-2xl lg:text-2xl mb-4 font-['Helvetica_Neue'] Applications-Header"
            id="HowdoesPanaceawork"
          >
            How does Panacea work?
          </h2>
          <p className="text-white font-['Helvetica_Neue'] text-xl leading-relaxed mb-6">
            Panacea enables agents with defined roles in a multi-agent environment. Key components include:
            <br /><br />
            - <span className="font-bold">Interface:</span> Human-facing input for task assignment.
            <br />
            - <span className="font-bold">Node:</span> An individual agent within the system.
            <br />
            - <span className="font-bold">Edges:</span> Communication links between agents.
            <br />
            - <span className="font-bold">Orchestrator:</span> Manages task distribution and agent coordination.
          </p>

          <hr className="h-px mt-10 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] border-0 mx-auto" />

          {/* How is it Private? */}
          <h2
            className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent text-2xl lg:text-2xl mb-4 font-['Helvetica_Neue'] Applications-Header"
            id="HowisitPrivate"
          >
            How does Panacea ensure privacy when agents collaborate?
          </h2>
          <p className="text-white font-['Helvetica_Neue'] text-xl leading-relaxed mb-6">
          Panacea is built with privacy in mind. It enables on-premises deployment and private cloud options, ensuring that all agent activities and data remain within a secure environment. Agents can operate on sensitive data without external exposure, complying with strict security standards to protect your organization’s information.
          </p>

          <hr className="h-px mt-10 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] border-0 mx-auto" />

          {/* What tasks does Panacea support? */}
          <h2
            className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent text-2xl lg:text-2xl mb-4 font-['Helvetica_Neue'] Applications-Header"
            id="WhattasksdoesPanaceasupport"
          >
            What kinds of collaborative tasks can Panacea agents perform?
          </h2>
          <p className="text-white font-['Helvetica_Neue'] text-xl leading-relaxed mb-6">
          Panacea supports agents across a variety of industries, each with the ability to work collaboratively on tasks such as:
            <br /><br />
            - <span className="font-bold">Document Analysis and Summarization:</span> Agents can collectively analyze, summarize, and extract insights from large volumes of documents.
            <br />
            - <span className="font-bold">Data Integration and Processing:</span> Multiple agents can work together to process and synthesize data from different sources, such as financial reports, healthcare data, and customer inquiries.
            <br />
            - <span className="font-bold">Project Management:</span> Agents assist in planning, tracking, and coordinating project workflows, ensuring efficient teamwork across tasks.
            <br />
            - <span className="font-bold">Customer and Technical Support:</span> Agents can collaboratively handle complex customer inquiries, with each agent contributing specialized knowledge.
          </p>

          <hr className="h-px mt-10 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] border-0 mx-auto" />

          {/* How do you mitigate hallucinations? */}
          <h2
            className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent text-2xl lg:text-2xl mb-4 font-['Helvetica_Neue'] Applications-Header"
            id="Howdoyoumitigatehallucinations"
          >
            How can Panacea agents adapt to new tasks and environments?
          </h2>
          <p className="text-white font-['Helvetica_Neue'] text-xl leading-relaxed mb-6">
          Panacea’s agents are built to be flexible and adaptive. The platform allows agents to learn from past interactions, store relevant knowledge, and incorporate new tools as needed. With each task, agents update their capabilities and adjust workflows to better meet the unique demands of your organization’s evolving environment.
          </p>

        </div>
      </div>
    </div>
  );
}

export default FAQs;
