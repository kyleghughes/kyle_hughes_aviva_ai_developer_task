import { CheckCircle2, RotateCcw } from "lucide-react";
import {
  Box,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import type { Item } from "../types/mailbox";
import { WorkTypeBadge } from "./Badge";

// #region props interface
export interface WorkloadTableProps {
  items: Item[];
  onOpen: (item: Item) => void;
  onDone: (item: Item) => void;
  onIncomplete: (item: Item) => void;
}
//#endregion

export const WorkloadTable = ({
  items,
  onOpen,
  onDone,
  onIncomplete,
}: WorkloadTableProps) => (
  <Paper
    sx={{
      border: "1px solid",
      borderColor: "divider",
      borderRadius: 1,
      overflow: "hidden",
    }}
  >
    <Table size="small" sx={{ tableLayout: "fixed", width: "100%" }}>
      <colgroup>
        <col style={{ width: "34%" }} />
        <col style={{ width: "31%" }} />
        <col style={{ width: "13%" }} />
        <col style={{ width: "12%" }} />
        <col style={{ width: "10%" }} />
      </colgroup>
      <TableHead>
        <TableRow sx={{ bgcolor: "background.default" }}>
          <TableCell>Work item</TableCell>
          <TableCell>AI decision support</TableCell>
          <TableCell>Type</TableCell>
          <TableCell>Latest</TableCell>
          <TableCell align="right">Status</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {items.map((item) => (
          <TableRow
            hover
            key={item.thread_id}
            onClick={() => onOpen(item)}
            sx={{ cursor: "pointer" }}
          >
            <TableCell sx={{ overflow: "hidden" }}>
              <Typography fontWeight={700} fontSize={13} noWrap>
                {item.subject}
              </Typography>
              <Typography color="text.secondary" fontSize={11} mt={0.5} noWrap>
                {item.topic || "Awaiting analysis"} · {item.sender} ·{" "}
                {item.message_count} msg
              </Typography>
            </TableCell>
            <TableCell sx={{ overflow: "hidden" }}>
              <Typography fontSize={12} color="text.secondary" noWrap>
                {item.analysis_status === "analyzed"
                  ? item.actions[0] || item.summary
                  : "Click to analyse"}
              </Typography>
            </TableCell>
            <TableCell>
              <WorkTypeBadge type={item.email_type} />
            </TableCell>
            <TableCell>
              <Typography fontSize={11} color="text.secondary">
                {new Date(item.latest_date).toLocaleDateString("en-GB", {
                  day: "2-digit",
                  month: "short",
                })}
              </Typography>
            </TableCell>
            <TableCell
              align="right"
              onClick={(event) => event.stopPropagation()}
            >
              <Tooltip
                title={item.done ? "Mark still incomplete" : "Mark done"}
              >
                <IconButton
                  size="small"
                  aria-label={item.done ? "Mark still incomplete" : "Mark done"}
                  onClick={() =>
                    item.done ? onIncomplete(item) : onDone(item)
                  }
                >
                  {item.done ? (
                    <RotateCcw size={16} />
                  ) : (
                    <CheckCircle2 size={16} />
                  )}
                </IconButton>
              </Tooltip>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
    {!items.length && (
      <Box p={6} textAlign="center">
        <Typography color="text.secondary">No items in this view.</Typography>
      </Box>
    )}
  </Paper>
);
