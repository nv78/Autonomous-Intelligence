import { useState } from "react";
import axios from "axios";
import { API_BASE_URL } from "../constants/constants";

/** "Continue with Microsoft": work or school (Entra ID) and personal Microsoft accounts. */
export default function MicrosoftSignInButton({ disabled, onError }: { disabled?: boolean; onError: (msg: string) => void }) {
  const [loading, setLoading] = useState(false);

  const start = async () => {
    setLoading(true);
    onError("");
    try {
      const res = await axios.get(`${API_BASE_URL}/auth/microsoft/url`);
      window.location.href = res.data.url;
    } catch (err: any) {
      onError(err.response?.data?.error || "Microsoft sign-in failed");
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={start}
      disabled={disabled || loading}
      className="flex items-center justify-center gap-3 w-full py-3 -mt-3 mb-6 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2F2F2F] text-gray-900 dark:text-white font-medium hover:bg-gray-50 dark:hover:bg-[#3A3A3A] disabled:opacity-50 transition-colors"
    >
      <svg width="18" height="18" viewBox="0 0 21 21" aria-hidden="true">
        <rect x="1" y="1" width="9" height="9" fill="#F25022" />
        <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
        <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
        <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
      </svg>
      {loading ? "Redirecting..." : "Continue with Microsoft"}
    </button>
  );
}
