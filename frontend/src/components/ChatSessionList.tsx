import { Plus, Trash2 } from "lucide-react";
import {
  Box,
  Button,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import type { ChatSession } from "../types/mailbox";
import { formatSessionDate } from "../types/chatTypes";

// #region props interface
export interface ChatSessionListProps {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDeleteAll: () => void;
}
//#endregion

export const ChatSessionList = ({
  sessions,
  activeId,
  onSelect,
  onNew,
  onDeleteAll,
}: ChatSessionListProps) => (
  <Box
    sx={{
      width: { xs: 0, sm: 220 },
      display: { xs: "none", sm: "flex" },
      flexDirection: "column",
      borderRight: "1px solid",
      borderColor: "divider",
      bgcolor: "background.default",
    }}
  >
    <Stack
      direction="row"
      alignItems="center"
      justifyContent="space-between"
      sx={{ p: 1.5 }}
    >
      <Typography fontWeight={800} fontSize={14}>
        Chats
      </Typography>
      <Tooltip title="New chat">
        <IconButton size="small" onClick={onNew}>
          <Plus size={17} />
        </IconButton>
      </Tooltip>
    </Stack>
    <Divider />
    <Box sx={{ flex: 1, overflowY: "auto", p: 1 }}>
      {!sessions.length && (
        <Typography color="text.secondary" fontSize={12} sx={{ p: 1.25 }}>
          Your conversations will appear here.
        </Typography>
      )}
      <Stack spacing={0.5}>
        {sessions.map((session) => (
          <Button
            key={session.id}
            onClick={() => onSelect(session.id)}
            sx={{
              display: "block",
              textAlign: "left",
              textTransform: "none",
              px: 1.25,
              py: 1,
              borderRadius: 1,
              bgcolor:
                activeId === session.id ? "action.selected" : "transparent",
              color: "text.primary",
            }}
          >
            <Typography noWrap fontSize={12} fontWeight={700}>
              {session.title}
            </Typography>
            <Typography
              noWrap
              fontSize={10}
              color="text.secondary"
              sx={{ mt: 0.25 }}
            >
              {formatSessionDate(session.lastInteractedAt)}
            </Typography>
          </Button>
        ))}
      </Stack>
    </Box>
    <Divider />
    <Stack direction="row" spacing={0.5} sx={{ p: 1 }}>
      <Button
        size="small"
        onClick={onNew}
        startIcon={<Plus size={14} />}
        sx={{ textTransform: "none", flex: 1 }}
      >
        New chat
      </Button>
      <Tooltip title="Delete all chat history">
        <IconButton
          size="small"
          onClick={onDeleteAll}
          disabled={!sessions.length}
          aria-label="Delete all chat history"
        >
          <Trash2 size={15} />
        </IconButton>
      </Tooltip>
    </Stack>
  </Box>
);
