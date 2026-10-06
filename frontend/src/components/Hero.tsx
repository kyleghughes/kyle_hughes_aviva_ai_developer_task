import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { Metrics } from "./Metrics";
import type { MetricsCounts } from "./Metrics";

// #region props interface
export interface HeroProps {
  counts: MetricsCounts;
}
//#endregion

export const Hero = ({ counts }: HeroProps) => (
  <Box
    sx={{
      display: "flex",
      justifyContent: "space-between",
      alignItems: "flex-end",
      gap: 3,
      mb: 3.5,
      flexWrap: "wrap",
    }}
  >
    <Box>
      <Typography
        sx={{
          fontSize: 10,
          fontWeight: 800,
          letterSpacing: ".13em",
          color: "text.secondary",
          mb: 1,
        }}
      >
        HANDLER WORKLOAD
      </Typography>
      <Typography
        variant="h1"
        sx={{ fontSize: { xs: 29, md: 36 }, letterSpacing: "-.04em" }}
      >
        What needs my attention?
      </Typography>
      <Typography color="text.secondary" mt={1}>
        Business rules classify the mailbox. AI provides decision support when
        you open an email.
      </Typography>
    </Box>
    <Metrics counts={counts} />
  </Box>
);
