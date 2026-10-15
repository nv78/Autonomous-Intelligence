import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../App";

export default function OAuthCallbackPage() {
  const { setToken } = useAuth();
  const nav = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const token = searchParams.get("token");
    if (token) {
      setToken(token);
      // New accounts go straight into coworker onboarding.
      nav(searchParams.get("isNewUser") === "1" ? "/app/onboarding" : "/app", { replace: true });
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
