import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { Send } from "lucide-react";

// #region props interface
export interface ChatComposerProps {
  question: string;
  asking: boolean;
  hasMessages: boolean;
  suggestions: string[];
  dark: boolean;
  onChange: (value: string) => void;
  onSubmit: (value?: string) => void;
}
// #endregion

export const ChatComposer = ({
  question,
  asking,
  hasMessages,
  suggestions,
  dark,
  onChange,
  onSubmit,
}: ChatComposerProps) => (
  <Box sx={{ p: 1.5, bgcolor: "background.paper" }}>
    {!hasMessages && (
      <Stack
        direction="row"
        spacing={0.75}
        flexWrap="wrap"
        useFlexGap
        sx={{ mb: 1 }}
      >
        {suggestions.map((prompt) => (
          <Chip
            key={prompt}
            label={prompt}
            onClick={() => onSubmit(prompt)}
            variant="outlined"
            clickable
            size="small"
          />
        ))}
      </Stack>
    )}
    {hasMessages && suggestions.length > 0 && !asking && (
      <Stack spacing={0.5} sx={{ mb: 1 }}>
        <Typography fontSize={10} fontWeight={800} color="text.secondary">
          Suggested follow-ups
        </Typography>
        <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
          {suggestions.map((suggestion) => (
            <Chip
              key={suggestion}
              label={suggestion}
              onClick={() => onSubmit(suggestion)}
              variant="outlined"
              clickable
              size="small"
            />
          ))}
        </Stack>
      </Stack>
    )}
    <Stack direction="row" spacing={1} alignItems="flex-end">
      <TextField
        fullWidth
        multiline
        maxRows={4}
        value={question}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSubmit();
          }
        }}
        placeholder="Ask about your mailbox…"
        disabled={asking}
      />
      <IconButton
        onClick={() => onSubmit()}
        disabled={!question.trim() || asking}
        aria-label="Send message"
        sx={{
          bgcolor: dark ? "#F7C948" : "primary.main",
          color: dark ? "#10202D" : "primary.contrastText",
          borderRadius: 1,
          width: 40,
          height: 40,
          mb: 0.25,
          "&:hover": { bgcolor: dark ? "#E8C84A" : "primary.dark" },
        }}
      >
        <Send size={17} />
      </IconButton>
    </Stack>
  </Box>
);
