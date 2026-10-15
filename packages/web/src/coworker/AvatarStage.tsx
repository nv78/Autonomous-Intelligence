import { useEffect, useState } from 'react';
import { useAuth } from '../App';
import { coworkerApi } from './api';

/** Fetch an authenticated twin asset as an object URL. */
export function useAssetUrl(assetId: number | null | undefined): string | null {
  const { token } = useAuth();
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!assetId) {
      setUrl(null);
      return;
    }
    let revoked = false;
    let objectUrl = '';
    const api = coworkerApi(token);
    fetch(`${api.base}/twin/assets/${assetId}/file`, { headers: api.headers })
      .then((r) => (r.ok ? r.blob() : null))
      .then((blob) => {
        if (blob && !revoked) {
          objectUrl = URL.createObjectURL(blob);
          setUrl(objectUrl);
        }
      })
      .catch(() => {});
    return () => {
      revoked = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [assetId, token]);
  return url;
}

/**
 * The coworker's face on a call. Uses the user's consented photo or video
 * when present. The "AI" badge is part of the frame and cannot be hidden.
 */
export default function AvatarStage({
  name, ownerName, photoUrl, videoUrl, speaking, listening, size = 'lg',
}: {
  name: string;
  ownerName?: string;
  photoUrl?: string | null;
  videoUrl?: string | null;
  speaking: boolean;
  listening?: boolean;
  size?: 'sm' | 'lg';
}) {
  const person = name.replace(/'s AI coworker.*$/i, '').trim() || name;
  const initials = (ownerName || person).split(' ').map((p) => p[0]).join('').slice(0, 2).toUpperCase();
  const dim = size === 'lg' ? 'w-40 h-40 sm:w-48 sm:h-48' : 'w-20 h-20';
  return (
    <div className="flex flex-col items-center gap-3 select-none">
      <div className="relative">
        <div
          className={`absolute -inset-2 rounded-full transition-all duration-300 ${
            speaking ? 'bg-emerald-400/30 animate-pulse scale-105' : listening ? 'bg-blue-400/20' : 'bg-transparent'
          }`}
        />
        <div className={`relative ${dim} rounded-full overflow-hidden bg-gradient-to-br from-gray-200 to-gray-300 dark:from-[#3a3a3a] dark:to-[#2a2a2a] flex items-center justify-center ring-2 ring-white dark:ring-[#212121]`}>
          {videoUrl ? (
            <video src={videoUrl} muted loop autoPlay={speaking} playsInline className={`w-full h-full object-cover transition-transform duration-150 ${speaking ? 'scale-[1.02]' : ''}`} />
          ) : photoUrl ? (
            <img src={photoUrl} alt="" className={`w-full h-full object-cover transition-transform duration-150 ${speaking ? 'scale-[1.03]' : ''}`} />
          ) : (
            <span className="text-3xl font-semibold text-gray-600 dark:text-gray-300">{initials || 'AI'}</span>
          )}
        </div>
        <span className="absolute bottom-1 right-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-black text-white dark:bg-white dark:text-black shadow">
          AI
        </span>
      </div>
      <div className="text-center">
        <p className="text-sm font-medium">{name}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {speaking ? 'Speaking…' : listening ? 'Listening…' : 'AI coworker · discloses itself on every call'}
        </p>
      </div>
    </div>
  );
}
