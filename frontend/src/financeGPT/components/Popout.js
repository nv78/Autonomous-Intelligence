import { useEffect } from "react";

export default function Popout({ onClose }) {
  // ESC to close
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div className="absolute">
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
        onClick={onClose} // close when clicking outside
      >
        <div
          className="bg-white rounded-xl shadow-xl p-6 w-96"
          onClick={(e) => e.stopPropagation()} // prevent close on inner click
        >
          <h2 className="text-lg font-semibold mb-2">Popout</h2>
          <p>This is a modal-style popout component.</p>
          <button
            onClick={onClose}
            className="mt-4 text-sm text-blue-600 hover:underline"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
