import { Pagination, Stack, Typography } from "@mui/material";

// #region props interface
export interface WorkloadPaginationProps {
  page: number;
  totalPages: number;
  from: number;
  to: number;
  total: number;
  onPageChange: (page: number) => void;
}
//#endregion

export const WorkloadPagination = ({
  page,
  totalPages,
  from,
  to,
  total,
  onPageChange,
}: WorkloadPaginationProps) => {
  if (total === 0) return null;
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      justifyContent="space-between"
      alignItems="center"
      spacing={1.5}
      sx={{ py: 2 }}
    >
      <Typography fontSize={12} color="text.secondary">
        Showing {from}–{to} of {total} threads
      </Typography>
      <Pagination
        count={totalPages}
        page={page}
        onChange={(_, value) => onPageChange(value)}
        size="small"
        color="primary"
        shape="rounded"
      />
    </Stack>
  );
};
