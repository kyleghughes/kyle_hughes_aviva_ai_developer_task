import { Box, Chip, IconButton, Paper, Table, TableBody, TableCell, TableHead, TableRow, Tooltip, Typography } from "@mui/material";
import { Pin } from "lucide-react";
import type { Item } from "../types/mailbox";
import { PriorityBadge, WorkTypeBadge } from "./Badge";

export interface WorkloadTableProps {
  items: Item[];
  onOpen: (item: Item) => void;
  onTogglePin: (item: Item) => void;
}

export const WorkloadTable = ({ items, onOpen, onTogglePin }: WorkloadTableProps) => (
  <Paper sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, overflow: "hidden" }}>
    <Table size="small" sx={{ tableLayout: "fixed", width: "100%" }}>
      <TableHead><TableRow sx={{ bgcolor: "background.default" }}>
        <TableCell>Work item</TableCell><TableCell>Priority</TableCell><TableCell>Type</TableCell><TableCell>Latest</TableCell>
      </TableRow></TableHead>
      <TableBody>{items.map((item) => {
        const actionable = item.email_type === "action";
        return (
          <TableRow hover key={item.thread_id} onClick={() => onOpen(item)} sx={{ cursor: "pointer" }}>
            <TableCell sx={{ overflow: "hidden" }}><Box sx={{ display: "flex", alignItems: "center", gap: 1 }}><Tooltip title={item.pinned ? "Pinned" : "Pin thread"}><IconButton size="small" onClick={(event) => { event.stopPropagation(); void onTogglePin(item); }} aria-label={item.pinned ? "Unpin thread" : "Pin thread"} sx={{ color: item.pinned ? "primary.main" : "text.disabled" }}><Pin size={15} fill={item.pinned ? "currentColor" : "none"} /></IconButton></Tooltip><Box minWidth={0}><Typography fontWeight={700} fontSize={13} noWrap>{item.subject}</Typography><Typography color="text.secondary" fontSize={11} mt={0.5} noWrap>{item.topic || (actionable ? "Awaiting analysis" : "Conversation only")} · {item.sender} · {item.message_count} msg</Typography></Box></Box></TableCell>
            <TableCell>{actionable ? <PriorityBadge priority={item.priority} /> : null}</TableCell>
            <TableCell>{item.done ? <Chip size="small" color="success" label="Actioned" sx={{ fontWeight: 800 }} /> : item.in_progress ? <Chip size="small" color="info" label="In Progress" sx={{ fontWeight: 800 }} /> : <WorkTypeBadge type={item.email_type} />}</TableCell>
            <TableCell><Typography fontSize={11} color="text.secondary">{new Date(item.latest_date).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}</Typography></TableCell>
          </TableRow>
        );
      })}</TableBody>
    </Table>
    {!items.length && <Box p={6} textAlign="center"><Typography color="text.secondary">No items in this view.</Typography></Box>}
  </Paper>
);
