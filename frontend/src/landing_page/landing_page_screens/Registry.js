import React, { useState, useMemo } from "react";
import { FaPlay } from "react-icons/fa";

function Registry() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");


  const agents = [
    {
    image: "/images/one-pager_builder_agent.png",
    title: "One-Pager Builder Agent",
    subtitle: "Create a GTM-ready sales sheet in minutes",
    description: "Input your product description, key features, and audience. This agent auto-generates a slick, well-formatted one-pager for sales or fundraising—editable in Google Docs or Canva.",
    websiteLink: "https://lutra.ai/shared/pNUzcBzkf08",
    metrics: [
      "Visual/content quality",
      "Time saved",
      "Adoption rate",
      "Edit rate"
    ],
    capabilities: "Creates well-formatted one-pagers quickly for sales or fundraising.",
    category: "Creator"
  },
  {
    image: "/images/meeting-to-newsletter_generator.png",
    title: "Meeting-to-Newsletter Generator",
    subtitle: "Turn Zoom notes into a polished update for your audience",
    description: "Upload transcripts or notes. Agent structures into blog, memo, or newsletter. Ideal for content creators.",
    websiteLink: "https://lutra.ai/shared/gHpdQZNBcqw",
    metrics: [
      "Output quality",
      "Time saved",
      "Share rate",
      "Edit rate"
    ],
    capabilities: "Structures meeting notes into polished newsletters or blogs.",
    category: "Creator"
  },
  {
    image: "/images/smart_newsletter_engine.png",
    title: "Smart Newsletter Engine",
    subtitle: "Personalized newsletters tailored to each account",
    description: "Dynamically personalizes newsletters based on reader’s company or behavior. Integrates with HubSpot, Mailchimp.",
    websiteLink: "https://lutra.ai/shared/gHpdQZNBcqw",
    metrics: [
      "Open/CTR rate",
      "Time saved",
      "Segment engagement"
    ],
    capabilities: "Personalizes newsletters dynamically per account using integrations.",
    category: "Creator"
  },
  {
    image: "/images/zoom_background_generator.png",
    title: "Zoom Background Generator",
    subtitle: "Make a custom AI-generated Zoom background to match your vibe",
    description: "Choose a theme and get a downloadable, stylized background.",
    websiteLink: "https://lutra.ai/shared/9Gn-CL032pY",
    metrics: [
      "Downloads",
      "Rating",
      "Reuse",
      "Virality"
    ],
    capabilities: "Generates custom AI Zoom backgrounds by theme.",
    category: "Creator"
  },
  {
    image: "/images/deck_designer_agent.png",
    title: "Deck Designer Agent",
    subtitle: "Pitch-ready slides from a prompt",
    description: "Input your pitch or topic, and the agent generates a full presentation deck with visuals, talking points, and speaker notes.",
    websiteLink: "https://lutra.ai/shared/TsuSKyvpmoE",
    metrics: [
      "Time saved",
      "Slide design quality",
      "Usage rate",
      "Edit rate"
    ],
    capabilities: "Generates presentation decks from prompts.",
    category: "Creator"
  },
  {
    image: "/images/ad_copy_brainstormer.png",
    title: "Ad Copy Brainstormer",
    subtitle: "Fresh ad angles in seconds",
    description: "Provide product and audience; receive multiple ad variants in different tones (funny, urgent, premium, etc).",
    websiteLink: "https://lutra.ai/shared/5CGhtFO4ntw",
    metrics: [
      "CTR improvement",
      "Variant diversity",
      "User preference selection",
      "Reuse rate"
    ],
    capabilities: "Generates multiple ad variants with different tones.",
    category: "Creator"
  },
  {
    image: "/images/blog_post_outline_generator.png",
    title: "Blog Post Outline Generator",
    subtitle: "From headline to structured article in seconds",
    description: "Enter your topic or headline, and the agent generates a coherent outline with headers, word counts, and internal link suggestions.",
    websiteLink: "https://lutra.ai/shared/36KdLoeHEko",
    metrics: [
      "Outline coherence",
      "SEO coverage",
      "Time saved",
      "Edit rate"
    ],
    capabilities: "Creates structured blog outlines with SEO suggestions.",
    category: "Creator"
  },
  {
    image: "/images/infographic_builder.png",
    title: "Infographic Builder",
    subtitle: "Data‑driven visuals without a designer",
    description: "Upload data or pick a template; the agent crafts a polished infographic with charts, icons, and captions.",
    websiteLink: "https://lutra.ai/shared/r0mRz-JP72A",
    metrics: [
      "Visual appeal",
      "Data accuracy",
      "Creation time",
      "Share rate"
    ],
    capabilities: "Creates infographics from data quickly.",
    category: "Creator"
  },
  {
    image: "/images/social_media_carousel_designer.png",
    title: "Social Media Carousel Designer",
    subtitle: "Scroll‑stopping multi‑slide posts in one go",
    description: "Input message and platform; agent designs a 3‑5 slide carousel with copy, layout, and visual prompts.",
    websiteLink: "https://lutra.ai/shared/NYNLuO1-Ydc",
    metrics: [
      "Engagement (saves/shares)",
      "Slide clarity",
      "Time saved",
      "Edit rate"
    ],
    capabilities: "Designs social media carousels from input messages.",
    category: "Creator"
  },
  {
    image: "/images/tiktok_script_writer.png",
    title: "TikTok Script Writer",
    subtitle: "Create engaging short-form scripts instantly",
    description: "Provide your content idea and audience; agent returns a 15–60 second hook‑based script.",
    websiteLink: "https://lutra.ai/shared/Q57FFKr4k0I",
    metrics: [
      "Retention time",
      "Completion rate",
      "Edit frequency",
      "View count"
    ],
    capabilities: "Creates engaging TikTok scripts quickly.",
    category: "Creator"
  },
  {
    image: "/images/competitor_pricing_monitor.png",
    title: "Competitor Pricing Monitor",
    subtitle: "Monitor and analyze competitor pricing changes",
    description: "Track changes in competitor pricing, promotions, and product strategies.",
    websiteLink: "https://lutra.ai/shared/uFbEXnTq0Tw",
    metrics: [
      "Price change detection",
      "Competitive insight",
      "Response speed",
      "Revenue uplift"
    ],
    capabilities: "Tracks competitor pricing behavior over time.",
    category: "Analyze"
  },
  {
    image: "/images/market_trend_analyzer.png",
    title: "Market Trend Analyzer",
    subtitle: "Detect emerging market trends",
    description: "Aggregate news, social signals, and research to identify emerging industry shifts.",
    websiteLink: "https://lutra.ai/shared/AGAQNAi0-uk",
    metrics: [
      "Trend relevance",
      "Signal aggregation quality",
      "Insight quality",
      "Time saved"
    ],
    capabilities: "Identifies emerging market trends from multiple sources.",
    category: "Analyze"
  },
  {
    image: "/images/financial_report_summarizer.png",
    title: "Financial Report Summarizer",
    subtitle: "Summarize financial performance reports",
    description: "Extract KPIs, management commentary, and risk factors from company filings.",
    websiteLink: "https://lutra.ai/shared/Z74tRRLgxV4",
    metrics: [
      "Summary quality",
      "Time saved",
      "Decision support quality",
      "Analyst satisfaction"
    ],
    capabilities: "Summarizes quarterly and annual reports for financial analysts.",
    category: "Analyze"
  },
  {
    image: "/images/product_feedback_summarizer.png",
    title: "Product Feedback Summarizer",
    subtitle: "Summarize customer reviews and feedback",
    description: "Extract common themes, sentiment, and feature requests from feedback data.",
    websiteLink: "https://lutra.ai/shared/UVrrIq4VC2A",
    metrics: [
      "Theme extraction accuracy",
      "Sentiment accuracy",
      "Time saved",
      "Product improvement adoption"
    ],
    capabilities: "Summarizes feedback into actionable product insights.",
    category: "Analyze"
  },
  {
    image: "/images/seo_keyword_expander.png",
    title: "SEO Keyword Expander",
    subtitle: "Expand search keyword coverage",
    description: "Suggest long-tail keywords, search volume estimates, and ranking difficulty.",
    websiteLink: "https://lutra.ai/shared/GEXHnAdmgvU",
    metrics: [
      "Keyword relevance",
      "Search volume accuracy",
      "Ranking uplift",
      "SEO traffic growth"
    ],
    capabilities: "Expands keyword lists for organic traffic growth.",
    category: "Analyze"
  },
  {
    image: "/images/upreach.png",
    title: "Upreach",
    subtitle: "AI-powered email marketing and outreach automation",
    description: "Upreach is an advanced email marketing agent designed to streamline outreach and optimize email campaigns with AI-driven insights.",
    websiteLink: "https://www.youtube.com/watch?v=d0ZkHkRLbpU",
    metrics: [
      "Open rate improvement",
      "Personalization depth",
      "Campaign conversion rate",
      "Time saved on outreach"
    ],
    capabilities: "Automates email campaigns, personalizes outreach, analyzes engagement, and optimizes future strategy.",
    category: "Productivity"
  },
  {
    image: "/images/autolabel.png",
    title: "AutoLabel",
    subtitle: "AI-powered data labeling for machine learning datasets",
    description: "AutoLabel provides accurate and efficient annotation for large-scale image, text, and entity extraction datasets, supporting multiple annotation formats with integrated quality control.",
    websiteLink: "https://www.youtube.com/watch?v=EAeBYGkxA_8",
    metrics: [
      "Labeling accuracy",
      "Annotation throughput",
      "Quality assurance score",
      "Dataset export success rate"
    ],
    capabilities: "Automates data annotation with support for images, text, and entities; includes quality control and scalable dataset exports.",
    category: "Analyze"
  },
  {
    image: "/images/ai-rfp.png",
    title: "AI-RFP",
    subtitle: "Grant writing and RFP proposal drafting agent",
    description: "AI-RFP assists with grant writing and proposal drafting, automatically generating high-quality drafts and analyzing funding opportunities for compliance and fit.",
    websiteLink: "https://www.youtube.com/watch?v=fE4_Yjjfl0M",
    metrics: [
      "Proposal completion time reduction",
      "Funding opportunity matching rate",
      "Draft quality score",
      "Reviewer satisfaction"
    ],
    capabilities: "Automates drafting, reviewing, and funding source research for proposals and grant applications.",
    category: "Productivity"
  },
  {
    image: "/images/autocode.png",
    title: "Autocode",
    subtitle: "Autonomous AI software engineer for coding tasks",
    description: "Autocode automatically generates code, reviews pull requests, detects bugs, and suggests optimizations for software projects with minimal human intervention.",
    websiteLink: "https://www.youtube.com/watch?v=K2KUVdZjZnc",
    metrics: [
      "Code generation speed",
      "Code review coverage",
      "Bug detection accuracy",
      "Developer productivity uplift"
    ],
    capabilities: "Generates and reviews code, detects bugs, and recommends refactorings for better software quality.",
    category: "Code"
  },
  {
    image: "/images/financial_chatbot.png",
    title: "Financial Chatbot",
    subtitle: "AI-powered financial analysis and reporting agent",
    description: "The Financial Chatbot delivers real-time financial insights, analyzes market data, and generates customizable dashboards to support decision-making.",
    websiteLink: "https://www.youtube.com/watch?v=SW6itfZ2nmg",
    metrics: [
      "Analysis turnaround time",
      "Market trend detection accuracy",
      "Dashboard customization flexibility",
      "User satisfaction"
    ],
    capabilities: "Analyzes financial reports, detects trends, and produces interactive dashboards for financial insights.",
    category: "Analyze"
  },
  {
    image: "/images/autonews.png",
    title: "AutoNews",
    subtitle: "AI newsletter and content curation agent",
    description: "AutoNews curates trending content from multiple sources, summarizes key insights, and automatically compiles personalized newsletters for distribution.",
    websiteLink: "https://www.youtube.com/watch?v=sKSqpxP-GRw",
    metrics: [
      "Curation relevance score",
      "Newsletter open rate",
      "Subscriber engagement",
      "Time saved on content assembly"
    ],
    capabilities: "Aggregates, summarizes, and personalizes content into newsletters while tracking audience engagement.",
    category: "Creator"
  },
   {
     "image": "/images/job_description_optimizer.png",
     "title": "Job Description Optimizer",
     "subtitle": "Attract better talent with smarter listings",
     "description": "Paste your draft JD or hiring goals. This agent rewrites for clarity, inclusiveness, and keyword optimization. Includes market compensation suggestions.",
     "websiteLink": "https://lutra.ai/shared/o_OHINQsVIg",
     "metrics": [
       "JD engagement",
       "Keyword density",
       "Recruiter satisfaction",
       "Edit rate"
     ],
     "capabilities": "Optimizes job descriptions for clarity and inclusiveness.",
     "category": "Education"
   },
   {
     "image": "/images/course_curriculum_designer.png",
     "title": "Course Curriculum Designer",
     "subtitle": "Build a multi-week learning plan from a topic",
     "description": "Enter a skill (e.g. SQL, branding, finance for PMs), and agent returns modules, learning objectives, weekly assignments, and suggested resources.",
     "websiteLink": "https://lutra.ai/shared/5mYjwzYznOA",
     "metrics": [
       "Curriculum completeness",
       "Learning outcome fit",
       "Reuse rate",
       "Instructor feedback"
     ],
     "capabilities": "Designs multi-week learning curricula.",
     "category": "Education"
   },
   {
     "image": "/images/instant_icp_analyzer.png",
     "title": "Instant ICP Analyzer",
     "subtitle": "Find your Ideal Customer Profile based on your website or product",
     "description": "Enter a website, get sectors, firmographics, and contact list suggestions.",
     "websiteLink": "https://lutra.ai/shared/V5SQRt8TWis",
     "metrics": [
       "ICP match score",
       "Contact usefulness",
       "Lead volume",
       "Satisfaction score"
     ],
     "capabilities": "Analyzes website to identify ideal customer profile.",
     "category": "Analyze"
   },
   {
     "image": "/images/icp_contact_finder.png",
     "title": "ICP Contact Finder",
     "subtitle": "Instantly generate leads that match your ideal customer profile",
     "description": "Auto-generates up to 500 verified leads based on your product or company. Filters by role, industry, etc.",
     "websiteLink": "https://lutra.ai/shared/6GH2sFS9pOg",
     "metrics": [
       "ICP fit",
       "Bounce rate",
       "Lead volume",
       "Pipeline impact"
     ],
     "capabilities": "Generates leads matching your ideal customer profile.",
     "category": "Analyze"
   },
   {
     "image": "/images/linkedin_job_hunter_pro.png",
     "title": "LinkedIn Job Hunter Pro",
     "subtitle": "Match your profile to jobs and message recruiters in one click",
     "description": "Connect LinkedIn, scrape jobs, tailor DMs, and optimize your profile.",
     "websiteLink": "https://lutra.ai/shared/5f-uI5W74gA",
     "metrics": [
       "Matches found",
       "Recruiter reply rate",
       "Profile-match accuracy",
       "Message clarity"
     ],
     "capabilities": "Matches jobs and messages recruiters efficiently.",
     "category": "Analyze"
   },
   {
     "image": "/images/interview_question_generator.png",
     "title": "Interview Question Generator",
     "subtitle": "Generate tailored interview questions for any role",
     "description": "Input role and seniority, get behavioral, technical, and culture-fit questions with scoring rubrics.",
     "websiteLink": "https://lutra.ai/shared/4jZnbzvnVIQ",
     "metrics": [
       "Question relevance",
       "Interviewer satisfaction",
       "Candidate experience",
       "Time saved"
     ],
     "capabilities": "Creates tailored interview questions with rubrics.",
     "category": "Education"
   },
   {
     "image": "/images/learning_style_analyzer.png",
     "title": "Learning Style Analyzer",
     "subtitle": "Identify your preferred learning style and study tips",
     "description": "Take a quick quiz; agent provides personalized advice and resource suggestions based on style (visual, auditory, kinesthetic).",
     "websiteLink": "https://lutra.ai/shared/jNWR6OKGILs",
     "metrics": [
       "Quiz completion",
       "User satisfaction",
       "Advice relevance",
       "Follow-up engagement"
     ],
     "capabilities": "Analyzes learning style and offers personalized study tips.",
     "category": "Education"
   },
   {
     "image": "/images/expense_categorization_agent.png",
     "title": "Expense Categorization Agent",
     "subtitle": "Automatically categorize business expenses from receipts",
     "description": "Upload receipts or expense data; agent classifies and summarizes for accounting.",
     "websiteLink": "https://lutra.ai/shared/QQd5nS8oZjY",
     "metrics": [
       "Categorization accuracy",
       "Processing speed",
       "Error rate",
       "Accounting adoption"
     ],
     "capabilities": "Categorizes expenses automatically.",
     "category": "Analyze"
   },
   {
     "image": "/images/contract_clause_highlighter.png",
     "title": "Contract Clause Highlighter",
     "subtitle": "Identify key clauses and risks in contracts instantly",
     "description": "Upload contracts; agent highlights terms like termination, indemnity, exclusivity, and risk areas.",
     "websiteLink": "https://lutra.ai/shared/Y23gpEOrxtA",
     "metrics": [
       "Clause detection accuracy",
       "Risk flagging precision",
       "Review speed",
       "Legal team adoption"
     ],
     "capabilities": "Highlights key contract clauses and risks.",
     "category": "Analyze"
   },
   {
     "image": "/images/email_response_suggestion_agent.png",
     "title": "Email Response Suggestion Agent",
     "subtitle": "Get quick, contextual replies for your inbox",
     "description": "Analyzes email thread and suggests reply drafts tailored to tone and urgency.",
     "websiteLink": "https://lutra.ai/shared/mJPTE2ag1yI",
     "metrics": [
       "Reply acceptance rate",
       "Time saved",
       "Tone accuracy",
       "User satisfaction"
     ],
     "capabilities": "Suggests contextual email replies.",
     "category": "Automate"
   },
   {
     "image": "/images/calendar_scheduling_agent.png",
     "title": "Calendar Scheduling Agent",
     "subtitle": "Automate meeting scheduling with smart availability matching",
     "description": "Syncs calendars, proposes optimal slots, and sends invites with customizable messages.",
     "websiteLink": "https://lutra.ai/shared/BgxD8m8RLsw",
     "metrics": [
       "Scheduling success rate",
       "Time saved",
       "User satisfaction",
       "Conflict reduction"
     ],
     "capabilities": "Automates scheduling and meeting invites.",
     "category": "Automate"
   },
   {
     "image": "/images/invoice_generation_agent.png",
     "title": "Invoice Generation Agent",
     "subtitle": "Create and send invoices automatically",
     "description": "Generate invoices based on contracts or sales data, customize templates, and send reminders.",
     "websiteLink": "https://lutra.ai/shared/Z7bmRCCY5vE",
     "metrics": [
       "Invoice accuracy",
       "Time saved",
       "Payment speed",
       "Error rate"
     ],
     "capabilities": "Generates and sends invoices automatically.",
     "category": "Automate"
   },
   {
     "image": "/images/social_media_posting_scheduler.png",
     "title": "Social Media Posting Scheduler",
     "subtitle": "Plan and automate social posts across platforms",
     "description": "Draft posts or upload media, schedule publishing, and track engagement metrics.",
     "websiteLink": "https://lutra.ai/shared/vkiCCFQScog",
     "metrics": [
       "Post reach",
       "Engagement rate",
       "Scheduling accuracy",
       "User adoption"
     ],
     "capabilities": "Schedules and automates social media posts.",
     "category": "Automate"
   },
   {
     "image": "/images/customer_onboarding_workflow_agent.png",
     "title": "Customer Onboarding Workflow Agent",
     "subtitle": "Automate onboarding emails and task sequences",
     "description": "Create personalized onboarding flows triggered by customer actions or milestones.",
     "websiteLink": "https://lutra.ai/shared/WW796GqYANg",
     "metrics": [
       "Completion rate",
       "Customer satisfaction",
       "Time saved",
       "Churn reduction"
     ],
     "capabilities": "Automates customer onboarding communications.",
     "category": "Automate"
   },
   {
     "image": "/images/document_translation_agent.png",
     "title": "Document Translation Agent",
     "subtitle": "Translate documents instantly with high accuracy",
     "description": "Supports multiple languages with formatting preserved.",
     "websiteLink": "https://lutra.ai/shared/alFufXKTgoA",
     "metrics": [
       "Translation accuracy",
       "Turnaround time",
       "User satisfaction",
       "Formatting retention"
     ],
     "capabilities": "Translates documents while preserving formatting.",
     "category": "Automate"
   },
   {
     "image": "/images/meeting_minute_taker.png",
     "title": "Meeting Minute Taker",
     "subtitle": "Automatically generate meeting minutes from recordings",
     "description": "Upload audio/video, get a summarized transcript with action items and decisions highlighted.",
     "websiteLink": "https://lutra.ai/shared/QnGzSpOubTo",
     "metrics": [
       "Transcript accuracy",
       "Action item detection",
       "Time saved",
       "User satisfaction"
     ],
     "capabilities": "Generates summarized meeting minutes with action points.",
     "category": "Automate"
   },
   {
     "image": "/images/travel_itinerary_planner.png",
     "title": "Travel Itinerary Planner",
     "subtitle": "Create detailed travel plans with attractions, hotels, and restaurants",
     "description": "Enter destination and dates; agent suggests optimized day-wise itineraries with booking links.",
     "websiteLink": "https://lutra.ai/shared/y-8iDdoQVT4",
     "metrics": [
       "Plan accuracy",
       "User satisfaction",
       "Booking conversion",
       "Time saved"
     ],
     "capabilities": "Plans detailed travel itineraries automatically.",
     "category": "Automate"
   },
   {
     "image": "/images/regex_pattern_builder.png",
     "title": "Regex Pattern Builder",
     "subtitle": "Complex regular expressions without the headache",
     "description": "Describe the text pattern you want to match, and the agent generates, tests, and explains the regex.",
     "websiteLink": "https://lutra.ai/shared/HrdBLQnUB9Q",
     "metrics": [
       "Regex accuracy",
       "Time saved",
       "Debugging support usage",
       "Error reduction"
     ],
     "capabilities": "Generates, tests, and explains regular expressions based on user descriptions.",
     "category": "Code"
   },
   {
     "image": "/images/code_docstring_writer.png",
     "title": "Code Docstring Writer",
     "subtitle": "Generate helpful comments for your codebase",
     "description": "Paste a code snippet, and this agent writes clear docstrings, type hints, and parameter descriptions.",
     "websiteLink": "https://lutra.ai/shared/8fJp6VLOg1Y",
     "metrics": [
       "Docstring completeness",
       "Developer edit rate",
       "Readability score",
       "Reuse across codebase"
     ],
     "capabilities": "Creates detailed docstrings and type hints for code snippets.",
     "category": "Code"
   },
   {
     "image": "/images/bug_fix_suggestion_bot.png",
     "title": "Bug Fix Suggestion Bot",
     "subtitle": "Quickly find and fix bugs with AI guidance",
     "description": "Paste your error message or problematic code snippet, and the agent analyzes, suggests fixes, and explains the root cause.",
     "websiteLink": "https://lutra.ai/shared/jBT2JGRLw-Q",
     "metrics": [
       "Bug resolution rate",
       "Fix accuracy",
       "Time saved",
       "Developer satisfaction"
     ],
     "capabilities": "Analyzes bugs and suggests fixes with explanations.",
     "category": "Code"
   },
   {
     "image": "/images/code_refactoring_assistant.png",
     "title": "Code Refactoring Assistant",
     "subtitle": "Clean up your code effortlessly",
     "description": "Upload a code module, and the agent proposes refactoring improvements focusing on readability, performance, and maintainability.",
     "websiteLink": "https://lutra.ai/shared/msu4EMZS2tM",
     "metrics": [
       "Code complexity reduction",
       "Readability score",
       "Developer adoption rate",
       "Performance impact"
     ],
     "capabilities": "Suggests code refactoring for better readability and performance.",
     "category": "Code"
   },
   {
     "image": "/images/api_endpoint_generator.png",
     "title": "API Endpoint Generator",
     "subtitle": "Spin up API endpoints with zero boilerplate",
     "description": "Describe your data models and desired endpoints, agent generates FastAPI/Flask/Django REST code complete with validation and docs.",
     "websiteLink": "https://lutra.ai/shared/c8Tqi4rLK34",
     "metrics": [
       "Endpoint correctness",
       "Code generation time",
       "Integration success rate",
       "Developer review edits"
     ],
     "capabilities": "Generates API endpoints based on user specifications.",
     "category": "Code"
   },
   {
     "image": "/images/unit_test_generator.png",
     "title": "Unit Test Generator",
     "subtitle": "Boost your test coverage without headaches",
     "description": "Provide functions or classes, and the agent generates comprehensive unit tests with edge cases and mocks.",
     "websiteLink": "https://lutra.ai/shared/QlvVxsR-qfE",
     "metrics": [
       "Test coverage increase",
       "Test execution success",
       "Bug catch rate",
       "Developer trust level"
     ],
     "capabilities": "Creates detailed unit tests automatically.",
     "category": "Code"
   },
   {
     "image": "/images/auto_follow-up_buddy.png",
     "title": "Auto Follow-Up Buddy",
     "subtitle": "Never forget to send a follow-up email again",
     "description": "Upload your last email/meeting note, agent drafts follow-up, suggests timing + subject line, integrates with Gmail.",
     "websiteLink": "https://lutra.ai/shared/I3r2w9iKLjQ",
     "metrics": [
       "Open/reply rate",
       "Time saved",
       "Follow-ups/session"
     ],
     "capabilities": "Drafts follow-up emails and suggests timing and subjects.",
     "category": "Productivity"
   },
   {
     "image": "/images/linkedin_dm_sender.png",
     "title": "LinkedIn DM Sender",
     "subtitle": "Ditch email — connect with leads where they live",
     "description": "Input LinkedIn profiles, agent writes personalized DMs.",
     "websiteLink": "https://lutra.ai/shared/N6_Pzzg1L1k",
     "metrics": [
       "Acceptance rate",
       "Response rate",
       "Quality score",
       "Flag rate"
     ],
     "capabilities": "Creates personalized LinkedIn direct messages for outreach.",
     "category": "Productivity"
   },
   {
     "image": "/images/meeting_summarizer_agent.png",
     "title": "Meeting Summarizer Agent",
     "subtitle": "From chaos to clarity in minutes",
     "description": "Upload meeting recordings or Zoom transcripts, and get clean, action-based summaries with follow-up lists.",
     "websiteLink": "https://lutra.ai/shared/8QiCtkXjfBA",
     "metrics": [
       "Summary usefulness",
       "Action item clarity",
       "Time saved",
       "Edit rate"
     ],
     "capabilities": "Generates concise meeting summaries with action items.",
     "category": "Productivity"
   },
   {
     "image": "/images/contextual_to-do_generator.png",
     "title": "Contextual To-Do Generator",
     "subtitle": "Turn messy notes into actionable next steps",
     "description": "Paste meeting notes, recordings, or chats. Agent parses and converts into a prioritized task list with owners.",
     "websiteLink": "https://lutra.ai/shared/iOwyohT6hHo",
     "metrics": [
       "Task clarity score",
       "Prioritization accuracy",
       "Time saved",
       "Action rate"
     ],
     "capabilities": "Transforms notes into prioritized task lists with owners.",
     "category": "Productivity"
   },
   {
     "image": "/images/email_tone_checker.png",
     "title": "Email Tone Checker",
     "subtitle": "Craft emails with the right tone every time",
     "description": "Paste your draft emails, and the agent suggests improvements for tone, politeness, clarity, and conciseness.",
     "websiteLink": "https://lutra.ai/shared/VGDnSLqS8Zk",
     "metrics": [
       "Email response rate",
       "User satisfaction",
       "Edit frequency",
       "Miscommunication incidents"
     ],
     "capabilities": "Improves email drafts for tone and clarity.",
     "category": "Productivity"
   },
   {
     "image": "/images/focus_session_planner.png",
     "title": "Focus Session Planner",
     "subtitle": "Maximize productivity with personalized work blocks",
     "description": "Input your tasks and deadlines, and the agent generates optimized focus sessions with breaks following productivity science.",
     "websiteLink": "https://lutra.ai/shared/QIOWUPoGSCM",
     "metrics": [
       "Task completion rate",
       "Focus session adherence",
       "User feedback",
       "Time-on-task increase"
     ],
     "capabilities": "Plans personalized focus sessions with breaks.",
     "category": "Productivity"
   },
   {
     "image": "/images/knowledge_base_summarizer.png",
     "title": "Knowledge Base Summarizer",
     "subtitle": "Turn documents and manuals into digestible insights",
     "description": "Upload large documents, and the agent produces executive summaries, key points, and FAQs for easy reference.",
     "websiteLink": "https://lutra.ai/shared/540kkErdsbQ",
     "metrics": [
       "Summary accuracy",
       "User engagement",
       "Helpdesk ticket reduction",
       "Time saved"
     ],
     "capabilities": "Summarizes large documents into key points and FAQs.",
     "category": "Productivity"
   }, // TODO: The ones below still need to be finalized
  {
    image: "/images/survey_data_interpreter.png",
    title: "Survey Data Interpreter",
    subtitle: "Extract insights from survey datasets",
    description: "Analyze responses, segment results, and generate actionable reports.",
    websiteLink: "https://lutra.ai/shared/ZwLQpnrvLdQ",
    metrics: [
      "Insight quality",
      "Segmentation depth",
      "Time saved",
      "Report clarity"
    ],
    capabilities: "Transforms raw survey responses into business insights.",
    category: "Analyze"
  },
  {
    image: "/images/performance_analytics_specialist.png",
    title: "Performance Analytics Specialist",
    subtitle: "Evaluate business and team KPIs",
    description: "Assess performance against targets, benchmarks, and goals.",
    websiteLink: "https://lutra.ai/shared/uB3I7S1-M80",
    metrics: [
      "KPI coverage",
      "Goal alignment",
      "Management adoption",
      "Continuous improvement"
    ],
    capabilities: "Tracks organizational performance against goals.",
    category: "Analyze"
  },
  {
    image: "/images/social_media_metrics_analyzer.png",
    title: "Social Media Metrics Analyzer",
    subtitle: "Evaluate engagement across social platforms",
    description: "Measure post performance, growth, and campaign effectiveness by channel.",
    websiteLink: "https://lutra.ai/shared/HIo2cMGUP2U",
    metrics: [
      "Engagement accuracy",
      "Platform insights",
      "Optimization clarity",
      "Campaign ROI"
    ],
    capabilities: "Analyzes platform-specific engagement metrics.",
    category: "Analyze"
  },
  {
    image: "/images/website_analytics_evaluator.png",
    title: "Website Analytics Evaluator",
    subtitle: "Analyze web traffic patterns",
    description: "Visualize visitor behavior, conversion funnels, and user journey friction.",
    websiteLink: "https://lutra.ai/shared/oUIfFiT17wQ",
    metrics: [
      "Visitor retention",
      "Conversion improvement",
      "UX optimization",
      "Revenue impact"
    ],
    capabilities: "Evaluates website performance from analytics data.",
    category: "Analyze"
  },
  {
    image: "/images/business_intelligence_analyst.png",
    title: "Business Intelligence Analyst",
    subtitle: "Aggregate business data into insights",
    description: "Analyze sales, operations, customer and financial data across departments.",
    websiteLink: "https://lutra.ai/shared/lGkBQaHW-As",
    metrics: [
      "Data completeness",
      "Insight actionability",
      "Executive adoption",
      "Revenue lift"
    ],
    capabilities: "Creates integrated business intelligence dashboards.",
    category: "Analyze"
  },
     {
    image: "/images/ab_testing_results_analyst.png",
    title: "A/B Testing Results Analyst",
    subtitle: "Evaluate A/B test outcomes",
    description: "Assess statistical significance and optimization recommendations based on test results.",
    websiteLink: "https://lutra.ai/shared/u98d7CBaGTs",
    metrics: [
      "Test validity",
      "Variant significance",
      "Conversion improvement",
      "Iteration speed"
    ],
    capabilities: "Analyzes A/B tests to guide product optimization.",
    category: "Analyze"
  },
   {
     "image": "/images/sales_deal_risk_detector.png",
     "title": "Sales Deal Risk Detector",
     "subtitle": "Spot red flags in your pipeline early",
     "description": "Analyze CRM data and conversation transcripts to flag deals with low closing probability.",
     "websiteLink": "https://lutra.ai/shared/TRJKTPH3slI",
     "metrics": [
       "Prediction accuracy",
       "False positive rate",
       "Deal closure rate",
       "User trust"
     ],
     "capabilities": "Detects risky deals in sales pipelines.",
     "category": "Analyze"
   },
   {
     "image": "/images/customer_support_ticket_prioritizer.png",
     "title": "Customer Support Ticket Prioritizer",
     "subtitle": "Automatically triage and escalate urgent support tickets",
     "description": "Categorizes tickets by severity and topic, highlighting issues needing immediate attention.",
     "websiteLink": "https://lutra.ai/shared/TO5eMUetS1I",
     "metrics": [
       "Prioritization accuracy",
       "Response time reduction",
       "Customer satisfaction",
       "Ticket resolution rate"
     ],
     "capabilities": "Prioritizes support tickets by urgency and topic.",
     "category": "Analyze"
   },
    {
    image: "/images/blog_post_writer.png",
    title: "Blog Post Writer",
    subtitle: "Generate complete SEO-optimized blog posts",
    description: "Produce fully written blog posts tailored to audience, topic, and SEO goals.",
    websiteLink: "https://lutra.ai/shared/AGXi3TCSCzU",
    metrics: [
      "SEO score",
      "Readability score",
      "Time saved",
      "Edit rate"
    ],
    capabilities: "Generates complete, SEO-optimized blog posts from topics.",
    category: "Creator"
  },
  {
    image: "/images/data_trend_analyzer.png",
    title: "Data Trend Analyzer",
    subtitle: "Analyze trends in time-series data",
    description: "Visualize, compare, and extract insights from performance or operational data over time.",
    websiteLink: "https://lutra.ai/shared/RxmHpW5SiJ8",
    metrics: [
      "Trend accuracy",
      "Insight quality",
      "Time saved",
      "Data coverage"
    ],
    capabilities: "Analyzes time-series data and extracts actionable trends.",
    category: "Analyze"
  },
   {
     "image": "/images/product_naming_wizard.png",
     "title": "Product Naming Wizard",
     "subtitle": "Catchy, brand‑safe names generated instantly",
     "description": "Provide concept and audience. Agent proposes 10 names with domain availability and trademark risk flags.",
     "websiteLink": "https://lutra.ai/shared/yQtWCuf9nZc",
     "metrics": [
       "Name uniqueness",
       "Domain availability",
       "Selection rate",
       "Trademark issues avoided"
     ],
     "capabilities": "Generates product names with domain and trademark checks.",
     "category": "Creator"
   },
   {
     "image": "/images/brand_voice_style_guide_creator.png",
     "title": "Brand Voice Style Guide Creator",
     "subtitle": "Codify your tone in minutes",
     "description": "Paste content samples or answer a quiz. Agent builds a concise style guide with voice principles and sample phrases.",
     "websiteLink": "https://lutra.ai/shared/hQtX_fq_Ht4",
     "metrics": [
       "Guide completeness",
       "Team adoption",
       "Consistency improvement",
       "Revision frequency"
     ],
     "capabilities": "Creates brand voice style guides quickly.",
     "category": "Creator"
   },
   {
     "image": "/images/youtube_title_and_thumbnail_generator.png",
     "title": "YouTube Title + Thumbnail Generator",
     "subtitle": "Boost your click-throughs with compelling visuals",
     "description": "Enter your video topic and tone, and receive 3–5 optimized titles and thumbnail ideas.",
     "websiteLink": "https://lutra.ai/shared/PjAudl4GSkg",
     "metrics": [
       "CTR improvement",
       "Engagement rate",
       "Creator rating",
       "Title relevance"
     ],
     "capabilities": "Generates optimized YouTube titles and thumbnails.",
     "category": "Creator"
   },
   {
     "image": "/images/e-book_formatter_agent.png",
     "title": "E-book Formatter Agent",
     "subtitle": "Turn long-form writing into beautiful e-books",
     "description": "Upload a Google Doc and get a stylized, mobile-friendly ePub or PDF version.",
     "websiteLink": "https://lutra.ai/shared/6eq2HdGSFoU",
     "metrics": [
       "Design quality",
       "Conversion success",
       "Time saved",
       "Reader feedback"
     ],
     "capabilities": "Formats documents into stylish e-books.",
     "category": "Creator"
   },
   {
     "image": "/images/podcast_episode_packager.png",
     "title": "Podcast Episode Packager",
     "subtitle": "Turn a raw podcast into social-ready assets",
     "description": "Upload an audio file and get a summary, title, episode description, social captions, and quote cards.",
     "websiteLink": "https://lutra.ai/shared/_G1thqeErUE",
     "metrics": [
       "Time saved",
       "Engagement on assets",
       "Download uplift",
       "Edit rate"
     ],
     "capabilities": "Packages podcasts into social media assets.",
     "category": "Creator"
   },
 ]

  const categories = ["Creator", "Education", "Analyze", "Automate", "Code", "Productivity"];

  const [selectedCategory, setSelectedCategory] = useState(null);

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
    window.open(websiteLink, "_blank", "noopener,noreferrer");
  };

  const handleMoreInfo = (e, agent) => {
    e.stopPropagation();
    openModal(agent);
  };
  const normalize = (str) => str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

  // Filter agents based on selectedCategory; show all if none selected
  const filteredAgents = useMemo(() => {
  let filtered = selectedCategory
    ? agents.filter((agent) => agent.category === selectedCategory)
    : agents;

  if (searchTerm) {
    filtered = filtered.filter((agent) => {
      const target = `${agent.title} ${agent.subtitle} ${agent.description} ${agent.capabilities}`;
      return normalize(target).includes(normalize(searchTerm));
    });
  }

  return filtered;
}, [selectedCategory, searchTerm]);


  return (
    <div className="min-h-screen px-5 lg:px-32 py-24">
      <h1 className="text-center text-5xl font-extrabold text-white mb-6 tracking-tight">Agent Registry</h1>

      {/* Category selector */}
      <div className="flex justify-center flex-wrap gap-4 mb-12">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-4 py-2 rounded-full font-semibold ${
            selectedCategory === null
              ? "bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black"
              : "bg-gray-700 text-white hover:bg-gray-600"
          }`}
        >
          All
        </button>

        {categories.map((category) => (
          <button
            key={category}
            onClick={() =>
              setSelectedCategory((prev) => (prev === category ? null : category))
            }
            className={`px-4 py-2 rounded-full font-semibold ${
              selectedCategory === category
                ? "bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black"
                : "bg-gray-700 text-white hover:bg-gray-600"
            }`}
          >
            {category}
          </button>
        ))}
      </div>

<div className="flex justify-center mb-12">
  <input
    type="text"
    placeholder="🔎 Search agents by title, subtitle, or capabilities..."
    className="w-full md:w-1/2 p-4 rounded-xl text-white bg-gray-700 text-lg shadow-lg border border-gray-600 focus:outline-none focus:ring-4 focus:ring-blue-400"
    value={searchTerm}
    onChange={(e) => setSearchTerm(e.target.value)}
  />
</div>

<div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-12">
  {filteredAgents.length > 0 ? (
    filteredAgents.map((agent, index) => (
      <div
        key={index}
        className="bg-[#161616] border border-[#2a2a2a] rounded-3xl shadow-lg overflow-hidden transform transition-transform hover:-translate-y-3 hover:shadow-xl cursor-pointer group"
        onClick={() => window.open(agent.websiteLink, "_blank", "noopener,noreferrer")}
      >
        <div className="relative w-full h-56 overflow-hidden">
          <img
            src={agent.image}
            alt={agent.title}
            className="w-full h-full object-cover object-center transition-opacity duration-300 group-hover:opacity-30"
          />
          <div className="absolute inset-0 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 space-y-4">
            <div className="bg-white bg-opacity-80 rounded-full p-4 shadow-lg">
              <FaPlay className="text-black text-3xl" />
            </div>
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
    ))
  ) : (
    <p className="text-gray-500 italic col-span-full text-center">
      No agents available in this category.
    </p>
  )}
</div>


      {/* Modal */}
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
              <h2 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">
                About
              </h2>
              <p className="text-md">{selectedAgent.description}</p>
            </section>

            {/* Key Metrics */}
            {selectedAgent.metrics && selectedAgent.metrics.length > 0 && (
              <section className="mb-8">
                <h3 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">
                  Key Metrics
                </h3>
                <ul className="list-disc list-inside text-md space-y-1">
                  {selectedAgent.metrics.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </section>
            )}

            {/* Features */}
            {selectedAgent.features && selectedAgent.features.length > 0 && (
              <section className="mb-8">
                <h3 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">
                  Features
                </h3>
                <ul className="list-disc list-inside text-md space-y-1">
                  {selectedAgent.features.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </section>
            )}

            {/* Use Cases */}
            {selectedAgent.useCases && selectedAgent.useCases.length > 0 && (
              <section className="mb-8">
                <h3 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">
                  Use Cases
                </h3>
                <ul className="list-disc list-inside text-md space-y-1">
                  {selectedAgent.useCases.map((u, i) => (
                    <li key={i}>{u}</li>
                  ))}
                </ul>
              </section>
            )}

            {/* Capabilities */}
            {selectedAgent.capabilities && (
              <section className="mb-10">
                <h3 className="text-2xl font-semibold mb-3 text-gradient bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent">
                  Capabilities
                </h3>
                <p className="text-md leading-relaxed">{selectedAgent.capabilities}</p>
              </section>
            )}

            <a
              href={selectedAgent.websiteLink}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black px-6 py-3 rounded-full font-semibold text-lg hover:scale-105 transition-transform"
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
