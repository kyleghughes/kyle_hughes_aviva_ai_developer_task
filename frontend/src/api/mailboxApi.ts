import type {
  Ask,
  ChatMessage,
  Filter,
  Item,
  Priority,
  ThreadResponse,
  WorkItemPage,
} from "../types/mailbox";

/**
 * API client for the mailbox workload application.
 *
 * This file is the boundary between the React frontend and the FastAPI
 * backend. Components and hooks should call these functions instead of
 * constructing fetch requests themselves.
 *
 */

export const API = "http://localhost:8000/api";

/**
 * Reads an error message returned by the backend.
 *
 * FastAPI normally returns validation/application errors using a `detail`
 * property. We convert that backend response into a simple string so the
 * calling function can throw a normal JavaScript Error.
 *
 * If the backend response is not JSON, or does not contain a useful
 * `detail` value, the supplied fallback message is used.
 *
 * @param response The HTTP response returned by fetch.
 * @param fallback A safe message to show when the backend gives us no
 *                 usable error message.
 * @returns The backend error message or the supplied fallback.
 */
const parseError = async (
  response: Response,
  fallback: string,
): Promise<string> => {
  try {
    const data = await response.json();

    return data.detail || fallback;
  } catch {
    return fallback;
  }
};

/**
 * Loads the work items displayed in the main mailbox table.
 *
 * The backend is responsible for applying search, filtering and pagination.
 * This is important because the UI should display the same workload that
 * the backend considers to be the current workload.
 *
 * For example, a request might become:
 *
 *   /api/work-items?q=invoice&filter=action&page=2&page_size=10
 *
 * @param options Optional search and pagination settings.
 * @param options.query Free-text search entered by the user.
 * @param options.filter Workload category selected by the user.
 * @param options.page One-based page number.
 * @param options.pageSize Number of items requested on each page.
 *
 * @returns A `WorkItemPage` containing:
 * - the work items for the requested page
 * - workload counts
 * - total number of matching items
 * - total number of pages
 * - the current page
 *
 * @throws Error if the backend cannot return the workload.
 */
export const getWorkItems = async (
  options: {
    query?: string;
    filter?: Filter;
    page?: number;
    pageSize?: number;
  } = {},
): Promise<WorkItemPage> => {
  /*
   * URLSearchParams handles encoding search text and constructing the query
   * string safely.
   *
   * Defaults are provided here so callers can simply call getWorkItems()
   * when they want the first page of the complete workload.
   */
  const params = new URLSearchParams({
    q: options.query ?? "",
    filter: options.filter ?? "action",
    page: String(options.page ?? 1),
    page_size: String(options.pageSize ?? 10),
  });

  const response = await fetch(`${API}/work-items?${params.toString()}`);

  if (!response.ok) {
    const errorMessage = await parseError(response, "Unable to load mailbox.");

    throw new Error(errorMessage);
  }

  return response.json();
};

/**
 * Ingests the mailbox into the backend.
 *
 * Ingestion is the process of reading the source mailbox and updating the
 * application's local/indexed representation of the emails.
 *
 * Importantly, ingestion and AI analysis are separate concerns:
 *
 * 1. Ingestion discovers and classifies the email workload.
 * 2. AI decision support can then be requested for an individual work item.
 *
 * This prevents the application from unnecessarily running the LLM against
 * every email during every ingestion cycle.
 *
 * @returns The number of threads and messages processed.
 * @throws Error if the ingestion request fails.
 */
export const ingestMailbox = async (): Promise<{
  threads_processed: number;
  messages_processed: number;
}> => {
  const response = await fetch(`${API}/ingest`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorMessage = await parseError(response, "Ingestion failed.");

    throw new Error(errorMessage);
  }

  return response.json();
};

/**
 * Loads all messages belonging to a particular email thread.
 *
 * A work item represents the workload associated with a thread, while this
 * endpoint retrieves the underlying conversation that the user needs to
 * inspect in the detail drawer.
 *
 * @param threadId Unique identifier of the email thread.
 * @returns The requested thread and its messages.
 * @throws Error if the thread cannot be loaded.
 */
export const getThread = async (threadId: string): Promise<ThreadResponse> => {
  const response = await fetch(`${API}/threads/${threadId}`);

  if (!response.ok) {
    const errorMessage = await parseError(response, "Unable to load thread.");

    throw new Error(errorMessage);
  }

  return response.json();
};

/**
 * Requests AI decision support for a single work item.
 *
 * This is deliberately an explicit action rather than something that happens
 * automatically for every email. The application uses deterministic
 * business logic for workload classification and only calls the LLM when
 * the user needs additional decision-support evidence.
 *
 * The backend/LLM analysis can provide information such as:
 * - a summary of the conversation
 * - required actions
 * - evidence of urgency
 * - evidence of importance
 * - AI-assessed priority (high, medium or low)
 * - confidence and rationale
 *
 * The deterministic application rules still determine the workflow type; the
 * LLM provides an additional priority assessment from the thread evidence.
 *
 * @param threadId Unique identifier of the thread to analyse.
 * @returns The updated work item containing its AI analysis.
 * @throws Error if AI analysis cannot be completed.
 */
export const analyzeWorkItem = async (
  threadId: string,
): Promise<{ work_item: Item }> => {
  const response = await fetch(`${API}/work-items/${threadId}/analyze`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorMessage = await parseError(response, "Analysis failed.");

    throw new Error(errorMessage);
  }

  return response.json();
};

/**
 * Asks the mailbox assistant a natural-language question.
 *
 * This powers the chat experience in the application. The user can ask
 * questions about the overall workload or, when a thread is selected, ask
 * questions specifically about that conversation.
 *
 * `history` allows the backend to understand follow-up questions in the
 * context of previous messages.
 *
 * The UI's ChatMessage contains additional frontend-only information such as
 * message IDs. Only `role` and `content` are sent to the backend because
 * those are the fields required to understand the conversation.
 *
 * @param question The user's natural-language question.
 * @param options Optional conversation context.
 * @param options.threadId Thread currently being discussed, if any.
 * @param options.history Previous messages in the conversation.
 *
 * @returns The assistant's answer plus related thread IDs, caveats and
 *          suggested follow-up questions.
 * @throws Error if the question cannot be processed.
 */
export const askMailbox = async (
  question: string,
  options?: {
    threadId?: string;
    history?: Pick<ChatMessage, "role" | "content">[];
  },
): Promise<Ask> => {
  /*
   * Strip the frontend-specific properties from chat messages before sending
   * them to the API. This keeps the API contract deliberately small.
   */
  const history = (options?.history ?? []).map(({ role, content }) => ({
    role,
    content,
  }));

  /*
   * Keeping the request body in a named variable makes the payload easier to
   * inspect and debug than constructing it directly inside fetch().
   */
  const requestBody = {
    question,
    thread_id: options?.threadId,
    history,
  };

  const response = await fetch(`${API}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorMessage = await parseError(response, "Question failed.");

    throw new Error(errorMessage);
  }

  return response.json();
};

/**
 * Marks a work item as completed.
 *
 * This changes the deterministic workload state of the item. It does not
 * invoke the LLM because completing a task is a user-driven state change,
 * not an AI decision.
 *
 * @param threadId Unique identifier of the thread/work item.
 * @returns The updated work item.
 * @throws Error if the backend cannot update the item.
 */
export const markWorkItemInProgress = async (threadId: string): Promise<Item> => {
  const response = await fetch(`${API}/work-items/${threadId}/in-progress`, { method: "POST" });
  if (!response.ok) {
    const errorMessage = await parseError(response, "Unable to mark work item in progress.");
    throw new Error(errorMessage);
  }
  return response.json();
};

export const markWorkItemDone = async (threadId: string): Promise<Item> => {
  const response = await fetch(`${API}/work-items/${threadId}/done`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorMessage = await parseError(
      response,
      "Unable to mark work item as done.",
    );

    throw new Error(errorMessage);
  }

  return response.json();
};

/**
 * Reopens a previously completed work item.
 *
 * Like marking an item as done, this is a deterministic state change and
 * does not involve the LLM.
 *
 * @param threadId Unique identifier of the thread/work item.
 * @returns The updated work item.
 * @throws Error if the backend cannot reopen the item.
 */
export const markWorkItemIncomplete = async (
  threadId: string,
): Promise<Item> => {
  const response = await fetch(`${API}/work-items/${threadId}/incomplete`, {
    method: "POST",
  });

  if (!response.ok) {
    const errorMessage = await parseError(
      response,
      "Unable to reopen work item.",
    );

    throw new Error(errorMessage);
  }

  return response.json();
};

export const pinWorkItem = async (threadId: string): Promise<Item> => {
  const response = await fetch(`${API}/work-items/${threadId}/pin`, { method: "POST" });
  if (!response.ok) {
    throw new Error(await parseError(response, "Unable to pin thread."));
  }
  return response.json();
};

export const unpinWorkItem = async (threadId: string): Promise<Item> => {
  const response = await fetch(`${API}/work-items/${threadId}/unpin`, { method: "POST" });
  if (!response.ok) {
    throw new Error(await parseError(response, "Unable to unpin thread."));
  }
  return response.json();
};

export const setWorkItemType = async (
  threadId: string,
  emailType: "action" | "informational" | "irrelevant",
): Promise<Item> => {
  const response = await fetch(`${API}/work-items/${threadId}/type`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email_type: emailType }),
  });
  if (!response.ok) throw new Error(await parseError(response, "Unable to change thread category."));
  return response.json();
};

export const setWorkItemPriority = async (
  threadId: string,
  priority: Priority,
): Promise<Item> => {
  const response = await fetch(`${API}/work-items/${threadId}/priority`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ priority }),
  });
  if (!response.ok) throw new Error(await parseError(response, "Unable to change priority."));
  return response.json();
};
