import Chip from "@mui/material/Chip";
import type { EmailType } from "../types/mailbox";

// #region props interface
export interface WorkTypeBadgeProps {
  type: EmailType;
}
// #endregion

export const WorkTypeBadge = ({ type }: WorkTypeBadgeProps) => {
  // #region constants
  const colours = {
    action: "warning",
    informational: "info",
    irrelevant: "default",
  } as const;
  const labels = {
    action: "Actionable",
    informational: "Informational",
    irrelevant: "Irrelevant",
  } as const;
  // #endregion
  return (
    <Chip
      size="small"
      color={colours[type]}
      label={labels[type]}
      sx={{ fontWeight: 800 }}
    />
  );
};
