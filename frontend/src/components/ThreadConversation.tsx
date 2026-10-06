import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { User } from "lucide-react";

import type { Thread } from "../types/mailbox";

// #region props interface
export interface ThreadConversationProps {
  thread: Thread | null;
  loading: boolean;
}
//#endregion

// #region help functions
/**
 * Formats an ISO date/time value for display in the workload UI.
 *
 * Uses the UK locale and displays the date and time in a compact,
 * human-readable format.
 *
 * @param value Date/time value to format.
 * @returns Formatted date and time string.
 */
const formatDate = (value: string): string =>
  new Date(value).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
//#endregion

export const ThreadConversation = ({
  thread,
  loading,
}: ThreadConversationProps) => {
  if (loading)
    return (
      <Stack
        direction="row"
        spacing={1}
        alignItems="center"
        py={2}
        color="text.secondary"
      >
        <CircularProgress size={16} />
        <Typography fontSize={12}>Loading messages…</Typography>
      </Stack>
    );
  if (!thread)
    return (
      <Typography fontSize={12} color="text.secondary" py={2}>
        No messages available.
      </Typography>
    );
  return (
    <Stack spacing={1.5}>
      {[...thread.messages]
        .sort(
          (a, b) =>
            new Date(a.date_sent).getTime() - new Date(b.date_sent).getTime(),
        )
        .map((message) => (
          <Box
            key={message.message_id}
            sx={{
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 1,
              bgcolor: "background.default",
              p: 1.75,
            }}
          >
            <Stack
              direction="row"
              justifyContent="space-between"
              gap={1}
              alignItems="flex-start"
            >
              <Stack direction="row" spacing={1} minWidth={0}>
                <Box
                  sx={{
                    width: 28,
                    height: 28,
                    borderRadius: 1,
                    bgcolor: "action.hover",
                    color: "text.secondary",
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                  }}
                >
                  <User size={14} />
                </Box>
                <Box minWidth={0}>
                  <Typography
                    fontWeight={700}
                    fontSize={12}
                    sx={{ overflowWrap: "anywhere" }}
                  >
                    {message.sent_from}
                  </Typography>
                  <Typography
                    fontSize={10}
                    color="text.secondary"
                    sx={{ overflowWrap: "anywhere" }}
                  >
                    To: {message.sent_to.join(", ")}
                  </Typography>
                </Box>
              </Stack>
              <Typography
                component="time"
                fontSize={9}
                color="text.secondary"
                whiteSpace="nowrap"
              >
                {formatDate(message.date_sent)}
              </Typography>
            </Stack>
            {message.sent_cc?.length ? (
              <Typography fontSize={10} color="text.secondary" mt={1}>
                Cc: {message.sent_cc.join(", ")}
              </Typography>
            ) : null}
            <Divider sx={{ my: 1.25 }} />
            <Typography fontWeight={700} fontSize={11} mb={1}>
              {message.subject}
            </Typography>
            <Typography
              fontSize={12}
              lineHeight={1.55}
              color="text.primary"
              sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
            >
              {message.body}
            </Typography>
            {message.attachments?.length ? (
              <Stack direction="row" spacing={0.75} flexWrap="wrap" mt={1.25}>
                {message.attachments.map((a) => (
                  <Chip key={a.filename} size="small" label={a.filename} />
                ))}
              </Stack>
            ) : null}
          </Box>
        ))}
    </Stack>
  );
};
