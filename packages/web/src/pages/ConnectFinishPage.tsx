import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../App";
import { coworkerApi, errorMessage } from "../coworker/api";

/**
 * Google, Microsoft, Slack, and the CRMs send the browser back here after consent. The connection is
 * finished with *your* session, and the server checks you're the account that started it, so a consent
 * link from someone else can never attach your mailbox to their account.
 */
export default function ConnectFinishPage() {
  const { token } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [problem, setProblem] = useState("");

  useEffect(() => {
    const provider = params.get("provider") || "";
    const body: Record<string, string> = {};
    for (const key of ["code", "state", "error", "error_description"]) {
      const value = params.get(key);
      if (value) body[key] = value;
    }
    coworkerApi(token)
      .post(`/connections/${encodeURIComponent(provider)}/finish`, body)
      .then((d: any) => nav(d.next || "/app/coworker/settings", { replace: true }))
      .catch((e: unknown) => setProblem(errorMessage(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-white dark:bg-[#212121] px-4">
      {problem ? (
        <div className="max-w-md text-center space-y-3">
          <p className="text-gray-900 dark:text-white">{problem}</p>
          <button className="underline text-sm" onClick={() => nav("/app/coworker/settings", { replace: true })}>Back to Settings</button>
        </div>
      ) : (
        <p className="text-gray-500 dark:text-gray-400">Finishing the connection…</p>
      )}
    </div>
  );
}
