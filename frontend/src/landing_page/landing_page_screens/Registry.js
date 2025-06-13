import React, { useState } from "react";

function Registry() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);

  const agents = [
    {
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-JtVZYLbU3W80cCwbouJoBbA7.png?st=2025-06-13T17%3A45%3A08Z&se=2025-06-13T19%3A45%3A08Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T12%3A46%3A11Z&ske=2025-06-14T12%3A46%3A11Z&sks=b&skv=2024-08-04&sig=SD/marFNEbuo3GdssrzgLAtDXERDmGAtjvDXQTFcAJI%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-VXX9RZQYlo0FKyzzv6vhPGyA.png?st=2025-06-13T17%3A45%3A28Z&se=2025-06-13T19%3A45%3A28Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T06%3A54%3A26Z&ske=2025-06-14T06%3A54%3A26Z&sks=b&skv=2024-08-04&sig=Cg3Qy2sA8SGkRmyD7G734mk0DEMlgSpjK2GC%2BGl9yN8%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-rIVuDSiqVcWxzM5FIIPzkWrW.png?st=2025-06-13T17%3A45%3A47Z&se=2025-06-13T19%3A45%3A47Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T05%3A00%3A43Z&ske=2025-06-14T05%3A00%3A43Z&sks=b&skv=2024-08-04&sig=1be63zImL75hCnpytf2i1YNnoz3ivgSoxlQhSCLYgvY%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-5Z3ghfH0j5x89gL0CTtMwMFW.png?st=2025-06-13T17%3A46%3A08Z&se=2025-06-13T19%3A46%3A08Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T13%3A41%3A19Z&ske=2025-06-14T13%3A41%3A19Z&sks=b&skv=2024-08-04&sig=auWCSs76e5kZLoCbmJU6gyQp1sfuvET9tanY9IUFXms%3D",
      "title": "Zoom Background Generator",
      "subtitle": "Make a custom AI-generated Zoom background to match your vibe",
      "description": "Choose a theme and get a downloadable, stylized background.",
      "websiteLink": "https://lutra.ai/shared/kG1KV0a_V8c",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-xrgpfjSnd5Bd0O90ouGbOhiu.png?st=2025-06-13T17%3A46%3A30Z&se=2025-06-13T19%3A46%3A30Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T10%3A58%3A24Z&ske=2025-06-14T10%3A58%3A24Z&sks=b&skv=2024-08-04&sig=QENMFq7FYYQ%2BK%2BlXwtMUnyQB2zvyRYSyDLcvuy5vjfs%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-5rxpkvSxIbecKWmuMQjVayfK.png?st=2025-06-13T17%3A47%3A08Z&se=2025-06-13T19%3A47%3A08Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T12%3A46%3A50Z&ske=2025-06-14T12%3A46%3A50Z&sks=b&skv=2024-08-04&sig=CBOsLxATE%2BKYUhzXwyhEoEXPMB1rmydEjdTbk1zgA5k%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-Tju2bQva3MQEhN6Vjmha4u6K.png?st=2025-06-13T17%3A47%3A31Z&se=2025-06-13T19%3A47%3A31Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T08%3A29%3A37Z&ske=2025-06-14T08%3A29%3A37Z&sks=b&skv=2024-08-04&sig=qg5uZTiTWnyUKa5TLJg5Tig%2BNYhZ1OO1o66cxr2zfLk%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-NhjZi5NQwxUxgi3q435I48Zv.png?st=2025-06-13T17%3A47%3A51Z&se=2025-06-13T19%3A47%3A51Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T15%3A19%3A01Z&ske=2025-06-14T15%3A19%3A01Z&sks=b&skv=2024-08-04&sig=0Ki3T2hvKfKatlP1S8ceY7qFLwxzuAK0EkpnhhJ2MnI%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-iNg1cpL6tdSI15KNC5Wd7wzE.png?st=2025-06-13T17%3A48%3A09Z&se=2025-06-13T19%3A48%3A09Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T11%3A47%3A39Z&ske=2025-06-14T11%3A47%3A39Z&sks=b&skv=2024-08-04&sig=lpyhld46/E3tbvgdH7ia54EtTy%2B0O3hijjG10iFfihM%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-W1jxb6ZH8y0j6nycCa5LsbeA.png?st=2025-06-13T17%3A48%3A29Z&se=2025-06-13T19%3A48%3A29Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T14%3A35%3A22Z&ske=2025-06-14T14%3A35%3A22Z&sks=b&skv=2024-08-04&sig=qFUtUM1IDbCts6itDESmJ1XadbkAgvT7sXhWbk0s7JI%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-EPW1Brn3aOYtOLddTrvmTKAl.png?st=2025-06-13T17%3A48%3A49Z&se=2025-06-13T19%3A48%3A49Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T01%3A37%3A55Z&ske=2025-06-14T01%3A37%3A55Z&sks=b&skv=2024-08-04&sig=cPs996Ct9ue5SBTA%2BOphKj9FIZcbCKfpP1t5%2B1BSAaU%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-bfgL02UUBj8RbAsoIZ1druqn.png?st=2025-06-13T17%3A49%3A07Z&se=2025-06-13T19%3A49%3A07Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T13%3A17%3A40Z&ske=2025-06-14T13%3A17%3A40Z&sks=b&skv=2024-08-04&sig=qG9K628SpalA0nWHftkw0aw6pem5rm0GnK6/bzsbPPc%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-QYgvZdbKTBrByl3Tzbm1riWe.png?st=2025-06-13T17%3A49%3A28Z&se=2025-06-13T19%3A49%3A28Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T15%3A40%3A41Z&ske=2025-06-14T15%3A40%3A41Z&sks=b&skv=2024-08-04&sig=XW/0V1Vx8Qx0AW0RGVUc5dyPSvJI2hRVLBwbZniVu%2Bg%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-i7DPJ1XJcRZVICRRoOkC7AjK.png?st=2025-06-13T17%3A49%3A52Z&se=2025-06-13T19%3A49%3A52Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T13%3A16%3A06Z&ske=2025-06-14T13%3A16%3A06Z&sks=b&skv=2024-08-04&sig=AL%2BhOFGh1Ln3qgjcrW9umllywNvrQKDqK48f0DCEdC4%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-e1rwEfWDCEQgMxNL56PmmEPL.png?st=2025-06-13T17%3A50%3A13Z&se=2025-06-13T19%3A50%3A13Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-12T22%3A17%3A13Z&ske=2025-06-13T22%3A17%3A13Z&sks=b&skv=2024-08-04&sig=OgrfdfksLG2NlqYaRugW7KdN/bvrlMtz0bJsyf/YvDU%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-LYaozLZaHA7TUAAyDHWeS19k.png?st=2025-06-13T17%3A50%3A32Z&se=2025-06-13T19%3A50%3A32Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-12T23%3A29%3A59Z&ske=2025-06-13T23%3A29%3A59Z&sks=b&skv=2024-08-04&sig=f9tXjQ2bjWoIfp/tEheSbgREk3S1WyNMwCS6fFKnBNE%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-SyU8xSfoc8YgS2gI6WGEgPck.png?st=2025-06-13T17%3A50%3A52Z&se=2025-06-13T19%3A50%3A52Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T02%3A59%3A52Z&ske=2025-06-14T02%3A59%3A52Z&sks=b&skv=2024-08-04&sig=BdP59hR6TIIZ9PwtVxREyRcVvBy1W5QlaQh7pUlH/ZA%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-sogmvMzhhWo6PVRAu4PGThEu.png?st=2025-06-13T17%3A51%3A12Z&se=2025-06-13T19%3A51%3A12Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T08%3A16%3A38Z&ske=2025-06-14T08%3A16%3A38Z&sks=b&skv=2024-08-04&sig=fmM44bCe601NydhJ8lEWop1byd4iilTFlc9rqfWYfUg%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-oZdb3kRoDrdjQXh6yUllGc4b.png?st=2025-06-13T17%3A51%3A34Z&se=2025-06-13T19%3A51%3A34Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T01%3A41%3A11Z&ske=2025-06-14T01%3A41%3A11Z&sks=b&skv=2024-08-04&sig=5PZtkLKK4X/CeNLqhzGZJPTqq2mWLx6WMYtn%2BVT6/8Q%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-hqNvUNDYCAuNQU2LJbEff8ej.png?st=2025-06-13T17%3A51%3A53Z&se=2025-06-13T19%3A51%3A53Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T03%3A46%3A06Z&ske=2025-06-14T03%3A46%3A06Z&sks=b&skv=2024-08-04&sig=yXaOEKS%2BRMtSHhwHeckmMR97PbIesBl91FKEA5D72sk%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-0vYlQplrnyn8mjboS6j5D3jx.png?st=2025-06-13T17%3A52%3A10Z&se=2025-06-13T19%3A52%3A10Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T07%3A04%3A12Z&ske=2025-06-14T07%3A04%3A12Z&sks=b&skv=2024-08-04&sig=rcZJoA%2BgHOZVZOTBYXtPMscZ2Pmq5QnOQ%2Bxvm75zPsI%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-wD0N6Hc4XQQTq5AmJy50I3JS.png?st=2025-06-13T17%3A52%3A32Z&se=2025-06-13T19%3A52%3A32Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T14%3A46%3A04Z&ske=2025-06-14T14%3A46%3A04Z&sks=b&skv=2024-08-04&sig=Uc43tUSYdG/tJO4lbtzxBzV5Rv8nJLAUK87Qq8gU48g%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-0jYBoIUNxu3doFz8BJUcH4GT.png?st=2025-06-13T17%3A52%3A53Z&se=2025-06-13T19%3A52%3A53Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-12T20%3A10%3A40Z&ske=2025-06-13T20%3A10%3A40Z&sks=b&skv=2024-08-04&sig=vpk6wwjex5vRGZkhkFlWSG0i7ICVyNtsGKY46YYqHP4%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-86qH2TLLdhyzcBENKotm3gi9.png?st=2025-06-13T17%3A53%3A13Z&se=2025-06-13T19%3A53%3A13Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T15%3A50%3A46Z&ske=2025-06-14T15%3A50%3A46Z&sks=b&skv=2024-08-04&sig=LT4KUOVn00gAoFxipvDa7w6YPAVDk3Hb8adQaClNNSo%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-1nJNYJjsfLfliRavFQ3rin42.png?st=2025-06-13T17%3A53%3A33Z&se=2025-06-13T19%3A53%3A33Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T15%3A27%3A05Z&ske=2025-06-14T15%3A27%3A05Z&sks=b&skv=2024-08-04&sig=kDz3ZtQ61oNGbpXhysuWLE4QeggCUAKsG3x2XaisbT0%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-Nn6aWEVqxnKXdMfBKOQpknDJ.png?st=2025-06-13T17%3A53%3A52Z&se=2025-06-13T19%3A53%3A52Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T17%3A52%3A42Z&ske=2025-06-14T17%3A52%3A42Z&sks=b&skv=2024-08-04&sig=l0R9SUYCTRQkrX5VkTYK7oOVy6dz5mll1aTKnLkxXaA%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-c2UvwwdUNJf6YSbLiLFit0ew.png?st=2025-06-13T17%3A54%3A09Z&se=2025-06-13T19%3A54%3A09Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T09%3A32%3A57Z&ske=2025-06-14T09%3A32%3A57Z&sks=b&skv=2024-08-04&sig=IYPrQtYTtgX8lkEkPU/I5BbwOzcVBhQXDXoYcp0dgNk%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-SZ8CFzoYI0qkNNmet5fnzTOg.png?st=2025-06-13T17%3A54%3A28Z&se=2025-06-13T19%3A54%3A28Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T14%3A13%3A05Z&ske=2025-06-14T14%3A13%3A05Z&sks=b&skv=2024-08-04&sig=Qq4vfXkvaFkoff6SdBNByRdwzzlgLIVGU5r%2B8LKRsO0%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-gpZx1rYNdraezorjgw8HnHBG.png?st=2025-06-13T17%3A54%3A47Z&se=2025-06-13T19%3A54%3A47Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T14%3A55%3A25Z&ske=2025-06-14T14%3A55%3A25Z&sks=b&skv=2024-08-04&sig=a/xD8S574PVqS1pMXQlHcyIvuLmvE1szNzXuFwmaxVM%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-xwMRznehkmDjoPcaOj2ypqtH.png?st=2025-06-13T17%3A55%3A07Z&se=2025-06-13T19%3A55%3A07Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T14%3A55%3A29Z&ske=2025-06-14T14%3A55%3A29Z&sks=b&skv=2024-08-04&sig=UEv6jYqDlojEY0g/xtACxmiR/4tOubseXo2fI722T2o%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-rupfnnNZFxCdB5bxI07g1RAk.png?st=2025-06-13T17%3A55%3A27Z&se=2025-06-13T19%3A55%3A27Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T06%3A08%3A13Z&ske=2025-06-14T06%3A08%3A13Z&sks=b&skv=2024-08-04&sig=Aksrh4nPogFcdLOORp8eLW%2BAb7fIwRd7ysMRiMnAfCw%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-2bFxhOBAStacsAHaWaiuDLS1.png?st=2025-06-13T17%3A55%3A46Z&se=2025-06-13T19%3A55%3A46Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T16%3A33%3A53Z&ske=2025-06-14T16%3A33%3A53Z&sks=b&skv=2024-08-04&sig=8aM7NkYyLMbXb4DoxKH/6bUdM196hPmg9C9rYPf8RUg%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-J7n02vZmursb14ESQjYhAThE.png?st=2025-06-13T17%3A56%3A05Z&se=2025-06-13T19%3A56%3A05Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T00%3A00%3A07Z&ske=2025-06-14T00%3A00%3A07Z&sks=b&skv=2024-08-04&sig=5iJmmkoJO2/1NSDUxZbTNpmciyCafZwUp87L7/OG0xY%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-WGoOMfJ4RCpxKvlQ3Gt0wsst.png?st=2025-06-13T17%3A56%3A30Z&se=2025-06-13T19%3A56%3A30Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T00%3A54%3A32Z&ske=2025-06-14T00%3A54%3A32Z&sks=b&skv=2024-08-04&sig=NuetZS6aFW0gb4qZXSu016M/Brqa%2BuRfQgFbBLOzo%2Bs%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-qCGmKxGrHRgsCnUAeZyoktQB.png?st=2025-06-13T17%3A56%3A51Z&se=2025-06-13T19%3A56%3A51Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T18%3A37%3A06Z&ske=2025-06-14T18%3A37%3A06Z&sks=b&skv=2024-08-04&sig=pkNSf/UATPm4unz9OKuTtg9DbsKEllSHmq0Z9ORH1aA%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-J2YT6qPWmt3ksB4L4xW5CtTw.png?st=2025-06-13T17%3A57%3A23Z&se=2025-06-13T19%3A57%3A23Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T13%3A05%3A37Z&ske=2025-06-14T13%3A05%3A37Z&sks=b&skv=2024-08-04&sig=Uu6VF8pkHAMdPoRmFpmpEzkCEGOXMFikILa/2hqDQ6U%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-D1IqFlmaT9jHjBaXRZkAPo5h.png?st=2025-06-13T17%3A57%3A42Z&se=2025-06-13T19%3A57%3A42Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T15%3A31%3A27Z&ske=2025-06-14T15%3A31%3A27Z&sks=b&skv=2024-08-04&sig=Y7rYsBzxjbWfzQnoyRr%2By6RrHu6yypoawo%2BRtAmJ6Gk%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-aalJwbV4bIKq8c6hIWK23BjO.png?st=2025-06-13T17%3A58%3A00Z&se=2025-06-13T19%3A58%3A00Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T14%3A33%3A01Z&ske=2025-06-14T14%3A33%3A01Z&sks=b&skv=2024-08-04&sig=gII2q5Zig0DTADUPdYi1Vh0LLLXNjL7TkEt4NMsdI3E%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-xItMG2CZjh4NdD8uYjWsQ2jw.png?st=2025-06-13T17%3A58%3A44Z&se=2025-06-13T19%3A58%3A44Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-12T23%3A26%3A28Z&ske=2025-06-13T23%3A26%3A28Z&sks=b&skv=2024-08-04&sig=OqEYZ7hg4iChKajNHzI1TeNyis9jqKyKC2Wwr8EBWGs%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-8vdlEDDNh7jHVRUCxFruF4Zi.png?st=2025-06-13T17%3A59%3A05Z&se=2025-06-13T19%3A59%3A05Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T15%3A07%3A46Z&ske=2025-06-14T15%3A07%3A46Z&sks=b&skv=2024-08-04&sig=Yn0ndbBH62SbtOB%2BBG%2B7jhujiqJujKIu4mMdED4euu0%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-DMzoPmpCIfavKZoRwQRwZYi9.png?st=2025-06-13T17%3A59%3A24Z&se=2025-06-13T19%3A59%3A24Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T05%3A54%3A26Z&ske=2025-06-14T05%3A54%3A26Z&sks=b&skv=2024-08-04&sig=xgwHd0tZEbwafOLk9DqZYHOpfzFsmQqMLeJETKueK0U%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-KIPu3FsoS02CIHYNx8PLzT3l.png?st=2025-06-13T17%3A59%3A47Z&se=2025-06-13T19%3A59%3A47Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T12%3A33%3A52Z&ske=2025-06-14T12%3A33%3A52Z&sks=b&skv=2024-08-04&sig=V9Rv8LAcfs90c1c%2BHff6SjrOTTl1KIi9LTE7VW%2BdCgk%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-ML1huNCkxabh9sB7K5kmTDhM.png?st=2025-06-13T18%3A00%3A07Z&se=2025-06-13T20%3A00%3A07Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T02%3A26%3A44Z&ske=2025-06-14T02%3A26%3A44Z&sks=b&skv=2024-08-04&sig=cn5WHxXKKhxUmibRmRgMjXfF/5axXQmj6As19pTYbek%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-drHtLFwSTNwFTbkMzDNNEnEm.png?st=2025-06-13T18%3A00%3A27Z&se=2025-06-13T20%3A00%3A27Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T17%3A35%3A56Z&ske=2025-06-14T17%3A35%3A56Z&sks=b&skv=2024-08-04&sig=uy3xlx80tWcirvtngZnH9GRVrxt4BrVy1%2BMDiIGNZiE%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-0tMA24qiCbefmZLNOi92mwgc.png?st=2025-06-13T18%3A00%3A47Z&se=2025-06-13T20%3A00%3A47Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T14%3A04%3A20Z&ske=2025-06-14T14%3A04%3A20Z&sks=b&skv=2024-08-04&sig=kM47golW80fq1cTU%2BJlLZyk3dYmy1YGpqJWU0ty18rk%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-wayy55v9soy4wGFmb2jIDFlU.png?st=2025-06-13T18%3A01%3A08Z&se=2025-06-13T20%3A01%3A08Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T10%3A20%3A08Z&ske=2025-06-14T10%3A20%3A08Z&sks=b&skv=2024-08-04&sig=wdVi19vVDmDkMuafxdxKfn6ym%2B7YaAGwk9xjQx/7r9w%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-pnT0T9z7LJbA7Z1Xs0E1R51t.png?st=2025-06-13T18%3A01%3A30Z&se=2025-06-13T20%3A01%3A30Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-12T20%3A36%3A45Z&ske=2025-06-13T20%3A36%3A45Z&sks=b&skv=2024-08-04&sig=y8LcTrdLPiB4l2O%2Bk%2BW5/j3G8qZ0YR3yW3On37UoiZI%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-zaixGP7huVQrwaklGbmPaWDt.png?st=2025-06-13T18%3A01%3A50Z&se=2025-06-13T20%3A01%3A50Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T11%3A46%3A08Z&ske=2025-06-14T11%3A46%3A08Z&sks=b&skv=2024-08-04&sig=44aPDMutpinS8FAm7eCVZLy/WMxXYEwTBk49ZKbXMSg%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-gyOOk1Sq6nKIX8XhZKLVgYtd.png?st=2025-06-13T18%3A02%3A10Z&se=2025-06-13T20%3A02%3A10Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T12%3A46%3A04Z&ske=2025-06-14T12%3A46%3A04Z&sks=b&skv=2024-08-04&sig=RtAiMF5Xqbu6MRgiEZwllVV1dBu%2Bdj7uwGnLWaisJic%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-jJSIX8KQOvR8jgK3tDuUMAi2.png?st=2025-06-13T18%3A03%3A09Z&se=2025-06-13T20%3A03%3A09Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T08%3A34%3A16Z&ske=2025-06-14T08%3A34%3A16Z&sks=b&skv=2024-08-04&sig=Tsu/Pa%2Bd1Ov/xB2Q4/rgqSdO06QaixPHo4XOdIRIFV8%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-XTO5aeQOfWz9yQh7qeQt9Y8b.png?st=2025-06-13T18%3A03%3A39Z&se=2025-06-13T20%3A03%3A39Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-12T19%3A48%3A27Z&ske=2025-06-13T19%3A48%3A27Z&sks=b&skv=2024-08-04&sig=jTwt6gGAiSvohp9OwnGbPDLxhxzpIj/j4RaVmTlKTxQ%3D",
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
    // {
    //   "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-s8jkGVimFuUa99GR2TeJnHVE.png?st=2025-06-13T18%3A03%3A59Z&se=2025-06-13T20%3A03%3A59Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-12T19%3A15%3A43Z&ske=2025-06-13T19%3A15%3A43Z&sks=b&skv=2024-08-04&sig=CutHTDzNU2FABfh7JegaMDaGl97FzWq5EvMmKldK7tU%3D",
    //   "title": "Email Tone Checker",
    //   "subtitle": "Craft emails with the right tone every time",
    //   "description": "Paste your draft emails, and the agent suggests improvements for tone, politeness, clarity, and conciseness.",
    //   "websiteLink": "",
    //   "metrics": [
    //     "Email response rate",
    //     "User satisfaction",
    //     "Edit frequency",
    //     "Miscommunication incidents"
    //   ],
    //   "capabilities": "Improves email drafts for tone and clarity.",
    //   "category": "Productivity"
    // },
    {
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-7r5KYiyupQmNfzM9c5gmrxyb.png?st=2025-06-13T18%3A04%3A18Z&se=2025-06-13T20%3A04%3A18Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T09%3A12%3A30Z&ske=2025-06-14T09%3A12%3A30Z&sks=b&skv=2024-08-04&sig=pph1om%2BvIpTgvnMJmZpPWN/tynprvoN5svZOsiE3tks%3D",
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
      "image": "https://oaidalleapiprodscus.blob.core.windows.net/private/org-WM0C8DmpfiXb4ySIeUGFLcf2/user-GIG8da8QuHRCXLaF6Wti6LCe/img-eif6POMKPECBfHGrg0hanfs5.png?st=2025-06-13T18%3A04%3A38Z&se=2025-06-13T20%3A04%3A38Z&sp=r&sv=2024-08-04&sr=b&rscd=inline&rsct=image/png&skoid=475fd488-6c59-44a5-9aa9-31c4db451bea&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-06-13T02%3A17%3A43Z&ske=2025-06-14T02%3A17%3A43Z&sks=b&skv=2024-08-04&sig=jOka4ghpoMKWRfBxEVpkgpgYsJbyV%2Bt13Pe/6mehhk8%3D",
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
