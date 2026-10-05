import type { ChatSession, Item } from "./mailbox";

export const STORAGE_KEY = "claims-inbox-chat-sessions";
export const ACTIVE_SESSION_KEY = "claims-inbox-active-chat-session";

export const SUGGESTED_PROMPTS = [
  "What needs my attention today?",
  "Which emails require a response?",
  "Summarise the main actions in my mailbox.",
  "Are there any messages that look urgent?",
];

export const makeId = () =>
  `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
export const now = () => new Date().toISOString();

export const loadSessions = (): ChatSession[] => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const parsed = stored ? JSON.parse(stored) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

export const formatSessionDate = (value: string) =>
  new Intl.DateTimeFormat(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));

export const createSession = (thread: Item | null): ChatSession => ({
  id: makeId(),
  title: thread ? thread.subject : "New chat",
  createdAt: now(),
  lastInteractedAt: now(),
  threadId: thread?.thread_id,
  threadSubject: thread?.subject,
  messages: [],
});
