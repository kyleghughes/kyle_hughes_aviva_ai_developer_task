import { useEffect, useMemo, useRef, useState } from "react";
import { MessageCircle, Trash2, X } from "lucide-react";
import { askMailbox } from "../api/mailboxApi";
import type { ChatMessage, ChatSession, Item } from "../types/mailbox";
import { ChatComposer } from "./ChatComposer";
import { ChatConversation, EmptyChatState } from "./ChatConversation";
import { ChatDeleteDialog } from "./ChatDeleteDialog";
import { ChatSessionList } from "./ChatSessionList";
import {
  ACTIVE_SESSION_KEY,
  createSession,
  loadSessions,
  makeId,
  now,
  STORAGE_KEY,
  SUGGESTED_PROMPTS,
} from "../types/chatTypes";
import { useTheme } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";
import Divider from "@mui/material/Divider";

//#region props interface
export interface ChatPopperProps {
  open: boolean;
  onClose: () => void;
  thread: Item | null;
  newSessionToken: number;
}
//#endregion

const ChatPopper = ({
  open,
  onClose,
  thread,
  newSessionToken,
}: ChatPopperProps) => {
  //#region State
  const [sessions, setSessions] = useState<ChatSession[]>(loadSessions);
  const [activeId, setActiveId] = useState<string | null>(() =>
    localStorage.getItem(ACTIVE_SESSION_KEY),
  );
  const [question, setQuestion] = useState<string>("");
  const [asking, setAsking] = useState<boolean>(false);
  const [confirmDelete, setConfirmDelete] = useState<"session" | "all" | null>(
    null,
  );

  //#region Refs
  const previousToken = useRef<number>(newSessionToken);
  const chatPanelRef = useRef<HTMLDivElement | null>(null);
  //#endregion

  //#region Theme
  const theme = useTheme();
  const dark: boolean = theme.palette.mode === "dark";
  //#endregion

  //#region Variables
  const activeSession: ChatSession | null =
    sessions.find((session) => session.id === activeId) ?? null;

  const visibleMessages: ChatMessage[] = useMemo(
    () => activeSession?.messages.slice(-30) ?? [],
    [activeSession],
  );

  const latestSuggestions: string[] = useMemo(() => {
    for (let index = visibleMessages.length - 1; index >= 0; index -= 1) {
      const message = visibleMessages[index];

      if (message.role === "assistant" && message.suggestedQuestions?.length) {
        return message.suggestedQuestions;
      }
    }

    return [];
  }, [visibleMessages]);
  //#endregion

  //#region Persistence

  /**
   * Persists all chat sessions whenever the session state changes.
   */
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }, [sessions]);

  /**
   * Persists the currently selected session ID.
   *
   * The stored ID is removed when no session is selected.
   */
  useEffect(() => {
    if (activeId) {
      localStorage.setItem(ACTIVE_SESSION_KEY, activeId);
    } else {
      localStorage.removeItem(ACTIVE_SESSION_KEY);
    }
  }, [activeId]);

  //#endregion

  //#region Session Lifecycle

  /**
   * Creates a new thread-specific session when the parent supplies
   * a new session token.
   *
   * If the chat is opened without a new thread, the first existing
   * session is selected automatically.
   */
  useEffect(() => {
    if (!open) return;

    const tokenChanged = previousToken.current !== newSessionToken;

    previousToken.current = newSessionToken;

    if (thread && tokenChanged) {
      const session = createSession(thread);

      setSessions((current) => [session, ...current]);
      setActiveId(session.id);
      setQuestion("");

      return;
    }

    if (!activeId && sessions.length > 0) {
      setActiveId(sessions[0].id);
    }
  }, [open, thread, newSessionToken, activeId, sessions]);

  /**
   * Creates a new empty chat session.
   *
   * @returns Nothing; the new session becomes active.
   */
  const startNewChat = (): void => {
    const session = createSession(null);

    setSessions((current) => [session, ...current]);
    setActiveId(session.id);
    setQuestion("");
  };

  //#endregion

  //#region Outside Click Handling

  /**
   * Closes the popout when the user clicks outside the chat panel.
   *
   * Delete confirmation dialogs are excluded so clicking outside the
   * panel does not dismiss the confirmation unexpectedly.
   */
  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: PointerEvent): void => {
      if (confirmDelete !== null) return;

      const target = event.target;

      if (!(target instanceof Node)) return;

      if (chatPanelRef.current?.contains(target)) return;

      onClose();
    };

    document.addEventListener("pointerdown", handlePointerDown, true);

    return () =>
      document.removeEventListener("pointerdown", handlePointerDown, true);
  }, [open, confirmDelete, onClose]);

  //#endregion

  //#region Message Submission

  /**
   * Sends a question to the mailbox assistant.
   *
   * The user's message is added to the active session immediately.
   * The assistant response is then appended when the API request
   * completes.
   *
   * If no session is active, one is created automatically.
   *
   * @param value Optional question to submit. Defaults to the composer value.
   * @returns Resolves when the assistant response has been processed.
   */
  const submit = async (value: string = question): Promise<void> => {
    const trimmed: string = value.trim();

    if (!trimmed || asking) return;

    let session: ChatSession | null = activeSession;

    // Create a session automatically if the user starts typing before
    // selecting or creating one.
    if (!session) {
      session = createSession(thread);

      setSessions((current) => [session!, ...current]);
      setActiveId(session.id);
    }

    /**
     * Message being added to the conversation.
     */
    const userMessage: ChatMessage = {
      id: makeId(),
      role: "user",
      content: trimmed,
    };

    /**
     * Conversation history sent to the backend.
     *
     * The newly submitted question is excluded because it is sent
     * separately as the current question.
     */
    const history = [...session.messages, userMessage]
      .slice(-20)
      .map(({ role, content }) => ({ role, content }));

    setSessions((current) =>
      current.map((item) =>
        item.id === session!.id
          ? {
              ...item,
              title: item.messages.length ? item.title : trimmed.slice(0, 60),
              lastInteractedAt: now(),
              messages: [...item.messages, userMessage],
            }
          : item,
      ),
    );

    setQuestion("");
    setAsking(true);

    try {
      /**
       * Ask the backend mailbox assistant to answer the question.
       *
       * The optional thread ID keeps thread-specific conversations
       * scoped to their originating email thread.
       */
      const result = await askMailbox(trimmed, {
        threadId: session.threadId,
        history: history.slice(0, -1),
      });

      /**
       * Assistant response converted into the application's chat format.
       */
      const assistantMessage: ChatMessage = {
        id: makeId(),
        role: "assistant",
        content: result.answer,
        threadIds: result.thread_ids,
        suggestedQuestions: result.suggested_questions,
      };

      setSessions((current) =>
        current.map((item) =>
          item.id === session!.id
            ? {
                ...item,
                lastInteractedAt: now(),
                messages: [...item.messages, assistantMessage],
              }
            : item,
        ),
      );
    } catch (error: unknown) {
      /**
       * Keep API failures inside the conversation so the user can see
       * what went wrong without losing the existing chat history.
       */
      setSessions((current) =>
        current.map((item) =>
          item.id === session!.id
            ? {
                ...item,
                lastInteractedAt: now(),
                messages: [
                  ...item.messages,
                  {
                    id: makeId(),
                    role: "assistant",
                    content:
                      error instanceof Error
                        ? error.message
                        : "Question failed.",
                  },
                ],
              }
            : item,
        ),
      );
    } finally {
      setAsking(false);
    }
  };

  //#endregion

  //#region Session Deletion

  /**
   * Deletes the currently active chat session.
   *
   * The next remaining session becomes active, if one exists.
   */
  const deleteSession = (): void => {
    if (!activeId) return;

    const remaining: ChatSession[] = sessions.filter(
      (session) => session.id !== activeId,
    );

    setSessions(remaining);
    setActiveId(remaining[0]?.id ?? null);
    setConfirmDelete(null);
  };

  /**
   * Deletes every persisted chat session.
   *
   * Both session data and the active-session reference are removed
   * from localStorage.
   */
  const deleteAll = (): void => {
    setSessions([]);
    setActiveId(null);
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(ACTIVE_SESSION_KEY);
    setConfirmDelete(null);
  };

  //#endregion

  // The popout will not open whilst in a closed state
  if (!open) return null;

  return (
    <>
      <Box
        ref={chatPanelRef}
        sx={{
          position: "fixed",
          right: { xs: 12, sm: 24 },
          bottom: { xs: 12, sm: 24 },
          zIndex: theme.zIndex.modal,
          width: { xs: "calc(100vw - 24px)", sm: 720 },
          maxWidth: "calc(100vw - 24px)",
        }}
      >
        <Paper
          elevation={12}
          sx={{
            width: "100%",
            height: {
              xs: "min(680px, calc(100vh - 24px))",
              sm: "min(620px, calc(100vh - 48px))",
            },
            maxHeight: "calc(100vh - 24px)",
            overflow: "hidden",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 2,
            display: "flex",
          }}
        >
          <ChatSessionList
            sessions={sessions}
            activeId={activeId}
            onSelect={setActiveId}
            onNew={startNewChat}
            onDeleteAll={() => setConfirmDelete("all")}
          />

          <Box
            sx={{
              flex: 1,
              minWidth: 0,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Box
              sx={{
                px: 2,
                py: 1.5,
                bgcolor: dark ? "#0C1B25" : "#003B5C",
                color: "white",
              }}
            >
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                gap={1}
              >
                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  minWidth={0}
                >
                  <Box
                    sx={{
                      width: 32,
                      height: 32,
                      borderRadius: 1,
                      bgcolor: "rgba(247,201,72,.16)",
                      color: "#F7C948",
                      display: "grid",
                      placeItems: "center",
                      flexShrink: 0,
                    }}
                  >
                    <MessageCircle size={17} />
                  </Box>

                  <Box minWidth={0}>
                    <Typography fontWeight={800} fontSize={14}>
                      Mailbox assistant
                    </Typography>

                    <Typography noWrap fontSize={10} sx={{ opacity: 0.72 }}>
                      {activeSession?.threadSubject
                        ? `Thread: ${activeSession.threadSubject}`
                        : "Ask questions about your workload"}
                    </Typography>
                  </Box>
                </Stack>

                <Stack direction="row" spacing={0.25}>
                  <Tooltip title="Delete this session">
                    <IconButton
                      onClick={() => setConfirmDelete("session")}
                      disabled={!activeSession}
                      size="small"
                      sx={{ color: "inherit" }}
                      aria-label="Delete this session"
                    >
                      <Trash2 size={16} />
                    </IconButton>
                  </Tooltip>

                  <IconButton
                    onClick={onClose}
                    size="small"
                    sx={{ color: "inherit" }}
                    aria-label="Close chat"
                  >
                    <X size={18} />
                  </IconButton>
                </Stack>
              </Stack>
            </Box>

            <Box sx={{ flex: 1, overflowY: "auto", p: 2 }}>
              {activeSession?.threadSubject && (
                <Paper
                  elevation={0}
                  sx={{
                    p: 1.25,
                    mb: 1.5,
                    bgcolor: "action.hover",
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography
                    fontSize={9}
                    fontWeight={800}
                    color="text.secondary"
                    textTransform="uppercase"
                    letterSpacing=".08em"
                  >
                    New thread analysis session
                  </Typography>

                  <Typography fontSize={11} fontWeight={700} mt={0.35} noWrap>
                    {activeSession.threadSubject}
                  </Typography>
                </Paper>
              )}

              {!visibleMessages.length && <EmptyChatState />}

              <ChatConversation
                messages={visibleMessages}
                asking={asking}
                dark={dark}
              />
            </Box>

            <Divider />

            <ChatComposer
              question={question}
              asking={asking}
              hasMessages={visibleMessages.length > 0}
              suggestions={
                visibleMessages.length ? latestSuggestions : SUGGESTED_PROMPTS
              }
              dark={dark}
              onChange={setQuestion}
              onSubmit={(value) => void submit(value)}
            />
          </Box>
        </Paper>
      </Box>

      <ChatDeleteDialog
        mode={confirmDelete}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={confirmDelete === "all" ? deleteAll : deleteSession}
      />
    </>
  );
};

export default ChatPopper;
