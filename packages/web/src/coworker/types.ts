export type Autonomy = 'suggest' | 'approve' | 'notify' | 'silent';

export interface Coworker {
  id: number;
  displayName: string;
  ownerName: string;
  ownerEmail: string;
  persona: string;
  status: 'active' | 'paused';
  mode: 'demo' | 'live';
  plan: string;
  autonomy: Record<string, Autonomy>;
  settings: Record<string, any>;
  onboarding: { step?: string; completed?: boolean; [k: string]: any };
  styleProfile: StyleProfile;
  playbook: Record<string, any>;
  createdAt: string;
}

export interface StyleProfile {
  sample_size?: number;
  greeting?: string;
  signoff?: string;
  median_words?: number;
  summary?: string;
  rules?: string[];
  common_phrases?: string[];
}

export interface Connection {
  provider: string;
  account: string;
  status: string;
  error: string;
  lastSyncedAt: string | null;
  scopes: string;
}

export interface Capabilities {
  llm: boolean;
  google: boolean;
  slack_oauth: boolean;
  hubspot_oauth?: boolean;
  voice?: boolean;
  avatar?: boolean;
  meeting_bot?: boolean;
}

export interface Risk {
  code: string;
  message: string;
}

export interface Action {
  id: number;
  type: string;
  label: string;
  status: 'proposed' | 'approved' | 'executing' | 'executed' | 'rejected' | 'cancelled' | 'failed' | 'expired' | 'undone';
  title: string;
  payload: Record<string, any>;
  reasoning: string;
  autonomy: Autonomy;
  approvalReason: string;
  risks: Risk[];
  sourceItemId: number | null;
  responsibilityId: number | null;
  chatId: number | null;
  edited: boolean;
  feedback: string;
  result: Record<string, any>;
  error: string;
  executeAfter: string | null;
  expiresAt: string | null;
  createdAt: string;
  decidedAt: string | null;
  executedAt: string | null;
}

export interface Responsibility {
  id: number;
  name: string;
  template: string;
  instruction: string;
  trigger: Record<string, any>;
  autonomy: Autonomy;
  escalation: string;
  enabled: boolean;
  runs: number;
  lastRunAt: string | null;
  createdAt: string;
}

export interface Suggestion {
  template: string;
  name: string;
  why: string;
  count: number;
  description: string;
}

export interface ActivityRow {
  id: number;
  kind: string;
  summary: string;
  detail: Record<string, any> | null;
  action_id: number | null;
  created_at: string;
}

export interface Person {
  id: number;
  name: string;
  email: string;
  company: string;
  role: string;
  relationship: string;
  interactions: number;
  last_contact_at: string | null;
}

export interface Citation {
  type: string;
  id: number;
  title: string;
  from?: string;
  date?: string | null;
  snippet?: string;
  detail?: string;
  thread_id?: string;
  category?: string;
}

export interface Learned {
  company: string;
  role_guess: string;
  focus_areas: string[];
  counts: Record<string, number>;
  relationships: Record<string, number>;
  key_people: Person[];
  deals: { company: string; relationship: string; waiting_on: string; days_since_last: number | null; last: string }[];
  decisions: Citation[];
  needs_reply: Citation[];
  style: StyleProfile;
}

export interface CoworkerStatus {
  exists: boolean;
  status?: 'active' | 'paused';
  mode?: 'demo' | 'live';
  pending?: number;
  attention?: number;
  onboarding?: Record<string, any>;
}
