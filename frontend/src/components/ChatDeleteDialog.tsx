import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Typography from "@mui/material/Typography";

// #region props interface
export interface ChatDeleteDialogProps {
  mode: "session" | "all" | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export const ChatDeleteDialog = ({
  mode,
  onCancel,
  onConfirm,
}: ChatDeleteDialogProps) => (
  <Dialog open={mode !== null} onClose={onCancel}>
    <DialogTitle>
      {mode === "all"
        ? "Delete all chat history?"
        : "Delete this chat session?"}
    </DialogTitle>
    <DialogContent>
      <Typography fontSize={14} color="text.secondary">
        {mode === "all"
          ? "This will permanently remove every saved chat session from this browser."
          : "This will permanently remove this session and its messages from this browser."}
      </Typography>
    </DialogContent>
    <DialogActions>
      <Button onClick={onCancel} sx={{ textTransform: "none" }}>
        Cancel
      </Button>
      <Button
        color="error"
        variant="contained"
        onClick={onConfirm}
        sx={{ textTransform: "none" }}
      >
        Delete
      </Button>
    </DialogActions>
  </Dialog>
);
