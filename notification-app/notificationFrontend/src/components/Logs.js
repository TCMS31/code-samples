import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import React, { useCallback, useEffect, useState } from "react";

import { fetchLogs } from "../api/client";
import Navbar from "./Navbar";

const Logs = () => {
  const [logs, setLogs] = useState([]);
  const [state, setState] = useState("loading");

  const load = useCallback(() => {
    setState("loading");
    fetchLogs()
      .then((rows) => {
        setLogs(rows);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, []);

  useEffect(load, [load]);

  return (
    <>
      <Navbar />
      <Box sx={{ maxWidth: 960, mx: "auto", px: 2, py: 4 }}>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h5" component="h1">
              Notification log
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {state === "ready"
                ? `${logs.length} ${
                    logs.length === 1 ? "entry" : "entries"
                  }, newest first`
                : " "}
            </Typography>
          </Box>
          <Button onClick={load} disabled={state === "loading"}>
            Refresh
          </Button>
        </Stack>

        {state === "loading" && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress />
          </Box>
        )}

        {state === "error" && (
          <Alert severity="error" action={<Button onClick={load}>Retry</Button>}>
            Could not load logs. Check that the API is running.
          </Alert>
        )}

        {state === "ready" && logs.length === 0 && (
          <Paper
            variant="outlined"
            sx={{ p: 4, textAlign: "center", borderRadius: 2 }}
          >
            <Typography variant="subtitle1" gutterBottom>
              No notifications yet
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Seed the demo data with{" "}
              <code>python manage.py seed_demo</code>, then send a message from
              the Home page.
            </Typography>
          </Paper>
        )}

        {state === "ready" && logs.length > 0 && (
          <Stack spacing={1}>
            {logs.map(({ log }, index) => (
              // The log text is not unique (the same message fans out to many
              // users), so it cannot be the key on its own.
              <Paper
                key={`${index}-${log}`}
                variant="outlined"
                sx={{
                  px: 2,
                  py: 1.25,
                  borderRadius: 1.5,
                  fontFamily: "monospace",
                  fontSize: 13,
                  wordBreak: "break-word",
                  transition: "background-color 120ms",
                  "&:hover": { backgroundColor: "action.hover" },
                }}
              >
                {log}
              </Paper>
            ))}
          </Stack>
        )}
      </Box>
    </>
  );
};

export default Logs;
