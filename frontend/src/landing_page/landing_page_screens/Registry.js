import React, { useState } from "react";

function Registry() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);

  const agents = [
    {
      image: "/landing_page_assets/img1.png",
      title: "Auto Follow-Up Buddy",
      subtitle: "Never forget to send a follow-up email again",
      description: "Upload your last email or meeting notes and this agent drafts a personalized, thoughtful follow-up. Suggests optimal timing and subject lines, integrates with Gmail for seamless sending. Great for networking, job hunting, and client management.",
      websiteLink: "https://lutra.ai/shared/XBxkC18Mnwo",
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
      image: "/landing_page_assets/img2.png",
      title: "LinkedIn Job Hunter Pro",
      subtitle: "Match your profile to jobs and message recruiters in one click",
      description: "Upload your resume or connect your LinkedIn. This agent scrapes job postings, tailors recruiter DMs, and even suggests edits to your profile for better keyword matches.",
      websiteLink: "https://lutra.ai/shared/S-GnnGlD7zc",
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
      image: "/landing_page_assets/img3.png",
      title: "Cold Outreach Designer",
      subtitle: "Create a mini email campaign from scratch",
      description: "Describe your product and target audience, and this agent generates 2–3 cold emails with compelling hooks and CTAs. Designed for startup founders, freelancers, and B2B marketers.",
      websiteLink: "https://lutra.ai/shared/BztORfXlBUk",
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
      image: "/landing_page_assets/img4.png",
      title: "Instant ICP Analyzer",
      subtitle: "Find your Ideal Customer Profile based on your website or product",
      description: "Enter your startup's website, and the agent generates your likely ICPs: sectors, titles, firmographics, and even a target contact list suggestion. Ideal for new GTM teams.",
      websiteLink: "https://lutra.ai/shared/V5SQRt8TWis",
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
      image: "/landing_page_assets/img5.png",
      title: "Meeting-to-Newsletter Generator",
      subtitle: "Turn Zoom notes into a polished update for your audience",
      description: "Upload meeting transcripts or bullet notes. Agent turns it into a well-structured blog, newsletter, or memo with clear formatting and editable tone. Ideal for content creators, PMs, and founders.",
      websiteLink: "https://lutra.ai/shared/Y88uufxJGgk",
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
      websiteLink: "https://lutra.ai/shared/tCs6cw6hA-w",
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
      websiteLink: "https://lutra.ai/shared/3Ulu3akUl1M",
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
      websiteLink: "https://lutra.ai/shared/N6_Pzzg1L1k",
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
      websiteLink: "https://lutra.ai/shared/6GH2sFS9pOg",
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
      websiteLink: "https://lutra.ai/shared/pNUzcBzkf08",
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
      websiteLink: "https://lutra.ai/shared/o_OHINQsVIg",
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
      websiteLink: "https://lutra.ai/shared/kG1KV0a_V8c",
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
      websiteLink: "https://lutra.ai/shared/8rK-_uTMJtQ",
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
      websiteLink: "https://lutra.ai/shared/tPX6-WBi1E0",
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
      websiteLink: "https://lutra.ai/shared/oHCKSdEV07c",
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

  const handleTryAgent = (e, websiteLink) => {
    e.stopPropagation();
    window.open(websiteLink, '_blank', 'noopener,noreferrer');
  };

  const handleMoreInfo = (e, agent) => {
    e.stopPropagation();
    openModal(agent);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-black via-[#141414] to-[#1a1a1a] px-5 lg:px-32 py-24">
      <h1 className="text-center text-5xl font-extrabold text-white mb-20 tracking-tight">Agent Registry</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-12">
        {agents.map((agent, index) => (
          <div
            key={index}
            className="bg-[#161616] border border-[#2a2a2a] rounded-3xl shadow-lg overflow-hidden transform transition-transform hover:-translate-y-3 hover:shadow-xl cursor-pointer group"
            onClick={() => window.open(agent.websiteLink, '_blank', 'noopener,noreferrer')}
          >
            <div className="relative w-full h-56 overflow-hidden">
              <img
                src={agent.image}
                alt={agent.title}
                className="w-full h-full object-cover object-center transition-opacity duration-300 group-hover:opacity-30"
              />
              <div className="absolute inset-0 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 space-y-3">
                <button
                  onClick={(e) => handleTryAgent(e, agent.websiteLink)}
                  className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-5 py-2 rounded-full font-medium text-sm hover:scale-105 transition-transform"
                >
                  Try Agent
                </button>
                <button
                  onClick={(e) => handleMoreInfo(e, agent)}
                  className="bg-white text-black px-5 py-2 rounded-full font-medium text-sm hover:scale-105 transition-transform"
                >
                  More Info
                </button>
              </div>
            </div>
            <div className="p-5">
              <h3 className="text-xl font-bold text-white mb-1">{agent.title}</h3>
              <p className="text-sm text-gray-400">{agent.subtitle}</p>
            </div>
          </div>
        ))}
      </div>

      {isModalOpen && selectedAgent && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-70 z-50 backdrop-blur-md">
          <div className="bg-[#161616] w-11/12 md:w-3/4 lg:w-1/2 rounded-3xl p-10 text-white relative max-h-[90vh] overflow-y-auto border border-[#2a2a2a] shadow-2xl">
            <button
              className="absolute top-5 right-5 text-3xl font-bold text-gray-400 hover:text-white transition"
              onClick={closeModal}
            >
              &times;
            </button>

            <h1 className="text-center text-4xl font-bold mb-5">{selectedAgent.title}</h1>
            <p className="text-lg text-center text-gray-300 mb-10">{selectedAgent.subtitle}</p>

            <section className="mb-8">
              <h2 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">About</h2>
              <p className="text-md">{selectedAgent.description}</p>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Key Metrics</h3>
              <ul className="list-disc list-inside text-md space-y-1">{selectedAgent.metrics.map((m, i) => <li key={i}>{m}</li>)}</ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Features</h3>
              <ul className="list-disc list-inside text-md space-y-1">{selectedAgent.features.map((f, i) => <li key={i}>{f}</li>)}</ul>
            </section>

            <section className="mb-8">
              <h3 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Use Cases</h3>
              <ul className="list-disc list-inside text-md space-y-1">{selectedAgent.useCases.map((u, i) => <li key={i}>{u}</li>)}</ul>
            </section>

            <section className="mb-10">
              <h3 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Capabilities</h3>
              <p className="text-md leading-relaxed">{selectedAgent.capabilities}</p>
            </section>

            <a href={selectedAgent.websiteLink} target="_blank" rel="noopener noreferrer"
              className="block w-full text-center bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-6 py-3 rounded-full font-semibold text-lg hover:scale-105 transition-transform">
              Try Agent
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

export default Registry;


//   const openModal = (agent) => {
//     setSelectedAgent(agent);
//     setIsModalOpen(true);
//   };

//   const closeModal = () => {
//     setSelectedAgent(null);
//     setIsModalOpen(false);
//   };

//   const handleTryAgent = (e, websiteLink) => {
//     e.stopPropagation();
//     window.open(websiteLink, '_blank', 'noopener,noreferrer');
//   };

//   const handleMoreInfo = (e, agent) => {
//     e.stopPropagation();
//     openModal(agent);
//   };

//   return (
//     <div className="min-h-screen bg-gradient-to-b from-black via-[#141414] to-[#1a1a1a] px-5 lg:px-24 py-24">
//       <h1 className="text-center text-5xl font-extrabold text-white mb-16">Agent Registry</h1>

//       <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-10">
//         {agents.map((agent, index) => (
//           <div
//             key={index}
//             className="bg-[#1a1a1a] rounded-3xl shadow-2xl overflow-hidden transform transition-transform hover:-translate-y-3 hover:shadow-3xl cursor-pointer relative group border border-[#2a2a2a]"
//             onClick={() => window.open(agent.websiteLink, '_blank', 'noopener,noreferrer')}
//           >
//             <div className="relative w-full h-56 overflow-hidden">
//               <img
//                 src={agent.image}
//                 alt={agent.title}
//                 className="w-full h-full object-cover object-center transition-opacity duration-300 group-hover:opacity-40"
//               />

//               <div className="absolute inset-0 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 space-y-2">
//                 <button
//                   onClick={(e) => handleTryAgent(e, agent.websiteLink)}
//                   className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-4 py-2 rounded-full font-semibold text-sm hover:scale-105 transition-transform"
//                 >
//                   Try It
//                 </button>
//                 <button
//                   onClick={(e) => handleMoreInfo(e, agent)}
//                   className="bg-white text-black px-4 py-2 rounded-full font-semibold text-sm hover:scale-105 transition-transform"
//                 >
//                   More Info
//                 </button>
//               </div>
//             </div>

//             <div className="p-5">
//               <h3 className="text-xl font-bold text-white mb-2">{agent.title}</h3>
//               <p className="text-sm text-gray-400">{agent.subtitle}</p>
//             </div>
//           </div>
//         ))}
//       </div>

//       {isModalOpen && selectedAgent && (
//         <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-80 z-50 backdrop-blur-sm">
//           <div className="bg-[#1a1a1a] w-11/12 md:w-3/4 lg:w-1/2 rounded-3xl p-10 text-white relative max-h-[90vh] overflow-y-auto border border-[#2a2a2a] shadow-2xl">
//             <button
//               className="absolute top-4 right-4 text-3xl font-bold text-gray-400 hover:text-white transition"
//               onClick={closeModal}
//             >
//               &times;
//             </button>
//             <h1 className="text-center text-4xl font-bold mb-6">{selectedAgent.title}</h1>
//             <p className="text-xl text-center text-gray-300 mb-8">{selectedAgent.subtitle}</p>

//             <section className="mb-8">
//               <h2 className="text-2xl font-bold mb-3 text-gradient">About</h2>
//               <p className="text-lg">{selectedAgent.description}</p>
//             </section>

//             <section className="mb-8">
//               <h3 className="text-2xl font-bold mb-3 text-gradient">Key Metrics</h3>
//               <ul className="list-disc list-inside text-md space-y-1">{selectedAgent.metrics.map((m, i) => <li key={i}>{m}</li>)}</ul>
//             </section>

//             <section className="mb-8">
//               <h3 className="text-2xl font-bold mb-3 text-gradient">Features</h3>
//               <ul className="list-disc list-inside text-md space-y-1">{selectedAgent.features.map((f, i) => <li key={i}>{f}</li>)}</ul>
//             </section>

//             <section className="mb-8">
//               <h3 className="text-2xl font-bold mb-3 text-gradient">Use Cases</h3>
//               <ul className="list-disc list-inside text-md space-y-1">{selectedAgent.useCases.map((u, i) => <li key={i}>{u}</li>)}</ul>
//             </section>

//             <section className="mb-8">
//               <h3 className="text-2xl font-bold mb-3 text-gradient">Capabilities</h3>
//               <p className="text-md leading-relaxed">{selectedAgent.capabilities}</p>
//             </section>

//             <a href={selectedAgent.websiteLink} target="_blank" rel="noopener noreferrer"
//               className="block w-full text-center bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-6 py-3 rounded-full font-semibold text-lg hover:scale-105 transition-transform">
//               Try Agent
//             </a>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }

// export default Registry;


  // const openModal = (agent) => {
  //   setSelectedAgent(agent);
  //   setIsModalOpen(true);
  // };

  // const closeModal = () => {
  //   setSelectedAgent(null);
  //   setIsModalOpen(false);
  // };

  // const handleTryAgent = (e, websiteLink) => {
  //   e.stopPropagation();
  //   window.open(websiteLink, '_blank', 'noopener,noreferrer');
  // };

  // const handleMoreInfo = (e, agent) => {
  //   e.stopPropagation();
  //   openModal(agent);
  // };

  // return (
  //   <div className="mx-5 lg:mx-24 mt-24">
  //     <div className="text-3xl sm:text-4xl lg:text-5xl my-10 text-center font-medium lg:font-bold text-white">
  //       Agent Registry
  //     </div>

  //     <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-8 px-8">
  //       {agents.map((agent, index) => (
  //         <div
  //           key={index}
  //           className="bg-[#1a1a1a] rounded-lg shadow-lg overflow-hidden flex flex-col items-center text-center text-white transition-transform transform hover:scale-105 cursor-pointer relative group"
  //           onClick={() => window.open(agent.websiteLink, '_blank', 'noopener,noreferrer')}
  //         >
  //           {/* Image Container with Hover Effect */}
  //           <div className="relative w-full h-40 overflow-hidden">
  //             <img
  //               src={agent.image}
  //               alt={agent.title}
  //               className="w-full h-full object-cover object-center transition-opacity duration-300 group-hover:opacity-30"
  //             />

  //             {/* Hover Buttons */}
  //             <div className="absolute inset-0 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 space-y-2">
  //               <button
  //                 onClick={(e) => handleTryAgent(e, agent.websiteLink)}
  //                 className="bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-3 py-1 rounded-md font-semibold text-sm hover:scale-105 transition-transform"
  //               >
  //                 Try It
  //               </button>
  //               <button
  //                 onClick={(e) => handleMoreInfo(e, agent)}
  //                 className="bg-white text-black px-3 py-1 rounded-md font-semibold text-sm hover:scale-105 transition-transform"
  //               >
  //                 More Info
  //               </button>
  //             </div>
  //           </div>

  //           <div className="p-3">
  //             <h3 className="text-lg font-semibold mb-2 line-clamp-2">{agent.title}</h3>
  //             <p className="text-sm text-gray-400 line-clamp-2">{agent.subtitle}</p>
  //           </div>
  //         </div>
  //       ))}
  //     </div>

  //     {/* Modal */}
  //     {isModalOpen && selectedAgent && (
  //       <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-75 z-50">
  //         <div className="bg-[#1a1a1a] w-11/12 md:w-3/4 lg:w-1/2 rounded-lg p-8 text-white relative max-h-screen overflow-y-auto">
  //           <button
  //             className="absolute top-2 right-2 text-2xl font-bold hover:text-gray-300"
  //             onClick={closeModal}
  //           >
  //             &times;
  //           </button>
  //           <h1 className="mx-auto mb-4 text-4xl font-bold">{selectedAgent.title}</h1>
  //           <p className="text-xl text-gray-300 mb-4 text-center">{selectedAgent.subtitle}</p>
  //           <hr className="h-px mb-4 bg-white border-0 mx-auto" />

  //           <h2 className="text-2xl font-bold mb-4 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">About</h2>
  //           <p className="text-lg mb-6">{selectedAgent.description}</p>

  //           <div className="mb-6">
  //             <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Key Metrics</h3>
  //             <ul className="list-disc list-inside text-md space-y-2">
  //               {selectedAgent.metrics.map((metric, index) => (
  //                 <li key={index}>{metric}</li>
  //               ))}
  //             </ul>
  //           </div>

  //           <div className="mb-6">
  //             <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Features</h3>
  //             <ul className="list-disc list-inside text-md space-y-2">
  //               {selectedAgent.features.map((feature, index) => (
  //                 <li key={index}>{feature}</li>
  //               ))}
  //             </ul>
  //           </div>

  //           <div className="mb-6">
  //             <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Use Cases</h3>
  //             <ul className="list-disc list-inside text-md space-y-2">
  //               {selectedAgent.useCases.map((useCase, index) => (
  //                 <li key={index}>{useCase}</li>
  //               ))}
  //             </ul>
  //           </div>

  //           <div className="mb-8">
  //             <h3 className="text-2xl font-semibold mb-2 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">Capabilities</h3>
  //             <p className="text-md leading-relaxed">{selectedAgent.capabilities}</p>
  //           </div>

  //           <a
  //             href={selectedAgent.websiteLink}
  //             target="_blank"
  //             rel="noopener noreferrer"
  //             className="inline-block bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-4 py-2 rounded-md font-semibold mt-4 hover:scale-105 transition-transform"
  //           >
  //             Try Agent
  //           </a>
  //         </div>
  //       </div>
  //     )}
  //   </div>
  // );

  // }

  // export default Registry;
