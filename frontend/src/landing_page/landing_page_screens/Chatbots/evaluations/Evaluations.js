import React, { useState } from "react";
import axios from "axios";

const TranslateSentences = () => {
  const [translatedText, setTranslatedText] = useState([]);
  const [bleuScore, setBleuScore] = useState(null);
  const [count, setCount] = useState(5); // number of sentences to translate
  const [error, setError] = useState(null);

  const handleTranslationRequest = async () => {
    try {
      const response = await axios.post(
        "http://localhost:5000/spanish-gpt-evaluation",
        { count: count },
        { headers: { "Content-Type": "application/json" } }
      );

      const { translations, bleu } = response.data;
      setTranslatedText(translations);
      setBleuScore(bleu);
    } catch (error) {
      console.error("Error during translation:", error);
      setError("An error occurred while translating.");
    }
  };

  return (
    <section className="text-gray-100 body-font overflow-hidden min-h-screen bg-black px-4 py-10">
      <div className="flex flex-col text-center w-full mb-10">
        <h1 className="sm:text-5xl text-4xl font-extrabold title-font bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] bg-clip-text text-transparent w-fit mx-auto px-4 py-2">
          Evaluation Leaderboard
        </h1>
      </div>

      <div className="container mx-auto flex flex-col items-center">
        <button
          onClick={handleTranslationRequest}
          className="btn-black px-6 py-2 border border-white rounded hover:bg-white hover:text-black transition"
        >
          Generate GPT Spanish Score
        </button>

        {translatedText.length > 0 && (
          <div className="mt-10 max-w-xl text-left space-y-4">
            <h2 className="text-xl font-semibold">GPT Translations:</h2>
            {translatedText.map((sentence, idx) => (
              <p key={idx} className="text-gray-300">{idx + 1}. {sentence}</p>
            ))}
          </div>
        )}

        {bleuScore !== null && (
          <div className="mt-8">
            <h3 className="text-xl font-semibold">BLEU Score:</h3>
            <p>{bleuScore.toFixed(4)}</p>
          </div>
        )}

        {error && (
          <div className="mt-6 text-red-500">
            <p>{error}</p>
          </div>
        )}
      </div>
    </section>
  );
};

export default TranslateSentences;
