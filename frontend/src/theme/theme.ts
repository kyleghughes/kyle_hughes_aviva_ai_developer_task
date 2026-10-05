import { createTheme, type PaletteMode } from "@mui/material/styles";

const BLUE = "#003B5C";
const BLUE_DARK = "#002B42";
const YELLOW = "#DFAF20";

export const createAppTheme = (mode: PaletteMode) => {
  const dark = mode === "dark";

  return createTheme({
    palette: {
      mode,
      primary: {
        main: dark ? "#F7C948" : BLUE,
        dark: dark ? YELLOW : BLUE_DARK,
        light: dark ? "#FFE28A" : "#EAF0F4",
        contrastText: dark ? "#18202A" : "#FFFFFF",
      },
      secondary: {
        main: dark ? "#8FB7CC" : "#4D7185",
        contrastText: dark ? "#07131B" : "#FFFFFF",
      },
      background: {
        default: dark ? "#101A22" : "#F7F7F5",
        paper: dark ? "#17232D" : "#FFFFFF",
      },
      text: {
        primary: dark ? "#F5F7F8" : "#142B3A",
        secondary: dark ? "#B6C3CB" : "#5D6C76",
      },
      divider: dark ? "#30414D" : "#DCE2E5",
      success: { main: dark ? "#6FCF97" : "#287A4B" },
      warning: { main: dark ? "#F7C948" : "#C58A00" },
      error: { main: dark ? "#FF7B72" : "#C43D35" },
      info: { main: dark ? "#7DB5D4" : "#3E718E" },
    },
    typography: {
      fontFamily: '"DM Sans", Arial, sans-serif',
      h1: { fontFamily: '"Manrope", Arial, sans-serif', fontWeight: 800 },
      h2: { fontFamily: '"Manrope", Arial, sans-serif', fontWeight: 800 },
      h3: { fontFamily: '"Manrope", Arial, sans-serif', fontWeight: 800 },
    },
    shape: { borderRadius: 4 },
    components: {
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: { root: { borderRadius: 4 } },
      },
      MuiChip: { styleOverrides: { root: { borderRadius: 4 } } },
      MuiPaper: {
        styleOverrides: { root: { backgroundImage: "none", borderRadius: 4 } },
      },
      MuiCard: { styleOverrides: { root: { borderRadius: 4 } } },
      MuiTextField: { defaultProps: { size: "small" } },
      MuiOutlinedInput: { styleOverrides: { root: { borderRadius: 4 } } },
      MuiDrawer: { styleOverrides: { paper: { borderRadius: "4px 0 0 4px" } } },
      MuiTableContainer: { styleOverrides: { root: { borderRadius: 4 } } },
      MuiAlert: { styleOverrides: { root: { borderRadius: 4 } } },
    },
  });
};
