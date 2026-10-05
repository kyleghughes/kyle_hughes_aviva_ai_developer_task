import { Archive, ClipboardCheck, Clock3, XCircle } from "lucide-react";
import { Box, Stack, Typography } from "@mui/material";

// #region interfaces
export interface MetricsCounts {
  action: number;
  informational: number;
  irrelevant: number;
  pending: number;
}
//#endregion

// #region props interface
export interface MetricsProps {
  counts: MetricsCounts;
}
//#endregion

// #region constants
const metrics = [
  ["Actionable", "action", ClipboardCheck],
  ["Informational", "informational", Clock3],
  ["Irrelevant", "irrelevant", XCircle],
  ["Awaiting AI", "pending", Archive],
] as const;
//#endregion

export const Metrics = ({ counts }: MetricsProps) => (
  <Stack direction="row" spacing={1} sx={{ overflowX: "auto", pb: 0.5 }}>
    {metrics.map(([label, key, Icon]) => (
      <Box
        key={label}
        sx={{
          bgcolor: "background.paper",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 1,
          p: 1.5,
          minWidth: 115,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          gap: 0.5,
        }}
      >
        <Icon size={17} color="currentColor" />
        <Typography fontWeight={800} fontSize={19}>
          {counts[key]}
        </Typography>
        <Typography color="text.secondary" fontSize={10}>
          {label}
        </Typography>
      </Box>
    ))}
  </Stack>
);
