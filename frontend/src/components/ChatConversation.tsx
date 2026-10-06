import { Bot, UserRound } from "lucide-react";
import type { ChatMessage } from "../types/mailbox";
import Stack from "@mui/material/Stack";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";

// #region props interface
export interface ChatConversationProps {
  messages: ChatMessage[];
  asking: boolean;
  dark: boolean;
}
// #endregion

export const ChatConversation = ({
  messages,
  asking,
  dark,
}: ChatConversationProps) => (
  <Stack spacing={1.5}>
    {messages.map((message) => (
      <Stack
        key={message.id}
        direction="row"
        spacing={1}
        justifyContent={message.role === "user" ? "flex-end" : "flex-start"}
      >
        {message.role === "assistant" && (
          <Bot size={16} style={{ marginTop: 8, flexShrink: 0 }} />
        )}
        <Paper
          elevation={0}
          sx={{
            maxWidth: "86%",
            px: 1.5,
            py: 1.15,
            bgcolor:
              message.role === "user"
                ? dark
                  ? "#F7C948"
                  : "primary.main"
                : "background.paper",
            color:
              message.role === "user"
                ? dark
                  ? "#10202D"
                  : "#FFFFFF"
                : "text.primary",
            border: "1px solid",
            borderColor: message.role === "user" ? "transparent" : "divider",
            borderRadius: 1,
          }}
        >
          <Typography
            fontSize={13}
            lineHeight={1.55}
            sx={{ whiteSpace: "pre-wrap" }}
          >
            {message.content}
          </Typography>
          {message.threadIds?.length ? (
            <Stack direction="row" spacing={0.5} flexWrap="wrap" mt={1}>
              {message.threadIds.map((id) => (
                <Chip
                  key={id}
                  label={message.threadTitles?.[id] ?? id}
                  title={message.threadTitles?.[id] ?? id}
                  size="small"
                  sx={{
                    height: 24,
                    fontSize: 10,
                    maxWidth: 420,
                    "& .MuiChip-label": {
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    },
                  }}
                />
              ))}
            </Stack>
          ) : null}
        </Paper>
        {message.role === "user" && (
          <UserRound size={16} style={{ marginTop: 8, flexShrink: 0 }} />
        )}
      </Stack>
    ))}
    {asking && (
      <Stack
        direction="row"
        spacing={1}
        alignItems="center"
        sx={{ color: "text.secondary" }}
      >
        <Bot size={16} />
        <Typography fontSize={12}>Thinking…</Typography>
      </Stack>
    )}
  </Stack>
);

export const EmptyChatState = () => (
  <Stack
    alignItems="center"
    textAlign="center"
    spacing={1}
    sx={{ pt: 5, px: 2 }}
  >
    <Box
      sx={{
        width: 44,
        height: 44,
        borderRadius: 1,
        bgcolor: "action.hover",
        color: "primary.main",
        display: "grid",
        placeItems: "center",
      }}
    >
      <Bot size={22} />
    </Box>
    <Typography fontWeight={800}>How can I help?</Typography>
    <Typography fontSize={12} color="text.secondary" sx={{ maxWidth: 320 }}>
      Ask about emails, actions, conversations or your current workload.
    </Typography>
  </Stack>
);
