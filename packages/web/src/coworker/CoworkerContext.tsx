import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useAuth } from '../App';
import { coworkerApi } from './api';
import type { Action, Capabilities, Connection, Coworker, CoworkerStatus } from './types';

interface CoworkerState {
  coworker: Coworker | null;
  connections: Connection[];
  capabilities: Capabilities | null;
  scenarios: { id: string; label: string }[];
  status: CoworkerStatus;
  loaded: boolean;
  refresh: () => Promise<void>;
  refreshStatus: () => Promise<void>;
  tick: (force?: boolean) => Promise<any>;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  actionCache: Record<number, Action>;
  putActions: (actions: Action[]) => void;
  loadActions: (ids: number[]) => Promise<void>;
  version: number;
}

const Ctx = createContext<CoworkerState | null>(null);

export function useCoworker(): CoworkerState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useCoworker must be used inside CoworkerProvider');
  return ctx;
}

const TICK_MS = 20000;

export function CoworkerProvider({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const [coworker, setCoworker] = useState<Coworker | null>(null);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [scenarios, setScenarios] = useState<{ id: string; label: string }[]>([]);
  const [status, setStatus] = useState<CoworkerStatus>({ exists: false });
  const [loaded, setLoaded] = useState(false);
  const [actionCache, setActionCache] = useState<Record<number, Action>>({});
  const [version, setVersion] = useState(0);
  const pendingIds = useRef<Set<number>>(new Set());

  const api = coworkerApi(token);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.get('');
      setCoworker(data.coworker);
      setConnections(data.connections || []);
      setCapabilities(data.capabilities);
      setScenarios(data.scenarios || []);
    } catch {
      setCoworker(null);
    } finally {
      setLoaded(true);
    }
  }, [token]);

  const refreshStatus = useCallback(async () => {
    if (!token) return;
    try {
      setStatus(await api.get('/status'));
    } catch {}
  }, [token]);

  const putActions = useCallback((actions: Action[]) => {
    setActionCache((prev) => {
      const next = { ...prev };
      for (const a of actions) next[a.id] = a;
      return next;
    });
  }, []);

  const loadActions = useCallback(
    async (ids: number[]) => {
      const missing = ids.filter((id) => !pendingIds.current.has(id));
      if (!missing.length) return;
      missing.forEach((id) => pendingIds.current.add(id));
      try {
        const data = await api.get('/actions', { ids: missing.join(',') });
        putActions(data.actions || []);
      } finally {
        missing.forEach((id) => pendingIds.current.delete(id));
      }
    },
    [token, putActions],
  );

  const tick = useCallback(
    async (force = false) => {
      if (!token) return null;
      try {
        const result = await api.post('/tick', { force });
        if (!result.skipped && (result.results?.length || result.executed || result.failed || result.expired)) {
          setVersion((v) => v + 1);
        }
        await refreshStatus();
        return result;
      } catch {
        return null;
      }
    },
    [token, refreshStatus],
  );

  const pause = useCallback(async () => {
    await api.post('/pause', { reason: 'Kill switch in header' });
    await refresh();
    await refreshStatus();
    setVersion((v) => v + 1);
  }, [token, refresh, refreshStatus]);

  const resume = useCallback(async () => {
    await api.post('/resume');
    await refresh();
    await refreshStatus();
    setVersion((v) => v + 1);
  }, [token, refresh, refreshStatus]);

  useEffect(() => {
    refresh();
    refreshStatus();
  }, [refresh, refreshStatus]);

  useEffect(() => {
    if (!coworker) return;
    tick();
    const handle = setInterval(() => {
      if (document.visibilityState === 'visible') tick();
    }, TICK_MS);
    return () => clearInterval(handle);
  }, [coworker?.id, tick]);

  return (
    <Ctx.Provider
      value={{
        coworker, connections, capabilities, scenarios, status, loaded, refresh, refreshStatus, tick,
        pause, resume, actionCache, putActions, loadActions, version,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}
