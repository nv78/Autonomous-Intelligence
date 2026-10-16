import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../App";

export default function OAuthCallbackPage() {
  const { setToken } = useAuth();
  const nav = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    // The token arrives in the URL fragment (never sent to servers); older links used the query.
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const token = fragment.get("token") || searchParams.get("token");
    const isNew = (fragment.get("isNewUser") || searchParams.get("isNewUser")) === "1";
    if (token) {
      setToken(token);
      window.history.replaceState(null, "", window.location.pathname);
      // New accounts go straight into coworker onboarding.
      nav(isNew ? "/app/onboarding" : "/app", { replace: true });
    } else {
      nav("/login?error=missing_code", { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-[#212121]">
      <p className="text-gray-500 dark:text-gray-400">Signing you in...</p>
    </div>
  );
}
