import { createTheme } from "@mui/material/styles";

/** One place for the colours and shape used across both screens. */
const theme = createTheme({
  palette: {
    primary: { main: "#2f6f4e" },
    background: { default: "#f7f8f7" },
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    h5: { fontWeight: 600 },
  },
  components: {
    MuiButton: { defaultProps: { disableElevation: true } },
  },
});

export default theme;
