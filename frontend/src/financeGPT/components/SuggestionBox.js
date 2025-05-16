import React from 'react'

export default function SuggestionBox({ handleTryMessage, selectedChatId, isPrivate }) {
  return (
    <div>
      {" "}
      <div className="bg-[#1A1A1A] p-2 rounded-lg bottom-24 mb-2 overflow-hidden">
        <div
          className="flex gap-2 whitespace-nowrap overflow-x-scroll"
          style={{ msOverflowStyle: "none", scrollbarWidth: "thin" }}
        >
          {[
            "Key financial metrics",
            "Budget planning",
            "Stocks vs bonds",
            "Calculate net worth",
            "Compound interest",
            "Tax reduction",
            "Debt-to-income ratio",
            "Start investing",
            "Credit score",
            "Emergency fund",
          ].map((label, i) => (
            <button
              key={i}
              className="bg-[#3A3B41] text-white text-xs rounded-xl p-2 cursor-pointer hover:bg-[#4A4B51] flex-shrink-0"
              onClick={() =>
                handleTryMessage(
                  [
                    "What are the key financial metrics I should track?",
                    "How do I create a budget plan?",
                    "What is the difference between stocks and bonds?",
                    "How do I calculate my net worth?",
                    "What is compound interest?",
                    "How to reduce my tax liability?",
                    "What is a good debt-to-income ratio?",
                    "How to start investing with little money?",
                    "What is a good credit score?",
                    "How to create an emergency fund?",
                  ][i],
                  selectedChatId,
                  isPrivate
                )
              }
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
