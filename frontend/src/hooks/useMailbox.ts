import { useCallback, useEffect, useMemo, useState } from "react";

import {
  analyzeWorkItem,
  askMailbox,
  getThread,
  getWorkItems,
  ingestMailbox,
  markWorkItemDone,
  markWorkItemIncomplete,
} from "../api/mailboxApi";

import type {
  Ask,
  Filter,
  Item,
  Thread,
  WorkloadCounts,
} from "../types/mailbox";

//#region Constants
const PAGE_SIZE: number = 10;
//#endregion

/**
 * Coordinates mailbox data, UI state and mailbox actions.
 *
 * The hook keeps API calls and state transitions out of the presentation
 * components. Business workload decisions remain deterministic; AI is used
 * for decision support and natural-language questions.
 *
 * @returns Mailbox data, UI state and actions required by the workload UI.
 */
export const useMailbox = () => {
  //#region State
  const [items, setItems] = useState<Item[]>([]);
  const [counts, setCounts] = useState<WorkloadCounts>({
    action: 0,
    informational: 0,
    irrelevant: 0,
    done: 0,
    pending: 0,
  });
  const [total, setTotal] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [page, setPage] = useState<number>(1);
  const [search, setSearch] = useState<string>("");
  const [filter, setFilter] = useState<Filter>("all");
  const [status, setStatus] = useState<string>("Loading mailbox…");
  const [selected, setSelected] = useState<Item | null>(null);
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null);
  const [threadLoading, setThreadLoading] = useState<boolean>(false);
  const [asking, setAsking] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [answer, setAnswer] = useState<Ask | null>(null);

  //#endregion

  //#region Data Loading

  /**
   * Loads a specific workload view from the backend.
   *
   * The values are passed explicitly so callers can immediately load a new
   * search/filter combination without waiting for React state to update.
   *
   * @param nextPage Page number to load.
   * @param nextSearch Search text to apply.
   * @param nextFilter Workload filter to apply.
   * @returns Resolves when the workload request has completed.
   */
  const load = useCallback(
    async (
      nextPage: number,
      nextSearch: string,
      nextFilter: Filter,
    ): Promise<void> => {
      try {
        const result = await getWorkItems({
          query: nextSearch,
          filter: nextFilter,
          page: nextPage,
          pageSize: PAGE_SIZE,
        });

        setItems(result.items);
        setCounts(result.counts);
        setTotal(result.total);
        setTotalPages(result.total_pages);
        setPage(result.page);
        setStatus("Mailbox indexed — AI decision support is on demand");
      } catch (error: unknown) {
        setStatus(
          error instanceof Error ? error.message : "Unable to load mailbox.",
        );
      }
    },
    [],
  );

  /**
   * Loads the default mailbox view when the hook first mounts.
   */
  useEffect(() => {
    const loadInitialMailbox = async (): Promise<void> => {
      await load(1, "", "all");
    };

    void loadInitialMailbox();
  }, [load]);

  /**
   * Re-ingests the mailbox and reloads the current view.
   *
   * The current page, search and filter are retained after ingestion.
   *
   * @returns Resolves when ingestion and the subsequent reload complete.
   */
  const refresh = useCallback(async (): Promise<void> => {
    setStatus("Refreshing mailbox…");

    try {
      const result = await ingestMailbox();

      await load(page, search, filter);

      setStatus(
        `Indexed ${result.threads_processed} threads / ${result.messages_processed} messages`,
      );
    } catch (error: unknown) {
      setStatus(error instanceof Error ? error.message : "Ingestion failed.");
    }
  }, [filter, load, page, search]);

  //#endregion

  //#region Search, Filtering and Pagination

  /**
   * Applies a new search/filter combination.
   *
   * Changing the search or filter resets the table to the first page.
   *
   * @param nextSearch New search text.
   * @param nextFilter New workload filter.
   * @returns Nothing; the new view is loaded asynchronously.
   */
  const updateView = useCallback(
    (nextSearch: string, nextFilter: Filter): void => {
      setSearch(nextSearch);
      setFilter(nextFilter);
      setPage(1);

      void load(1, nextSearch, nextFilter);
    },
    [load],
  );

  /**
   * Changes the current workload page.
   *
   * @param nextPage Page number to display.
   * @returns Nothing; the requested page is loaded asynchronously.
   */
  const changePage = useCallback(
    (nextPage: number): void => {
      setPage(nextPage);

      void load(nextPage, search, filter);
    },
    [filter, load, search],
  );

  //#endregion

  //#region Work Item and Thread Actions

  /**
   * Opens a work item and loads its conversation.
   *
   * If the item has not already been analysed, AI decision support is
   * requested after the conversation has been loaded.
   *
   * @param item Work item selected by the user.
   * @returns Resolves when thread loading and any required AI analysis finish.
   */
  const openItem = useCallback(async (item: Item): Promise<void> => {
    setSelected(item);
    setSelectedThread(null);
    setThreadLoading(true);

    try {
      const response = await getThread(item.thread_id);
      setSelectedThread(response.thread);
    } catch (error: unknown) {
      setStatus(
        error instanceof Error ? error.message : "Unable to load thread.",
      );
    } finally {
      setThreadLoading(false);
    }

    // Avoid making the same AI request every time the thread is opened.
    if (item.analysis_status === "analyzed") {
      return;
    }

    setAnalyzing(true);
    setStatus("Analysing selected email with Ollama…");

    try {
      const result = await analyzeWorkItem(item.thread_id);

      setItems((current: Item[]) =>
        current.map((entry: Item) =>
          entry.thread_id === item.thread_id ? result.work_item : entry,
        ),
      );

      setSelected(result.work_item);
      setStatus("AI decision support complete");
    } catch (error: unknown) {
      setStatus(error instanceof Error ? error.message : "AI analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  }, []);

  /**
   * Marks a work item as done or reopens it.
   *
   * This is a deterministic user action and does not involve the LLM.
   *
   * @param item Work item being updated.
   * @param done `true` to mark the item done, `false` to reopen it.
   * @returns Resolves when the work item and current workload have been updated.
   */
  const setDoneState = useCallback(
    async (item: Item, done: boolean): Promise<void> => {
      try {
        const updated: Item = done
          ? await markWorkItemDone(item.thread_id)
          : await markWorkItemIncomplete(item.thread_id);

        setSelected((current: Item | null) =>
          current?.thread_id === item.thread_id ? updated : current,
        );

        await load(page, search, filter);

        setStatus(done ? "Work item marked done" : "Work item reopened");
      } catch (error: unknown) {
        setStatus(
          error instanceof Error
            ? error.message
            : "Unable to update work item.",
        );
      }
    },
    [filter, load, page, search],
  );

  /**
   * Closes the detail drawer and clears the selected conversation.
   *
   * @returns Nothing.
   */
  const closeDrawer = useCallback((): void => {
    setSelected(null);
    setSelectedThread(null);
  }, []);

  //#endregion

  //#region Natural Language Q&A

  /**
   * Sends a natural-language question to the mailbox assistant.
   *
   * @param question Question entered by the user.
   * @returns Resolves when the question has been answered.
   */
  const ask = useCallback(async (question: string): Promise<void> => {
    if (!question.trim()) {
      return;
    }

    setAsking(true);
    setAnswer(null);

    try {
      const result: Ask = await askMailbox(question);
      setAnswer(result);
    } catch (error: unknown) {
      setAnswer({
        answer: error instanceof Error ? error.message : "Question failed.",
        thread_ids: [],
        caveats: [],
        suggested_questions: [],
      });
    } finally {
      setAsking(false);
    }
  }, []);

  //#endregion

  //#region Derived State

  /**
   * Calculates the item range shown by the current page.
   *
   * For example, page 2 with 10 items per page displays items 11–20.
   */
  const visibleRange = useMemo((): { from: number; to: number } => {
    if (!total) {
      return {
        from: 0,
        to: 0,
      };
    }

    return {
      from: (page - 1) * PAGE_SIZE + 1,
      to: Math.min(page * PAGE_SIZE, total),
    };
  }, [page, total]);

  //#endregion

  //#region Public API

  /**
   * Values and actions exposed to the mailbox UI.
   *
   * Keeping this interface in one place makes it clear what the consuming
   * components are allowed to use without exposing the hook's implementation.
   */
  return {
    // Workload
    items,
    counts,
    total,
    totalPages,
    page,
    pageSize: PAGE_SIZE,
    visibleRange,

    // Current view
    search,
    filter,
    status,

    // Selected thread
    selected,
    selectedThread,
    threadLoading,

    // AI / Q&A state
    asking,
    analyzing,
    answer,

    // View controls
    setSearch: (value: string): void => updateView(value, filter),

    setFilter: (value: Filter): void => updateView(search, value),

    changePage,

    // Actions
    refresh,
    openItem,
    setDoneState,
    closeDrawer,
    ask,
  };

  //#endregion
};
