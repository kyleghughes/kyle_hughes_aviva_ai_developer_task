import { useMemo, useState } from "react";

import App from "./App";
import { createAppTheme } from "./theme/theme";
import "./styles.css";
import { ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";

const Root = () => {
  const [mode, setMode] = useState<"light" | "dark">(() => {
    const stored = localStorage.getItem("claims-inbox-theme");

    return stored === "dark" ? "dark" : "light";
  });
  const theme = useMemo(() => createAppTheme(mode), [mode]);

  /**
   * Switches between light and dark mode.
   *
   * The selected mode is also persisted so it is restored when the
   * application is opened again.
   *
   * @returns void.
   */
  const toggleMode = (): void => {
    setMode((current) => {
      const next = current === "light" ? "dark" : "light";

      localStorage.setItem("claims-inbox-theme", next);

      return next;
    });
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App mode={mode} onToggleMode={toggleMode} />
    </ThemeProvider>
  );
};

export default Root;
