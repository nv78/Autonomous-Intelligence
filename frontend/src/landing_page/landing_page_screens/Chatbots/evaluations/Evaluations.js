import React, { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const TranslateSentences = () => {
  const [translatedText, setTranslatedText] = useState([]);
  const [bleuScore, setBleuScore] = useState(null);
  const [count, setCount] = useState(5);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleTranslationRequest = async () => {
    try {
      const response = await axios.post(
        "http://localhost:8000/spanish-gpt-evaluation",
        { count },
        { headers: { "Content-Type": "application/json" } }
      );

      const { translations, bleu_score } = response.data;
      setTranslatedText(translations);
      setBleuScore(bleu_score);
      setError(null);
    } catch (err) {
      console.error("Translation error:", err);
      setError("An error occurred while translating.");
    }
  };

  const handleSubmitToLeaderboard = () => {
    navigate("/submit-to-leaderboard");
  };

  const datasets = [
    {
      name: "Spanish – BLEU",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "GPT-4o Zero-Shot", score: 0.523, updated: "Aug 2025" },
        { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.521, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash Zero-Shot", score: 0.511, updated: "Aug 2025" },
        //{ rank: 4, model: "GPT-4.1 Fine-Tuned", score: 0.35, updated: "Aug 2025" },
      ],
    },
    {
      name: "Spanish – BERTScore",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "GPT-4o Zero-Shot", score: 0.886, updated: "Aug 2025" },
        { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.886, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash Zero-Shot", score: 0.883, updated: "Aug 2025" },
        //{ rank: 4, model: "GPT-4.1 Fine-Tuned", score: 0.852, updated: "Aug 2025" },
      ],
    },
    {
      name: "Japanese – BLEU",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "GPT-4o Zero-Shot", score: 0.66, updated: "Aug 2025" },
        { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.652, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.639, updated: "Aug 2025" },
        //{ rank: 4, model: "GPT-4.1 Fine-Tuned", score: 0.574, updated: "Aug 2025" },
      ],
    },
    {
      name: "Japanese – BERTScore",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "GPT-4o Zero-Shot", score: 0.883, updated: "Aug 2025" },
        { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.878, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.874, updated: "Aug 2025" },
        //{ rank: 4, model: "GPT-4.1 Fine-Tuned", score: 0.869, updated: "Aug 2025" },
      ],
    },
    {
      name: "Arabic – BLEU",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.53, updated: "Aug 2025" },
        { rank: 2, model: "GPT-4o Zero-Shot", score: 0.524, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.518, updated: "Aug 2025" },
        //{ rank: 4, model: "GPT-4.1 Fine-Tuned", score: 0.141, updated: "Aug 2025" },
      ],
    },
    {
      name: "Arabic – BERTScore",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "GPT-4o Zero-Shot", score: 0.887, updated: "Aug 2025" },
        { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.887, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.884, updated: "Aug 2025" },
        //{ rank: 4, model: "GPT-4.1 Fine-Tuned", score: 0.722, updated: "Aug 2025" },
      ],
    },
    {
      name: "Chinese – BLEU",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "GPT-4o Zero-Shot", score: 0.616, updated: "Aug 2025" },
        { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.615, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.257, updated: "Aug 2025" },
        //{ rank: 3, model: "GPT-4.1 Fine-Tuned", score: 0.472, updated: "Aug 2025" },
        //{ rank: 4, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.257, updated: "Aug 2025" },
      ],
    },
    {
      name: "Chinese – BERTScore",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "GPT-4o Zero-Shot", score: 0.898, updated: "Aug 2025" },
        { rank: 2, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.897, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.892, updated: "Aug 2025" },
        //{ rank: 4, model: "GPT-4.1 Fine-Tuned", score: 0.872, updated: "Aug 2025" },
      ],
    },
    {
      name: "Korean – BLEU",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.581, updated: "Aug 2025" },
        { rank: 2, model: "GPT-4o Zero-Shot", score: 0.577, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.559, updated: "Aug 2025" },
        //{ rank: 4, model: "GPT-4.1 Fine-Tuned", score: 0.518, updated: "Aug 2025" },
      ],
    },
    {
      name: "Korean – BERTScore",
      url: "https://huggingface.co/datasets/openlanguagedata/flores_plus",
      models: [
        { rank: 1, model: "Claude 3.5 Sonnet Zero-Shot", score: 0.874, updated: "Aug 2025" },
        { rank: 2, model: "GPT-4o Zero-Shot", score: 0.872, updated: "Aug 2025" },
        { rank: 3, model: "Gemini 2.5 Flash-Lite Zero-Shot", score: 0.868, updated: "Aug 2025" },
        //{ rank: 4, model: "GPT-4.1 Fine-Tuned", score: 0.86, updated: "Aug 2025" },
      ],
    },
  ];

  return (
    <section className="bg-black min-h-screen py-10 px-4 text-gray-100">
      <div className="text-center mb-10">
        <h1 className="text-4xl sm:text-5xl font-extrabold bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent mb-4">
          Evaluation Leaderboard
        </h1>

        <button
          className="btn-black px-6 py-2 border border-yellow rounded hover:bg-white hover:text-white transition mb-6"
          onClick={handleSubmitToLeaderboard}
        >
        Submit Model to Leaderboard
        </button>
      </div>

      <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12">
        {datasets.map((dataset, i) => (
          <div key={i} className="bg-gray-950 p-6 rounded-xl shadow-md border border-gray-800">
            <h2 className="text-xl font-semibold text-[#EDDC8F] mb-2">{dataset.name}</h2>
            <a
              href={dataset.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-400 hover:underline mb-4 inline-block"
            >
              View Dataset
            </a>
            <div className="mt-2 space-y-2">
              {dataset.models.map((m) => (
                <div
                  key={m.rank}
                  className="flex items-center justify-between bg-gray-900 p-3 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-white">
                      {m.rank}. {m.model}
                    </p>
                    <p className="text-sm text-gray-400">
                      Updated: {m.updated}
                    </p>
                  </div>
                  <div className="text-lg font-bold text-[#F1CA57]">{m.score}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="max-w-4xl mx-auto mt-16 flex flex-col items-center">
        <button
          onClick={handleTranslationRequest}
          className="btn-black px-6 py-2 border border-white rounded hover:bg-white hover:text-black transition mb-6"
        >
          Generate GPT Spanish Score
        </button>

        {translatedText.length > 0 && (
          <div className="bg-gray-950 p-6 rounded-lg w-full shadow-lg">
            <h3 className="text-xl font-bold mb-4 text-white">GPT Translations</h3>
            <ul className="list-decimal pl-5 space-y-1 text-gray-300">
              {translatedText.map((sentence, idx) => (
                <li key={idx}>{sentence}</li>
              ))}
            </ul>
          </div>
        )}

        {bleuScore !== null && (
          <div className="bg-gray-950 mt-6 p-6 rounded-lg w-full shadow-lg">
            <h3 className="text-xl font-bold text-white mb-2">BLEU Score</h3>
            <p className="text-gray-300 text-lg">{bleuScore.toFixed(4)}</p>
          </div>
        )}

        {error && (
          <div className="mt-6 text-red-500 bg-red-900 p-4 rounded-md w-full text-center">
            {error}
          </div>
        )}
      </div>
    </section>
  );
};

export default TranslateSentences;
