import React, { useState } from "react";

function Registry() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);

  const agents = [
   {
     "image": "/images/one-pager_builder_agent.png",
     "title": "One-Pager Builder Agent",
     "subtitle": "Create a GTM-ready sales sheet in minutes",
     "description": "Input your product description, key features, and audience. This agent auto-generates a slick, well-formatted one-pager for sales or fundraising—editable in Google Docs or Canva.",
     "websiteLink": "https://lutra.ai/shared/pNUzcBzkf08",
     "metrics": [
       "Visual/content quality",
       "Time saved",
       "Adoption rate",
       "Edit rate"
     ],
     "capabilities": "Creates well-formatted one-pagers quickly for sales or fundraising.",
     "category": "Creator"
   },
   {
     "image": "/images/meeting-to-newsletter_generator.png",
     "title": "Meeting-to-Newsletter Generator",
     "subtitle": "Turn Zoom notes into a polished update for your audience",
     "description": "Upload transcripts or notes. Agent structures into blog, memo, or newsletter. Ideal for content creators.",
     "websiteLink": "https://lutra.ai/shared/Y88uufxJGgk",
     "metrics": [
       "Output quality",
       "Time saved",
       "Share rate",
       "Edit rate"
     ],
     "capabilities": "Structures meeting notes into polished newsletters or blogs.",
     "category": "Creator"
   },
   {
     "image": "/images/smart_newsletter_engine.png",
     "title": "Smart Newsletter Engine",
     "subtitle": "Personalized newsletters tailored to each account",
     "description": "Dynamically personalizes newsletters based on reader’s company or behavior. Integrates with HubSpot, Mailchimp.",
     "websiteLink": "https://lutra.ai/shared/tCs6cw6hA-w",
     "metrics": [
       "Open/CTR rate",
       "Time saved",
       "Segment engagement"
     ],
     "capabilities": "Personalizes newsletters dynamically per account using integrations.",
     "category": "Creator"
   },
   {
     "image": "/images/zoom_background_generator.png",
     "title": "Zoom Background Generator",
     "subtitle": "Make a custom AI-generated Zoom background to match your vibe",
     "description": "Choose a theme and get a downloadable, stylized background.",
     "websiteLink": "",
     "metrics": [
       "Downloads",
       "Rating",
       "Reuse",
       "Virality"
     ],
     "capabilities": "Generates custom AI Zoom backgrounds by theme.",
     "category": "Creator"
   },
   {
     "image": "/images/deck_designer_agent.png",
     "title": "Deck Designer Agent",
     "subtitle": "Pitch-ready slides from a prompt",
     "description": "Input your pitch or topic, and the agent generates a full presentation deck with visuals, talking points, and speaker notes.",
     "websiteLink": "",
     "metrics": [
       "Time saved",
       "Slide design quality",
       "Usage rate",
       "Edit rate"
     ],
     "capabilities": "Generates presentation decks from prompts.",
     "category": "Creator"
   },
   {
     "image": "/images/ad_copy_brainstormer.png",
     "title": "Ad Copy Brainstormer",
     "subtitle": "Fresh ad angles in seconds",
     "description": "Provide product and audience; receive multiple ad variants in different tones (funny, urgent, premium, etc).",
     "websiteLink": "",
     "metrics": [
       "CTR improvement",
       "Variant diversity",
       "User preference selection",
       "Reuse rate"
     ],
     "capabilities": "Generates multiple ad variants with different tones.",
     "category": "Creator"
   },
   {
     "image": "/images/blog_post_outline_generator.png",
     "title": "Blog Post Outline Generator",
     "subtitle": "From headline to structured article in seconds",
     "description": "Enter your topic or headline, and the agent generates a coherent outline with headers, word counts, and internal link suggestions.",
     "websiteLink": "",
     "metrics": [
       "Outline coherence",
       "SEO coverage",
       "Time saved",
       "Edit rate"
     ],
     "capabilities": "Creates structured blog outlines with SEO suggestions.",
     "category": "Creator"
   },
   {
     "image": "/images/infographic_builder.png",
     "title": "Infographic Builder",
     "subtitle": "Data‑driven visuals without a designer",
     "description": "Upload data or pick a template; the agent crafts a polished infographic with charts, icons, and captions.",
     "websiteLink": "",
     "metrics": [
       "Visual appeal",
       "Data accuracy",
       "Creation time",
       "Share rate"
     ],
     "capabilities": "Creates infographics from data quickly.",
     "category": "Creator"
   },
   {
     "image": "/images/product_naming_wizard.png",
     "title": "Product Naming Wizard",
     "subtitle": "Catchy, brand‑safe names generated instantly",
     "description": "Provide concept and audience. Agent proposes 10 names with domain availability and trademark risk flags.",
     "websiteLink": "",
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
     "websiteLink": "",
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
     "image": "/images/social_media_carousel_designer.png",
     "title": "Social Media Carousel Designer",
     "subtitle": "Scroll‑stopping multi‑slide posts in one go",
     "description": "Input message and platform; agent designs a 3‑5 slide carousel with copy, layout, and visual prompts.",
     "websiteLink": "",
     "metrics": [
       "Engagement (saves/shares)",
       "Slide clarity",
       "Time saved",
       "Edit rate"
     ],
     "capabilities": "Designs social media carousels from input messages.",
     "category": "Creator"
   },
   {
     "image": "/images/youtube_title_+_thumbnail_generator.png",
     "title": "YouTube Title + Thumbnail Generator",
     "subtitle": "Boost your click-throughs with compelling visuals",
     "description": "Enter your video topic and tone, and receive 3–5 optimized titles and thumbnail ideas.",
     "websiteLink": "",
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
     "image": "/images/tiktok_script_writer.png",
     "title": "TikTok Script Writer",
     "subtitle": "Create engaging short-form scripts instantly",
     "description": "Provide your content idea and audience; agent returns a 15–60 second hook‑based script.",
     "websiteLink": "",
     "metrics": [
       "Retention time",
       "Completion rate",
       "Edit frequency",
       "View count"
     ],
     "capabilities": "Creates engaging TikTok scripts quickly.",
     "category": "Creator"
   },
   {
     "image": "/images/e-book_formatter_agent.png",
     "title": "E-book Formatter Agent",
     "subtitle": "Turn long-form writing into beautiful e-books",
     "description": "Upload a Google Doc and get a stylized, mobile-friendly ePub or PDF version.",
     "websiteLink": "",
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
     "websiteLink": "",
     "metrics": [
       "Time saved",
       "Engagement on assets",
       "Download uplift",
       "Edit rate"
     ],
     "capabilities": "Packages podcasts into social media assets.",
     "category": "Creator"
   },
   {
     "image": "/images/outreach_follow-up_tree_builder.png",
     "title": "Outreach Follow-Up Tree Builder",
     "subtitle": "Auto-generate a sequence of 3–5 follow-up emails based on intent",
     "description": "Describe the outreach context, and this agent crafts a follow-up sequence with variations for no-response, soft interest, or bounce.",
     "websiteLink": "https://lutra.ai/shared/BztORfXlBUk",
     "metrics": [
       "Response uplift",
       "Sequence clarity",
       "Personalization depth",
       "Edit frequency"
     ],
     "capabilities": "Creates personalized follow-up email sequences.",
     "category": "Creator"
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "image": "/images/product_feedback_summarizer.png",
     "title": "Product Feedback Summarizer",
     "subtitle": "Condense hundreds of user reviews into actionable insights",
     "description": "Upload raw feedback data, and the agent extracts themes, sentiment, and top requests.",
     "websiteLink": "",
     "metrics": [
       "Insight accuracy",
       "Time saved",
       "Actionability",
       "Stakeholder adoption"
     ],
     "capabilities": "Summarizes user feedback into clear insights.",
     "category": "Analyze"
   },
   {
     "image": "/images/sales_deal_risk_detector.png",
     "title": "Sales Deal Risk Detector",
     "subtitle": "Spot red flags in your pipeline early",
     "description": "Analyze CRM data and conversation transcripts to flag deals with low closing probability.",
     "websiteLink": "",
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
     "websiteLink": "",
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
     "image": "/images/seo_keyword_expander.png",
     "title": "SEO Keyword Expander",
     "subtitle": "Grow your keyword list with AI-powered suggestions",
     "description": "Input seed keywords and get long-tail variations, search volumes, and competition metrics.",
     "websiteLink": "",
     "metrics": [
       "Keyword relevance",
       "List size",
       "CTR improvement",
       "Ranking uplift"
     ],
     "capabilities": "Expands keyword lists with relevant variants.",
     "category": "Analyze"
   },
   {
     "image": "/images/market_trend_analyzer.png",
     "title": "Market Trend Analyzer",
     "subtitle": "Spot emerging trends from news and social media",
     "description": "Aggregates signals from various sources to highlight rising topics relevant to your industry.",
     "websiteLink": "",
     "metrics": [
       "Trend detection accuracy",
       "Signal-to-noise ratio",
       "Time saved",
       "User engagement"
     ],
     "capabilities": "Detects emerging market trends.",
     "category": "Analyze"
   },
   {
     "image": "/images/competitor_pricing_monitor.png",
     "title": "Competitor Pricing Monitor",
     "subtitle": "Track competitor prices and promotions automatically",
     "description": "Scrapes competitor sites and flags pricing changes and campaigns for your product category.",
     "websiteLink": "",
     "metrics": [
       "Detection accuracy",
       "Alert speed",
       "Competitive action rate",
       "ROI impact"
     ],
     "capabilities": "Monitors competitor pricing and promotions.",
     "category": "Analyze"
   },
   {
     "image": "/images/financial_report_summarizer.png",
     "title": "Financial Report Summarizer",
     "subtitle": "Condense quarterly and annual reports into digestible highlights",
     "description": "Extracts key financial metrics, management commentary, and risk factors.",
     "websiteLink": "",
     "metrics": [
       "Summary accuracy",
       "Time saved",
       "User satisfaction",
       "Decision support"
     ],
     "capabilities": "Summarizes financial reports effectively.",
     "category": "Analyze"
   },
   {
     "image": "/images/expense_categorization_agent.png",
     "title": "Expense Categorization Agent",
     "subtitle": "Automatically categorize business expenses from receipts",
     "description": "Upload receipts or expense data; agent classifies and summarizes for accounting.",
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
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
     "image": "/images/smart_calendar_scheduler.png",
     "title": "Smart Calendar Scheduler",
     "subtitle": "Find optimal meeting times, hassle-free",
     "description": "Integrate your calendar, and the agent suggests the best slots for meetings based on priorities, availability, and preferences.",
     "websiteLink": "",
     "metrics": [
       "Scheduling success rate",
       "Conflict reduction",
       "User time saved",
       "Reschedule frequency"
     ],
     "capabilities": "Suggests optimal meeting times based on calendar data.",
     "category": "Productivity"
   },
   {
     "image": "/images/email_tone_checker.png",
     "title": "Email Tone Checker",
     "subtitle": "Craft emails with the right tone every time",
     "description": "Paste your draft emails, and the agent suggests improvements for tone, politeness, clarity, and conciseness.",
     "websiteLink": "",
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
     "websiteLink": "",
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
     "websiteLink": "",
     "metrics": [
       "Summary accuracy",
       "User engagement",
       "Helpdesk ticket reduction",
       "Time saved"
     ],
     "capabilities": "Summarizes large documents into key points and FAQs.",
     "category": "Productivity"
   }
 ]


  // const categories = ["Education", "Analyze", "Automate", "Code", "Productivity"];
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

  // Filter agents based on selectedCategory; show all if none selected
  const filteredAgents = selectedCategory
    ? agents.filter((agent) => agent.category === selectedCategory)
    : agents;

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

      {/* Agents grid */}
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
