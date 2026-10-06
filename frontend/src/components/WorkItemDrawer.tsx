import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import {
  CheckCircle2,
  MessageSquareText,
  Pin,
  RotateCcw,
  Sparkles,
  X,
} from "lucide-react";

import { useState } from "react";
import type { ReactNode } from "react";

import type { Item, Thread } from "../types/mailbox";

import { PriorityBadge, WorkTypeBadge } from "./Badge";
import { ThreadConversation } from "./ThreadConversation";

// #region props interface
export interface WorkItemDrawerProps {
  item: Item | null;
  thread: Thread | null;
  threadLoading: boolean;
  analyzing: boolean;
  onClose: () => void;
  onAskFollowUp: () => void;
  onDone: () => void;
  onIncomplete: () => void;
  onInProgress: () => void;
  onTypeChange: (type: "action" | "informational" | "irrelevant") => void;
  onPriorityChange: (priority: "high" | "medium" | "low") => void;
  onTogglePin: () => void;
}
// #endregion

// #region props interface
export interface SectionTitleProps {
  children: ReactNode;
}
// #endregion

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

export const WorkItemDrawer = ({
  item,
  thread,
  threadLoading,
  analyzing,
  onClose,
  onAskFollowUp,
  onDone,
  onIncomplete,
  onInProgress,
  onTypeChange,
  onPriorityChange,
  onTogglePin,
}: WorkItemDrawerProps) => {
  const actionable = item?.email_type === "action";
  const analysisComplete = item?.analysis_status === "analyzed";
  const disableActionButtons = actionable && !analysisComplete;
  const [typeMenuAnchor, setTypeMenuAnchor] = useState<null | HTMLElement>(
    null,
  );
  const [priorityMenuAnchor, setPriorityMenuAnchor] =
    useState<null | HTMLElement>(null);
  const canOverrideType = actionable && analysisComplete && !item?.done;
  const canOverridePriority = actionable && analysisComplete;

  return (
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
            EMAIL
          </Typography>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="flex-start"
            gap={1.5}
            mt={3}
          >
            <Typography variant="h2" fontSize={25} lineHeight={1.18} mb={1.5}>
              {item.subject}
            </Typography>
            <Button
              size="small"
              variant="outlined"
              startIcon={
                <Pin size={15} fill={item.pinned ? "currentColor" : "none"} />
              }
              onClick={onTogglePin}
              sx={{ textTransform: "none", flexShrink: 0 }}
            >
              {item.pinned ? "Unpin" : "Pin"}
            </Button>
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <WorkTypeBadge
              type={item.email_type}
              onClick={
                canOverrideType
                  ? (event) => setTypeMenuAnchor(event.currentTarget)
                  : undefined
              }
              disabled={!canOverrideType}
            />
            {actionable && (
              <PriorityBadge
                priority={item.priority}
                onClick={
                  canOverridePriority
                    ? (event) => setPriorityMenuAnchor(event.currentTarget)
                    : undefined
                }
                disabled={!canOverridePriority}
              />
            )}
            {item.done && (
              <Typography fontSize={10} fontWeight={800} color="success.main">
                ACTIONED
              </Typography>
            )}
          </Stack>
          <Menu
            anchorEl={typeMenuAnchor}
            open={Boolean(typeMenuAnchor)}
            onClose={() => setTypeMenuAnchor(null)}
          >
            <MenuItem
              selected={item.email_type === "action"}
              onClick={() => {
                setTypeMenuAnchor(null);
                onTypeChange("action");
              }}
            >
              Actionable
            </MenuItem>
            <MenuItem
              selected={item.email_type === "informational"}
              onClick={() => {
                setTypeMenuAnchor(null);
                onTypeChange("informational");
              }}
            >
              Informational
            </MenuItem>
            <MenuItem
              selected={item.email_type === "irrelevant"}
              onClick={() => {
                setTypeMenuAnchor(null);
                onTypeChange("irrelevant");
              }}
            >
              Irrelevant
            </MenuItem>
          </Menu>
          <Menu
            anchorEl={priorityMenuAnchor}
            open={Boolean(priorityMenuAnchor)}
            onClose={() => setPriorityMenuAnchor(null)}
          >
            <MenuItem
              selected={item.priority === "high"}
              onClick={() => {
                setPriorityMenuAnchor(null);
                onPriorityChange("high");
              }}
            >
              High
            </MenuItem>
            <MenuItem
              selected={item.priority === "medium"}
              onClick={() => {
                setPriorityMenuAnchor(null);
                onPriorityChange("medium");
              }}
            >
              Medium
            </MenuItem>
            <MenuItem
              selected={item.priority === "low"}
              onClick={() => {
                setPriorityMenuAnchor(null);
                onPriorityChange("low");
              }}
            >
              Low
            </MenuItem>
          </Menu>

          {actionable && (
            <>
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
                      <CheckCircle2 size={16} />
                    </ListItemIcon>
                    <ListItemText
                      primary={action}
                      primaryTypographyProps={{ fontSize: 13 }}
                    />
                  </ListItem>
                ))}
              </List>

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
                        sx={{
                          display: "list-item",
                          py: 0.25,
                          listStyle: "disc",
                        }}
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
                        sx={{
                          display: "list-item",
                          py: 0.25,
                          listStyle: "disc",
                        }}
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

              <Stack spacing={1.25} mt={3}>
                {item.done ? (
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<RotateCcw size={16} />}
                    onClick={onIncomplete}
                    sx={{ textTransform: "none", minHeight: 42 }}
                  >
                    Mark incomplete
                  </Button>
                ) : item.in_progress ? (
                  <Button
                    fullWidth
                    variant="contained"
                    startIcon={<CheckCircle2 size={16} />}
                    disabled={disableActionButtons}
                    onClick={onDone}
                    sx={{ textTransform: "none", minHeight: 42 }}
                  >
                    Mark as actioned
                  </Button>
                ) : (
                  <Button
                    fullWidth
                    variant="contained"
                    disabled={disableActionButtons}
                    onClick={onInProgress}
                    sx={{ textTransform: "none", minHeight: 42 }}
                  >
                    Mark as in progress
                  </Button>
                )}
                {analysisComplete && (
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<MessageSquareText size={16} />}
                    onClick={onAskFollowUp}
                    sx={{ textTransform: "none", minHeight: 42 }}
                  >
                    Ask follow-up
                  </Button>
                )}
              </Stack>

              <SectionTitle>Conversation</SectionTitle>
              <ThreadConversation thread={thread} loading={threadLoading} />
            </>
          )}

          {!actionable && (
            <>
              <SectionTitle>Conversation</SectionTitle>
              <ThreadConversation thread={thread} loading={threadLoading} />
              <Button
                fullWidth
                variant="contained"
                onClick={() => onTypeChange("action")}
                sx={{ textTransform: "none", minHeight: 42, mt: 3 }}
              >
                Make actionable
              </Button>
            </>
          )}
        </Box>
      )}
    </Drawer>
  );
};
