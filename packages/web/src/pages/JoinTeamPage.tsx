import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../App';
import OurogenLogo from '../components/OurogenLogo';
import { coworkerApi, errorMessage } from '../coworker/api';

/** Accept a team invite: /app/join/:token */
export default function JoinTeamPage() {
  const { token: invite = '' } = useParams<{ token: string }>();
  const { token } = useAuth();
  const nav = useNavigate();
  const [state, setState] = useState<{ ok?: string; error?: string }>({});

  useEffect(() => {
    const api = coworkerApi(token);
    api.post(`/org/join/${invite}`)
      .then((d) => setState({ ok: d.org?.name || 'your team' }))
      .catch((e) => setState({ error: errorMessage(e) }));
  }, [invite, token]);

  return (
    <div className="min-h-dvh flex items-center justify-center bg-white dark:bg-[#212121] text-gray-900 dark:text-white px-4">
      <div className="max-w-md w-full text-center space-y-4">
        <OurogenLogo className="w-10 h-10 mx-auto" />
        {!state.ok && !state.error && <p className="text-gray-500">Joining…</p>}
        {state.ok && (
          <>
            <h1 className="text-2xl font-semibold">You joined {state.ok}</h1>
            <p className="text-gray-600 dark:text-gray-300">Your coworker now follows your team's rules. Set it up if you haven't yet.</p>
            <button className="rounded-xl bg-black dark:bg-white text-white dark:text-black px-5 py-2.5 font-semibold" onClick={() => nav('/app/coworker/team')}>
              Open your coworker
            </button>
          </>
        )}
        {state.error && (
          <>
            <h1 className="text-2xl font-semibold">Couldn't join</h1>
            <p className="text-gray-600 dark:text-gray-300">{state.error}</p>
            <Link className="underline" to="/app">Back to the app</Link>
          </>
        )}
      </div>
    </div>
  );
}
