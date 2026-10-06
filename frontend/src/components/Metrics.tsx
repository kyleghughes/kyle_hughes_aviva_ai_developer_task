import { Archive, CheckCircle2, ClipboardCheck, Clock3 } from "lucide-react";
import { Box, Stack, Typography } from "@mui/material";

export interface MetricsCounts {
  action: number;
  archive: number;
  done: number;
  pending: number;
}

export interface MetricsProps { counts: MetricsCounts; }

const metrics = [
  ["Actionable", "action", ClipboardCheck],
  ["Archived", "archive", Archive],
  ["Actioned", "done", CheckCircle2],
  ["Awaiting AI", "pending", Clock3],
] as const;

export const Metrics = ({ counts }: MetricsProps) => (
  <Stack direction="row" spacing={1} sx={{ overflowX: "auto", pb: 0.5 }}>
    {metrics.map(([label, key, Icon]) => (
      <Box key={label} sx={{ bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1, p: 1.5, minWidth: 115, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", gap: 0.5 }}>
        <Icon size={17} color="currentColor" />
        <Typography fontWeight={800} fontSize={19}>{counts[key]}</Typography>
        <Typography color="text.secondary" fontSize={10}>{label}</Typography>
      </Box>
    ))}
  </Stack>
);
