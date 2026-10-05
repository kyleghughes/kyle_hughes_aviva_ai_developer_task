import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { Mail, Moon, RefreshCw, Sun } from "lucide-react";

// #region props interface
export interface AppHeaderProps {
  status: string;
  onRefresh: () => void;
  mode: "light" | "dark";
  onToggleMode: () => void;
}
// #endregion

export const AppHeader = ({
  status,
  onRefresh,
  mode,
  onToggleMode,
}: AppHeaderProps) => {
  // #region variable
  const dark = mode === "dark";
  // #endregion

  return (
    <Box
      component="header"
      sx={{
        minHeight: 70,
        bgcolor: dark ? "#0C1B25" : "#003B5C",
        color: "white",
        px: { xs: 2, md: 6 },
        py: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 2,
      }}
    >
      <Stack direction="row" spacing={1.5} alignItems="center" minWidth={0}>
        <Box
          sx={{
            width: 36,
            height: 36,
            flexShrink: 0,
            borderRadius: 1,
            bgcolor: "#F7C948",
            color: "#003B5C",
            display: "grid",
            placeItems: "center",
          }}
        >
          <Mail size={20} />
        </Box>
        <Box minWidth={0}>
          <Typography fontWeight={800} fontSize={16}>
            Claims Inbox
          </Typography>
          <Typography fontSize={11} sx={{ color: "rgba(255,255,255,.68)" }}>
            Workload intelligence
          </Typography>
        </Box>
      </Stack>
      <Stack direction="row" spacing={1} alignItems="center">
        <Box
          sx={{ width: 7, height: 7, bgcolor: "#F7C948", borderRadius: "50%" }}
        />
        <Typography
          sx={{
            color: "rgba(255,255,255,.72)",
            fontSize: 12,
            display: { xs: "none", sm: "block" },
          }}
        >
          {status}
        </Typography>
        <Tooltip title={dark ? "Switch to light mode" : "Switch to dark mode"}>
          <IconButton
            onClick={onToggleMode}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
            sx={{
              color: "white",
              borderRadius: 1,
              "&:hover": { bgcolor: "rgba(255,255,255,.10)" },
            }}
          >
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </IconButton>
        </Tooltip>
        <Button
          size="small"
          variant="contained"
          startIcon={<RefreshCw size={15} />}
          onClick={onRefresh}
          sx={{
            bgcolor: "#F7C948",
            color: "#003B5C",
            "&:hover": { bgcolor: "#E6B836" },
          }}
        >
          Refresh
        </Button>
      </Stack>
    </Box>
  );
};
