export type EmailType = "action" | "informational" | "irrelevant";
export type Filter = "action" | "in_progress" | "archive" | "done";
export type AnalysisStatus = "analyzed" | "not_analyzed";
export type Priority = "high" | "medium" | "low";

export type Item = {
  thread_id: string;
  subject: string;
  latest_date: string;
  sender: string;
  email_type: EmailType;
  topic: string | null;
  actions: string[];
  urgency_signals: string[];
  importance_signals: string[];
  priority: Priority | null;
  summary: string;
  confidence: number | null;
  analysis_status: AnalysisStatus;
  message_count: number;
  importance_flag?: string | null;
  done: boolean;
  in_progress: boolean;
  pinned: boolean;
};

export type WorkloadCounts = {
  action: number;
  archive: number;
  informational: number;
  irrelevant: number;
  done: number;
  in_progress: number;
  pending: number;
};

export type WorkItemPage = {
  items: Item[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  counts: WorkloadCounts;
};

export type Email = {
  body: string;
  subject: string;
  sent_from: string;
  sent_to: string[];
  sent_cc?: string[] | null;
  date_sent: string;
  attachments?: { filename: string; filesize: number; filetype: string }[] | null;
  importance_flag?: string | null;
  message_id: string;
  thread_id: string;
};

export type Thread = { messages: Email[] };
export type ThreadResponse = { thread: Thread; decision: unknown; work_item: Item };
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  threadIds?: string[];
  threadTitles?: Record<string, string>;
  suggestedQuestions?: string[];
};

export type ChatSession = {
  id: string;
  title: string;
  createdAt: string;
  lastInteractedAt: string;
  threadId?: string;
  threadSubject?: string;
  messages: ChatMessage[];
};

export type Ask = {
  answer: string;
  thread_ids: string[];
  thread_titles: Record<string, string>;
  caveats: string[];
  suggested_questions: string[];
};
