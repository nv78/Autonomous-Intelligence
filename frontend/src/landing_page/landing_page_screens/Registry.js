// import React, { useState } from "react";

// function Registry() {
//   const [isModalOpen, setIsModalOpen] = useState(false);
//   const [selectedAgent, setSelectedAgent] = useState(null);

//   const agents = [
//     {
//       image: "/landing_page_assets/privatewhite.png",
//       title: "Upreach",
//       description: "Email Marketing Agent",
//       websiteLink: "https://agentwebsite.com/upreach",
//       details:
//         "Upreach is an advanced email marketing agent designed to streamline outreach and optimize email campaigns with AI-driven insights.",
//       features: ["Automated Campaigns", "Personalized Outreach", "Data Analytics"],
//       useCases: ["Lead Generation", "Customer Retention", "Campaign Performance Tracking"],
//       capabilities: "Upreach can send automated, personalized emails, track user engagement, and analyze campaign results to optimize future strategies.",
//     },
//     {
//       image: "/landing_page_assets/accuratewhite.png",
//       title: "Private Chatbot",
//       description: "Financial Analyst Agent",
//       websiteLink: "https://agentwebsite.com/privatechatbot",
//       details:
//         "Private Chatbot provides real-time financial insights, powered by AI to help you make data-driven decisions.",
//       features: ["Financial Data Analysis", "Real-Time Reporting", "Customizable Dashboards"],
//       useCases: ["Portfolio Analysis", "Market Trend Monitoring", "Risk Assessment"],
//       capabilities: "This agent can analyze financial reports, detect trends, and generate custom financial dashboards.",
//     },
//     {
//       image: "/landing_page_assets/accuratewhite.png",
//       title: "Anote",
//       description: "Data Labeler Agent",
//       websiteLink: "https://agentwebsite.com/anote",
//       details:
//         "Anote is a powerful data labeling agent that provides accurate and efficient annotation for machine learning datasets.",
//       features: ["Automated Labeling", "Quality Control", "Dataset Export"],
//       useCases: ["Image Annotation", "Text Labeling", "Entity Extraction"],
//       capabilities: "Anote supports multiple annotation formats and can handle large datasets efficiently with quality assurance features.",
//     },
//     {
//       image: "/landing_page_assets/citationswhite.png",
//       title: "AI-RFP",
//       description: "Grant Writer Agent",
//       websiteLink: "https://agentwebsite.com/ai-rfp",
//       details:
//         "AI-RFP assists with grant writing, helping you draft, review, and submit high-quality grant proposals efficiently.",
//       features: ["Automated Proposal Drafting", "Review Assistance", "Funding Source Analysis"],
//       useCases: ["Grant Application Preparation", "Funding Opportunity Research", "Proposal Quality Enhancement"],
//       capabilities: "AI-RFP streamlines the grant writing process by automating proposal drafts and assisting with funding source research.",
//     },
//     {
//       image: "/landing_page_assets/citationswhite.png",
//       title: "Autocode",
//       description: "Software Engineer Agent",
//       websiteLink: "https://agentwebsite.com/autocode",
//       details:
//         "Autocode is a software engineer agent that automates coding tasks, improves code quality, and assists with code reviews.",
//       features: ["Code Generation", "Automated Code Reviews", "Error Detection"],
//       useCases: ["Software Development Assistance", "Code Optimization", "Quality Assurance"],
//       capabilities: "Autocode can generate and review code, detect potential errors, and provide recommendations for optimization.",
//     },
//     {
//       image: "/landing_page_assets/citationswhite.png",
//       title: "Applico",
//       description: "Job Seeker Agent",
//       websiteLink: "https://agentwebsite.com/applico",
//       details:
//         "Applico is a job-seeker agent that helps you find job opportunities, prepare applications, and streamline the job search process.",
//       features: ["Job Search Optimization", "Application Tracking", "Resume and Cover Letter Assistance"],
//       useCases: ["Job Opportunity Discovery", "Application Management", "Personalized Job Recommendations"],
//       capabilities: "Applico aids in finding job listings, managing applications, and providing tailored job recommendations based on user profiles.",
//     },
//     {
//       image: "/landing_page_assets/citationswhite.png",
//       title: "MarketSense",
//       description: "Market Research Agent",
//       websiteLink: "https://agentwebsite.com/marketsense",
//       details:
//         "MarketSense is a market research agent that gathers, analyzes, and interprets market data to provide strategic insights.",
//       features: ["Competitor Analysis", "Trend Monitoring", "Consumer Insights"],
//       useCases: ["New Market Entry Analysis", "Product Development Insights", "Competitive Positioning"],
//       capabilities: "MarketSense collects and analyzes data to provide actionable insights on market trends, customer preferences, and competitor strategies.",
//     },
//     {
//       image: "/landing_page_assets/citationswhite.png",
//       title: "Assistly",
//       description: "Customer Support Agent",
//       websiteLink: "https://agentwebsite.com/assistly",
//       details:
//         "Assistly is a customer support agent that provides automated responses, tracks inquiries, and enhances customer satisfaction.",
//       features: ["Automated Responses", "Inquiry Tracking", "Personalized Support"],
//       useCases: ["Customer Service Automation", "Complaint Resolution", "Support Ticket Management"],
//       capabilities: "Assistly can handle customer inquiries, resolve complaints, and manage support tickets for streamlined customer service.",
//     },
//     {
//       image: "/landing_page_assets/citationswhite.png",
//       title: "TeamUp",
//       description: "Project Manager Agent",
//       websiteLink: "https://agentwebsite.com/teamup",
//       details:
//         "TeamUp is a project management agent that assists in task assignment, timeline tracking, and team coordination.",
//       features: ["Task Assignment", "Progress Tracking", "Team Collaboration"],
//       useCases: ["Project Planning", "Task Management", "Timeline Tracking"],
//       capabilities: "TeamUp enables teams to stay on track by assigning tasks, monitoring project timelines, and enhancing team collaboration.",
//     },
//   ];

//   const openModal = (agent) => {
//     setSelectedAgent(agent);
//     setIsModalOpen(true);
//   };

//   const closeModal = () => {
//     setSelectedAgent(null);
//     setIsModalOpen(false);
//   };

//   return (
//     <div className="mx-5 lg:mx-24 mt-24">
//       <div className="text-3xl sm:text-4xl lg:text-5xl my-10 text-center font-medium lg:font-bold text-white">
//         Agent Registry
//       </div>

//       <div className="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-3 gap-8 px-8">
//         {agents.map((agent, index) => (
//           <div
//             key={index}
//             className="bg-[#1a1a1a] rounded-lg shadow-lg p-6 flex flex-col items-center text-center text-white transition-transform transform hover:scale-105 cursor-pointer"
//             onClick={() => openModal(agent)}
//           >
//             <img src={agent.image} alt={agent.title} className="w-16 h-16 mb-4" />
//             <h3 className="text-xl font-semibold mb-2">{agent.title}</h3>
//             <p className="text-md mb-4">{agent.description}</p>
//             <button
//               className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-4 py-2 rounded-md font-semibold"
//             >
//               More Info
//             </button>
//           </div>
//         ))}
//       </div>

//       {isModalOpen && selectedAgent && (
//         <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-75 z-50">
//           <div className="bg-[#1a1a1a] w-11/12 md:w-3/4 lg:w-1/2 rounded-lg p-8 text-white relative max-h-screen overflow-y-auto">
//             <button
//               className="absolute top-2 right-2 text-2xl font-bold"
//               onClick={closeModal}
//             >
//               &times;
//             </button>
//             <h1 className="mx-auto mb-4 text-4xl font-bold "> {selectedAgent.title} </h1>
//             <hr className="h-px mb-4 bg-white border-0 mx-auto" />
//             <h2 className="text-2xl font-bold mb-4 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">About</h2>
//             <p className="text-lg mb-6">{selectedAgent.details}</p>

//             <div className="mb-6">
//               <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Features</h3>
//               <ul className="list-disc list-inside text-md space-y-2">
//                 {selectedAgent.features.map((feature, index) => (
//                   <li key={index}>{feature}</li>
//                 ))}
//               </ul>
//             </div>

//             <div className="mb-6">
//               <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Use Cases</h3>
//               <ul className="list-disc list-inside text-md space-y-2">
//                 {selectedAgent.useCases.map((useCase, index) => (
//                   <li key={index}>{useCase}</li>
//                 ))}
//               </ul>
//             </div>

//             <div className="mb-8">
//               <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Capabilities</h3>
//               <p className="text-md leading-relaxed">{selectedAgent.capabilities}</p>
//             </div>

//             <a
//               href={selectedAgent.websiteLink}
//               target="_blank"
//               rel="noopener noreferrer"
//               className="inline-block bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-4 py-2 rounded-md font-semibold mt-4"
//             >
//               Visit Website
//             </a>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }

// export default Registry;

import React, { useState } from "react";

function Registry() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);

  const agents = [
    {
      image: "/landing_page_assets/privatewhite.png",
      title: "Auto Follow-Up Buddy",
      subtitle: "Never forget to send a follow-up email again",
      description: "Upload your last email or meeting notes and this agent drafts a personalized, thoughtful follow-up. Suggests optimal timing and subject lines, integrates with Gmail for seamless sending. Great for networking, job hunting, and client management.",
      websiteLink: "https://agentwebsite.com/auto-followup-buddy",
      metrics: [
        "Follow-up email open rate",
        "Reply rate (%)",
        "Time saved vs manual drafting",
        "Number of follow-ups sent per session"
      ],
      features: ["Personalized Follow-ups", "Gmail Integration", "Optimal Timing", "Subject Line Optimization"],
      useCases: ["Networking", "Job Hunting", "Client Management", "Professional Communication"],
      capabilities: "Auto Follow-Up Buddy analyzes your previous communications and drafts contextually appropriate follow-up emails with optimal timing suggestions."
    },
    {
      image: "/landing_page_assets/accuratewhite.png",
      title: "LinkedIn Job Hunter Pro",
      subtitle: "Match your profile to jobs and message recruiters in one click",
      description: "Upload your resume or connect your LinkedIn. This agent scrapes job postings, tailors recruiter DMs, and even suggests edits to your profile for better keyword matches.",
      websiteLink: "https://agentwebsite.com/linkedin-job-hunter-pro",
      metrics: [
        "Number of tailored job matches found",
        "Recruiter response rate",
        "Accuracy of profile–job match",
        "Message clarity score (LLM-assessed)"
      ],
      features: ["Job Scraping", "Profile Optimization", "Recruiter DMs", "Keyword Matching"],
      useCases: ["Job Search", "Career Advancement", "Professional Networking", "Resume Optimization"],
      capabilities: "LinkedIn Job Hunter Pro automatically finds relevant job opportunities, optimizes your profile for better matches, and crafts personalized messages to recruiters."
    },
    {
      image: "/landing_page_assets/citationswhite.png",
      title: "Cold Outreach Designer",
      subtitle: "Create a mini email campaign from scratch",
      description: "Describe your product and target audience, and this agent generates 2–3 cold emails with compelling hooks and CTAs. Designed for startup founders, freelancers, and B2B marketers.",
      websiteLink: "https://agentwebsite.com/cold-outreach-designer",
      metrics: [
        "Click-through rate (CTR) of emails",
        "Open rate (%)",
        "Customization level (readability + tone match)",
        "Campaign creation speed"
      ],
      features: ["Compelling Hooks", "CTA Optimization", "Multi-email Campaigns", "Audience Targeting"],
      useCases: ["Startup Marketing", "Freelancer Outreach", "B2B Sales", "Lead Generation"],
      capabilities: "Cold Outreach Designer creates engaging email sequences with proven hooks and calls-to-action tailored to your specific product and target audience."
    },
    {
      image: "/landing_page_assets/privatewhite.png",
      title: "Instant ICP Analyzer",
      subtitle: "Find your Ideal Customer Profile based on your website or product",
      description: "Enter your startup's website, and the agent generates your likely ICPs: sectors, titles, firmographics, and even a target contact list suggestion. Ideal for new GTM teams.",
      websiteLink: "https://agentwebsite.com/instant-icp-analyzer",
      metrics: [
        "ICP match score (based on industry databases)",
        "Usefulness of contact suggestions",
        "Number of high-fit accounts identified",
        "User satisfaction score (from internal survey)"
      ],
      features: ["Website Analysis", "Firmographic Profiling", "Contact List Generation", "Sector Identification"],
      useCases: ["GTM Strategy", "Market Research", "Lead Generation", "Customer Segmentation"],
      capabilities: "Instant ICP Analyzer examines your website and product to identify ideal customer profiles with detailed firmographics and contact suggestions."
    },
    {
      image: "/landing_page_assets/accuratewhite.png",
      title: "Meeting-to-Newsletter Generator",
      subtitle: "Turn Zoom notes into a polished update for your audience",
      description: "Upload meeting transcripts or bullet notes. Agent turns it into a well-structured blog, newsletter, or memo with clear formatting and editable tone. Ideal for content creators, PMs, and founders.",
      websiteLink: "https://agentwebsite.com/meeting-to-newsletter",
      metrics: [
        "Quality of newsletter output (LLM grammar + coherence score)",
        "Time saved per newsletter",
        "Share rate or feedback from recipients",
        "Edit rate (how much user rewrites)"
      ],
      features: ["Transcript Processing", "Content Formatting", "Tone Customization", "Multi-format Output"],
      useCases: ["Content Creation", "Project Management", "Team Communication", "Stakeholder Updates"],
      capabilities: "Meeting-to-Newsletter Generator transforms raw meeting notes into professional newsletters, blogs, or memos with proper structure and tone."
    },
    {
      image: "/landing_page_assets/citationswhite.png",
      title: "Smart Newsletter Engine",
      subtitle: "Personalized newsletters tailored to each account",
      description: "Input your newsletter content (or let the agent generate it), and it dynamically personalizes sections based on the reader's company, industry, or behavior. Supports bulk sending with integrations for HubSpot, Mailchimp, and Gmail.",
      websiteLink: "https://agentwebsite.com/smart-newsletter-engine",
      metrics: [
        "Open rate (% personalized vs generic)",
        "Click-through rate (CTR)",
        "Time saved on newsletter creation",
        "Engagement by segment (account-level insights)"
      ],
      features: ["Dynamic Personalization", "Bulk Sending", "CRM Integration", "Behavioral Targeting"],
      useCases: ["Email Marketing", "Customer Engagement", "Account-Based Marketing", "Content Distribution"],
      capabilities: "Smart Newsletter Engine creates highly personalized newsletters that adapt content based on recipient data and behavior patterns."
    },
    {
      image: "/landing_page_assets/privatewhite.png",
      title: "Lead List Email Launcher",
      subtitle: "From CSV to inbox in a single flow",
      description: "Upload a lead list or CRM export. This agent enriches missing fields (like job title or company size), drafts personalized cold emails, and sends them via Gmail. Optional integration with MCP or outreach tools.",
      websiteLink: "https://agentwebsite.com/lead-list-email-launcher",
      metrics: [
        "Email delivery rate",
        "Enrichment accuracy",
        "Open/reply rate",
        "Time saved vs manual process"
      ],
      features: ["Data Enrichment", "Personalized Emails", "Gmail Integration", "Bulk Processing"],
      useCases: ["Sales Outreach", "Lead Generation", "CRM Management", "Cold Email Campaigns"],
      capabilities: "Lead List Email Launcher processes lead lists, enriches contact data, and executes personalized email campaigns with high deliverability."
    },
    {
      image: "/landing_page_assets/accuratewhite.png",
      title: "LinkedIn DM Sender",
      subtitle: "Ditch email — connect with leads where they live",
      description: "Paste a list of LinkedIn profiles or let the agent find them from your ICP. It crafts short, non-spammy messages, tailored to each lead's title and company. Works with tools like Sales Navigator or PhantomBuster.",
      websiteLink: "https://agentwebsite.com/linkedin-dm-sender",
      metrics: [
        "Connection acceptance rate",
        "Reply rate (% of messages)",
        "Message personalization quality",
        "LinkedIn flag rate (compliance/safety metric)"
      ],
      features: ["Profile Discovery", "Message Personalization", "Compliance Safety", "Integration Support"],
      useCases: ["Social Selling", "Professional Networking", "Lead Generation", "Relationship Building"],
      capabilities: "LinkedIn DM Sender creates personalized, compliant LinkedIn messages that build genuine professional connections without spamming."
    },
    {
      image: "/landing_page_assets/citationswhite.png",
      title: "ICP Contact Finder",
      subtitle: "Instantly generate leads that match your ideal customer profile",
      description: "Enter your company name, website, or product. This co-pilot determines your likely ICP, then finds and verifies up to 500 matching contacts from trusted databases. Filters by title, region, industry, and more.",
      websiteLink: "https://agentwebsite.com/icp-contact-finder",
      metrics: [
        "ICP fit score (relevance of returned contacts)",
        "Contact accuracy (bounce rate)",
        "Total high-quality leads generated",
        "Campaign impact (pipeline influenced)"
      ],
      features: ["Database Access", "Contact Verification", "Advanced Filtering", "ICP Matching"],
      useCases: ["Lead Generation", "Prospecting", "Market Expansion", "Sales Pipeline Building"],
      capabilities: "ICP Contact Finder identifies your ideal customer profile and generates verified contact lists with advanced filtering and matching capabilities."
    },
    {
      image: "/landing_page_assets/privatewhite.png",
      title: "One-Pager Builder Agent",
      subtitle: "Create a GTM-ready sales sheet in minutes",
      description: "Input your product description, key features, and audience. This agent auto-generates a slick, well-formatted one-pager for sales or fundraising—editable in Google Docs or Canva.",
      websiteLink: "https://agentwebsite.com/one-pager-builder",
      metrics: [
        "Visual and content quality (LLM + design score)",
        "Time saved per asset",
        "Team adoption rate",
        "Edit rate"
      ],
      features: ["Auto-formatting", "Design Templates", "Export Options", "Professional Layouts"],
      useCases: ["Sales Materials", "Fundraising", "Product Marketing", "Pitch Decks"],
      capabilities: "One-Pager Builder Agent creates professional sales and marketing materials with compelling design and content structure."
    },
    {
      image: "/landing_page_assets/accuratewhite.png",
      title: "Job Description Optimizer",
      subtitle: "Attract better talent with smarter listings",
      description: "Paste your draft JD or hiring goals. This agent rewrites for clarity, inclusiveness, and keyword optimization. Includes market compensation suggestions based on role and location.",
      websiteLink: "https://agentwebsite.com/job-description-optimizer",
      metrics: [
        "Job listing engagement (clicks + applies)",
        "Keyword density / SEO match",
        "Recruiter satisfaction",
        "Edit rate"
      ],
      features: ["Inclusive Language", "SEO Optimization", "Compensation Insights", "Clarity Enhancement"],
      useCases: ["Talent Acquisition", "HR Management", "Recruitment Marketing", "Diversity Hiring"],
      capabilities: "Job Description Optimizer enhances job listings for better candidate attraction with inclusive language and market-competitive positioning."
    },
    {
      image: "/landing_page_assets/citationswhite.png",
      title: "Zoom Background Generator",
      subtitle: "Make a custom AI-generated Zoom background to match your vibe",
      description: "Choose your mood (e.g. 'Tech Executive in Tokyo,' 'Cozy Writer in Paris,' 'Startup Jungle'), and this agent generates a stylized Zoom background you can download and use instantly.",
      websiteLink: "https://agentwebsite.com/zoom-background-generator",
      metrics: [
        "Download rate",
        "Background rating",
        "Reuse frequency",
        "Virality (posts/screenshots)"
      ],
      features: ["AI Generation", "Mood Customization", "Instant Download", "High Quality"],
      useCases: ["Professional Meetings", "Creative Expression", "Personal Branding", "Fun Content"],
      capabilities: "Zoom Background Generator creates personalized, professional or creative backgrounds that match your desired aesthetic and professional image."
    },
    {
      image: "/landing_page_assets/privatewhite.png",
      title: "Personal Brand Advisor",
      subtitle: "Find your niche and grow your audience faster",
      description: "This agent analyzes your past tweets, LinkedIn posts, or blog content, then suggests a unique angle or content niche that fits your voice and goals. Includes post ideas, hashtags, and tone optimization.",
      websiteLink: "https://agentwebsite.com/personal-brand-advisor",
      metrics: [
        "Engagement growth rate",
        "Audience fit score (LLM niche match)",
        "Post idea acceptance rate",
        "Time saved on content planning"
      ],
      features: ["Content Analysis", "Niche Discovery", "Hashtag Optimization", "Voice Matching"],
      useCases: ["Content Creation", "Social Media Growth", "Thought Leadership", "Professional Branding"],
      capabilities: "Personal Brand Advisor analyzes your existing content to identify your unique voice and suggests strategic content directions for audience growth."
    },
    {
      image: "/landing_page_assets/accuratewhite.png",
      title: "Meeting Bingo Card Maker",
      subtitle: "Turn your next meeting into a game",
      description: "Input your meeting type and common jargon or behaviors. This agent generates a Bingo card you can print or share — perfect for fighting meeting fatigue.",
      websiteLink: "https://agentwebsite.com/meeting-bingo-maker",
      metrics: [
        "Usage rate",
        "Share rate",
        "Meeting engagement score",
        "Repeat usage"
      ],
      features: ["Custom Cards", "Meeting Types", "Printable Format", "Shareable Design"],
      useCases: ["Team Building", "Meeting Engagement", "Corporate Culture", "Fun Activities"],
      capabilities: "Meeting Bingo Card Maker creates entertaining bingo cards that make meetings more engaging and help teams bond over shared experiences."
    },
    {
      image: "/landing_page_assets/citationswhite.png",
      title: "Lunch Buddy Matcher",
      subtitle: "Find your ideal lunch partner at work",
      description: "Based on interests, work style, and schedule, this agent matches you with a colleague for lunch or coffee chats.",
      websiteLink: "https://agentwebsite.com/lunch-buddy-matcher",
      metrics: [
        "Match success rate",
        "Meeting frequency",
        "User satisfaction",
        "Repeat matches"
      ],
      features: ["Interest Matching", "Schedule Coordination", "Personality Pairing", "Follow-up Tracking"],
      useCases: ["Team Building", "Networking", "Company Culture", "Professional Development"],
      capabilities: "Lunch Buddy Matcher uses compatibility algorithms to connect colleagues for meaningful professional and social interactions."
    }
  ];

  const openModal = (agent) => {
    setSelectedAgent(agent);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setSelectedAgent(null);
    setIsModalOpen(false);
  };

  return (
    <div className="mx-5 lg:mx-24 mt-24">
      <div className="text-3xl sm:text-4xl lg:text-5xl my-10 text-center font-medium lg:font-bold text-white">
        Agent Registry
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-1 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-3 gap-8 px-8">
        {agents.map((agent, index) => (
          <div
            key={index}
            className="bg-[#1a1a1a] rounded-lg shadow-lg p-6 flex flex-col items-center text-center text-white transition-transform transform hover:scale-105 cursor-pointer"
            onClick={() => openModal(agent)}
          >
            <img src={agent.image} alt={agent.title} className="w-16 h-16 mb-4" />
            <h3 className="text-xl font-semibold mb-2">{agent.title}</h3>
            <p className="text-sm text-gray-300 mb-2">{agent.subtitle}</p>
            <p className="text-md mb-4 line-clamp-3">{agent.description}</p>
            <button
              className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-4 py-2 rounded-md font-semibold"
            >
              More Info
            </button>
          </div>
        ))}
      </div>

      {isModalOpen && selectedAgent && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-75 z-50">
          <div className="bg-[#1a1a1a] w-11/12 md:w-3/4 lg:w-1/2 rounded-lg p-8 text-white relative max-h-screen overflow-y-auto">
            <button
              className="absolute top-2 right-2 text-2xl font-bold"
              onClick={closeModal}
            >
              &times;
            </button>
            <h1 className="mx-auto mb-4 text-4xl font-bold">{selectedAgent.title}</h1>
            <p className="text-xl text-gray-300 mb-4 text-center">{selectedAgent.subtitle}</p>
            <hr className="h-px mb-4 bg-white border-0 mx-auto" />

            <h2 className="text-2xl font-bold mb-4 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">About</h2>
            <p className="text-lg mb-6">{selectedAgent.description}</p>

            <div className="mb-6">
              <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Key Metrics</h3>
              <ul className="list-disc list-inside text-md space-y-2">
                {selectedAgent.metrics.map((metric, index) => (
                  <li key={index}>{metric}</li>
                ))}
              </ul>
            </div>

            <div className="mb-6">
              <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Features</h3>
              <ul className="list-disc list-inside text-md space-y-2">
                {selectedAgent.features.map((feature, index) => (
                  <li key={index}>{feature}</li>
                ))}
              </ul>
            </div>

            <div className="mb-6">
              <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Use Cases</h3>
              <ul className="list-disc list-inside text-md space-y-2">
                {selectedAgent.useCases.map((useCase, index) => (
                  <li key={index}>{useCase}</li>
                ))}
              </ul>
            </div>

            <div className="mb-8">
              <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Capabilities</h3>
              <p className="text-md leading-relaxed">{selectedAgent.capabilities}</p>
            </div>

            <a
              href={selectedAgent.websiteLink}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-4 py-2 rounded-md font-semibold mt-4"
            >
              Try Agent
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

export default Registry;
