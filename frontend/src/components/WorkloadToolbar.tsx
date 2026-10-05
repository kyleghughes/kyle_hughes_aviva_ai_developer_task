import { Search } from "lucide-react";
import {
  Button,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import type { Filter } from "../types/mailbox";

// #region props interface
export interface WorkloadToolbarProps {
  filter: Filter;
  search: string;
  count: number;
  onFilter: (filter: Filter) => void;
  onSearch: (value: string) => void;
}
//#endregion

// #region Constants
const filters: Filter[] = [
  "all",
  "action",
  "informational",
  "irrelevant",
  "done",
];
const labels: Record<Filter, string> = {
  all: "Open",
  action: "Actionable",
  informational: "Informational",
  irrelevant: "Irrelevant",
  done: "Done",
};
//#endregion

export const WorkloadToolbar = ({
  filter,
  search,
  count,
  onFilter,
  onSearch,
}: WorkloadToolbarProps) => (
  <Stack spacing={1.25} sx={{ my: 1.5 }}>
    <Stack
      direction={{ xs: "column", md: "row" }}
      justifyContent="space-between"
      alignItems={{ xs: "stretch", md: "center" }}
      sx={{ gap: 1 }}
    >
      <Stack
        direction="row"
        spacing={0.75}
        role="tablist"
        aria-label="Workload type filters"
        sx={{ overflowX: "auto" }}
      >
        {filters.map((value) => {
          const selected = filter === value;
          return (
            <Button
              key={value}
              size="small"
              onClick={() => onFilter(value)}
              variant={selected ? "contained" : "outlined"}
              role="tab"
              aria-selected={selected}
              sx={{
                minHeight: 34,
                px: 1.5,
                whiteSpace: "nowrap",
                borderRadius: 1,
                fontWeight: selected ? 800 : 600,
                borderColor: selected ? "primary.main" : "divider",
                color: selected ? "primary.contrastText" : "text.secondary",
                bgcolor: selected ? "primary.main" : "background.paper",
                boxShadow: selected ? "0 0 0 2px rgba(247,201,72,.28)" : "none",
                "&:hover": {
                  bgcolor: selected ? "primary.dark" : "action.hover",
                  borderColor: selected ? "primary.dark" : "text.secondary",
                },
              }}
            >
              {labels[value]}
            </Button>
          );
        })}
      </Stack>
      <Typography fontSize={12} color="text.secondary" sx={{ flexShrink: 0 }}>
        {count} threads
      </Typography>
    </Stack>
    <TextField
      size="small"
      value={search}
      onChange={(event) => onSearch(event.target.value)}
      placeholder="Search threads by subject, sender, topic or thread ID"
      aria-label="Search threads"
      fullWidth
      InputProps={{
        startAdornment: (
          <InputAdornment position="start">
            <Search size={17} />
          </InputAdornment>
        ),
      }}
      sx={{ maxWidth: 620 }}
    />
  </Stack>
);
