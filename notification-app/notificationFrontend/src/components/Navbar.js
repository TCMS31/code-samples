import { AppBar, Box, Button, Toolbar, Typography } from "@mui/material";
import React from "react";
import { Link, useLocation } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Home" },
  { to: "/logs", label: "Logs" },
];

const Navbar = () => {
  const { pathname } = useLocation();

  return (
    <AppBar position="static" elevation={0} sx={{ bgcolor: "#2f3438" }}>
      <Toolbar sx={{ gap: 1 }}>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Notification API
        </Typography>
        <Box sx={{ display: "flex", gap: 0.5 }}>
          {LINKS.map(({ to, label }) => {
            const active = pathname === to;
            return (
              <Button
                key={to}
                component={Link}
                to={to}
                aria-current={active ? "page" : undefined}
                sx={{
                  color: "common.white",
                  fontWeight: active ? 700 : 400,
                  borderBottom: 2,
                  borderRadius: 0,
                  borderColor: active ? "common.white" : "transparent",
                  "&:hover": { bgcolor: "rgba(255,255,255,0.08)" },
                }}
              >
                {label}
              </Button>
            );
          })}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
