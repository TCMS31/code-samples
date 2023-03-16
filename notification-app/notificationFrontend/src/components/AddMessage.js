import {
  Alert,
  Box,
  Button,
  CircularProgress,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import React, { useEffect, useState } from "react";

import { createMessage, fetchCategories } from "../api/client";

const AddMessage = () => {
  const [message, setMessage] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState([]);
  const [status, setStatus] = useState({ kind: "idle" });
  const [loadingCategories, setLoadingCategories] = useState(true);

  useEffect(() => {
    let active = true;
    fetchCategories()
      .then((rows) => {
        if (!active) return;
        setCategories(rows);
        if (rows.length > 0) setCategory(rows[0].id);
      })
      .catch(() =>
        active &&
        setStatus({
          kind: "error",
          text: "Could not load categories. Is the API running?",
        })
      )
      .finally(() => active && setLoadingCategories(false));
    return () => {
      active = false;
    };
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    if (message.trim().length === 0) {
      setStatus({ kind: "error", text: "Message cannot be empty." });
      return;
    }
    setStatus({ kind: "submitting" });
    try {
      await createMessage({ message: message.trim(), category });
      setStatus({ kind: "success", text: "Message sent to all subscribers." });
      setMessage("");
    } catch (error) {
      setStatus({
        kind: "error",
        text: error.response?.data
          ? JSON.stringify(error.response.data)
          : "Could not reach the API.",
      });
    }
  };

  return (
    <Box sx={{ maxWidth: 680, mx: "auto", px: 2, py: 4 }}>
      <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
        <Typography variant="h5" component="h1" gutterBottom>
          Send a notification
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          The message fans out to every user subscribed to the chosen category,
          on each channel they have enabled.
        </Typography>

        <Stack component="form" spacing={2.5} onSubmit={submit} noValidate>
          <TextField
            id="messageInput"
            label="Message"
            placeholder="Write your message here"
            multiline
            minRows={3}
            fullWidth
            required
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />

          <TextField
            id="categorySelection"
            label="Category"
            select
            fullWidth
            required
            value={category}
            disabled={loadingCategories || categories.length === 0}
            helperText={
              loadingCategories
                ? "Loading categories..."
                : categories.length === 0
                ? "No categories found. Run: python manage.py seed_demo"
                : " "
            }
            // Previously `onChange={(e) => e.target.value}` - the value was
            // computed and thrown away, so the category never changed.
            onChange={(e) => setCategory(e.target.value)}
          >
            {categories.map((c) => (
              <MenuItem key={c.id} value={c.id}>
                {c.name}
              </MenuItem>
            ))}
          </TextField>

          {status.kind === "error" && (
            <Alert severity="error" onClose={() => setStatus({ kind: "idle" })}>
              {status.text}
            </Alert>
          )}
          {status.kind === "success" && (
            <Alert
              severity="success"
              onClose={() => setStatus({ kind: "idle" })}
            >
              {status.text}
            </Alert>
          )}

          <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
            <Button
              type="submit"
              variant="contained"
              disabled={status.kind === "submitting" || loadingCategories}
              startIcon={
                status.kind === "submitting" ? (
                  <CircularProgress size={16} color="inherit" />
                ) : null
              }
            >
              {status.kind === "submitting" ? "Sending" : "Add message"}
            </Button>
          </Box>
        </Stack>
      </Paper>
    </Box>
  );
};

export default AddMessage;
