import Chip from "@mui/material/Chip";
import type { MouseEvent } from "react";
import type { EmailType, Priority } from "../types/mailbox";

// #region props interface
export interface WorkTypeBadgeProps {
  type: EmailType;
  onClick?: (event: MouseEvent<HTMLDivElement>) => void;
  disabled?: boolean;
}
// #endregion

export const WorkTypeBadge = ({ type, onClick, disabled = false }: WorkTypeBadgeProps) => {
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
      onClick={onClick}
      disabled={disabled}
      clickable={Boolean(onClick) && !disabled}
      sx={{ fontWeight: 800 }}
    />
  );
};


export interface PriorityBadgeProps {
  priority: Priority | null;
  onClick?: (event: MouseEvent<HTMLDivElement>) => void;
  disabled?: boolean;
}

export const PriorityBadge = ({ priority, onClick, disabled = false }: PriorityBadgeProps) => {
  if (!priority) {
    return (
      <Chip
        size="small"
        variant="outlined"
        label="Not assessed"
        onClick={onClick}
        disabled={disabled}
        clickable={Boolean(onClick) && !disabled}
        sx={{ fontWeight: 700 }}
      />
    );
  }

  const colours = {
    high: "error",
    medium: "warning",
    low: "default",
  } as const;

  const labels = {
    high: "High",
    medium: "Medium",
    low: "Low",
  } as const;

  return (
    <Chip
      size="small"
      color={colours[priority]}
      label={labels[priority]}
      onClick={onClick}
      disabled={disabled}
      clickable={Boolean(onClick) && !disabled}
      sx={{ fontWeight: 800 }}
    />
  );
};
