import type { ReactNode } from "react";
import {
  CheckCircle2,
  MessageSquareText,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";
import {
  Box,
  Button,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import type { Item, Thread } from "../types/mailbox";
import { WorkTypeBadge } from "./Badge";
import { ThreadConversation } from "./ThreadConversation";

// #region interfaces
export interface WorkItemDrawerProps {
  item: Item | null;
  thread: Thread | null;
  threadLoading: boolean;
  analyzing: boolean;
  onClose: () => void;
  onAskFollowUp: () => void;
  onDone: () => void;
  onIncomplete: () => void;
}
//#endregion

// #region props interface
export interface SectionTitleProps {
  children: ReactNode;
}
//#endregion

// #region sub-components
export const SectionTitle = ({ children }: SectionTitleProps) => (
  <Typography
    sx={{
      fontSize: 11,
      fontWeight: 800,
      letterSpacing: ".08em",
      textTransform: "uppercase",
      color: "text.secondary",
      mt: 3,
      mb: 1,
    }}
  >
    {children}
  </Typography>
);
//#endregion

export const WorkItemDrawer = ({
  item,
  thread,
  threadLoading,
  analyzing,
  onClose,
  onAskFollowUp,
  onDone,
  onIncomplete,
}: WorkItemDrawerProps) => (
  <Drawer
    anchor="right"
    open={Boolean(item)}
    onClose={onClose}
    PaperProps={{
      sx: { width: { xs: "92vw", sm: 520 }, p: { xs: 2.5, sm: 4 } },
    }}
  >
    {item && (
      <Box position="relative">
        <IconButton
          onClick={onClose}
          sx={{ position: "absolute", right: -8, top: -12 }}
          aria-label="Close"
        >
          <X />
        </IconButton>
        <Typography
          sx={{
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: ".13em",
            color: "text.secondary",
            mb: 1,
          }}
        >
          WORK ITEM
        </Typography>
        <Typography variant="h2" fontSize={25} lineHeight={1.18} mb={1.5}>
          {item.subject}
        </Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <WorkTypeBadge type={item.email_type} />
          {item.done && (
            <Typography fontSize={10} fontWeight={800} color="success.main">
              DONE
            </Typography>
          )}
          {item.confidence !== null && (
            <Typography fontSize={10} color="text.secondary">
              LLM confidence {Math.round(item.confidence * 100)}%
            </Typography>
          )}
        </Stack>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} mt={2}>
          {item.done ? (
            <Button
              variant="outlined"
              startIcon={<RotateCcw size={16} />}
              onClick={onIncomplete}
              sx={{ textTransform: "none" }}
            >
              Still incomplete
            </Button>
          ) : (
            <Button
              variant="contained"
              startIcon={<CheckCircle2 size={16} />}
              onClick={onDone}
              sx={{ textTransform: "none" }}
            >
              Mark as done
            </Button>
          )}
          {item.analysis_status === "analyzed" && (
            <Button
              variant="outlined"
              startIcon={<MessageSquareText size={16} />}
              onClick={onAskFollowUp}
              sx={{ textTransform: "none" }}
            >
              Ask follow-up
            </Button>
          )}
        </Stack>

        <SectionTitle>Summary</SectionTitle>
        {analyzing ? (
          <Stack direction="row" spacing={1} alignItems="center" py={2}>
            <Sparkles size={18} />
            <Typography fontWeight={600}>
              Analysing this thread with Ollama…
            </Typography>
          </Stack>
        ) : (
          <Typography color="text.primary" lineHeight={1.55}>
            {item.summary}
          </Typography>
        )}

        <SectionTitle>Why this needs attention</SectionTitle>
        {item.analysis_status === "analyzed" ? (
          <>
            <Typography fontSize={12} fontWeight={700} mb={0.5}>
              Urgency signals
            </Typography>
            <List dense sx={{ pl: 2, mb: 1 }}>
              {(item.urgency_signals.length
                ? item.urgency_signals
                : ["No explicit urgency signal identified."]
              ).map((signal) => (
                <ListItem
                  key={signal}
                  sx={{ display: "list-item", py: 0.25, listStyle: "disc" }}
                >
                  <ListItemText
                    primary={signal}
                    primaryTypographyProps={{
                      fontSize: 13,
                      color: "text.secondary",
                    }}
                  />
                </ListItem>
              ))}
            </List>
            <Typography fontSize={12} fontWeight={700} mb={0.5}>
              Importance signals
            </Typography>
            <List dense sx={{ pl: 2 }}>
              {(item.importance_signals.length
                ? item.importance_signals
                : ["No explicit importance signal identified."]
              ).map((signal) => (
                <ListItem
                  key={signal}
                  sx={{ display: "list-item", py: 0.25, listStyle: "disc" }}
                >
                  <ListItemText
                    primary={signal}
                    primaryTypographyProps={{
                      fontSize: 13,
                      color: "text.secondary",
                    }}
                  />
                </ListItem>
              ))}
            </List>
          </>
        ) : (
          <Typography fontSize={13} color="text.secondary">
            Open analysis will use Ollama to identify evidence of urgency,
            importance and required action.
          </Typography>
        )}

        <SectionTitle>Conversation</SectionTitle>
        <ThreadConversation thread={thread} loading={threadLoading} />

        <SectionTitle>Required actions</SectionTitle>
        <List dense disablePadding>
          {(item.actions.length
            ? item.actions
            : [
                item.analysis_status === "analyzed"
                  ? "No explicit action identified."
                  : "Open analysis",
              ]
          ).map((action) => (
            <ListItem key={action} disableGutters>
              <ListItemIcon sx={{ minWidth: 26 }}>
                <CheckCircle2 size={16} color="currentColor" />
              </ListItemIcon>
              <ListItemText
                primary={action}
                primaryTypographyProps={{ fontSize: 13, color: "text.primary" }}
              />
            </ListItem>
          ))}
        </List>

        <Box
          sx={{
            display: "flex",
            gap: 1,
            bgcolor: "action.hover",
            p: 1.5,
            borderRadius: 1,
            mt: 3,
            color: "text.secondary",
          }}
        >
          <MessageSquareText size={16} />
          <Typography fontSize={11} lineHeight={1.4}>
            Business rules determine whether this is actionable, informational
            or irrelevant. AI provides decision support; it does not assign a
            priority category.
          </Typography>
        </Box>
        <Typography
          fontFamily="monospace"
          fontSize={9}
          color="text.secondary"
          mt={1}
        >
          {item.thread_id}
        </Typography>
      </Box>
    )}
  </Drawer>
);
