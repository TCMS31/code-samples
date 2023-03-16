import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "./App";
import Logs from "./components/Logs";
import * as api from "./api/client";

jest.mock("./api/client");

const renderAt = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>);

// This MUI version renders a select as a div with role="button" holding the
// chosen option's label, so there is no input value to query.
const categorySelect = () => document.getElementById("categorySelection");
const waitForCategory = (label) =>
  waitFor(() => expect(categorySelect()).toHaveTextContent(label));

beforeEach(() => {
  jest.resetAllMocks();
});

describe("AddMessage", () => {
  test("loads categories from the API and selects the first", async () => {
    api.fetchCategories.mockResolvedValue([
      { id: 7, name: "Finance" },
      { id: 9, name: "Sports" },
    ]);

    renderAt(<App />);

    await waitForCategory("Finance");
  });

  test("submits the typed message with the selected category id", async () => {
    // Ids deliberately are not 1/2/3: the old form hardcoded those.
    api.fetchCategories.mockResolvedValue([{ id: 42, name: "Sports" }]);
    api.createMessage.mockResolvedValue({ id: 1 });

    renderAt(<App />);
    await waitForCategory("Sports");

    await userEvent.type(screen.getByLabelText(/message/i), "Match tonight");
    await userEvent.click(screen.getByRole("button", { name: /add message/i }));

    await waitFor(() =>
      expect(api.createMessage).toHaveBeenCalledWith({
        message: "Match tonight",
        category: 42,
      })
    );
  });

  test("refuses to submit an empty message", async () => {
    api.fetchCategories.mockResolvedValue([{ id: 1, name: "Sports" }]);

    renderAt(<App />);
    await waitForCategory("Sports");

    await userEvent.click(screen.getByRole("button", { name: /add message/i }));

    expect(await screen.findByText(/cannot be empty/i)).toBeInTheDocument();
    expect(api.createMessage).not.toHaveBeenCalled();
  });

  test("shows a confirmation and clears the field after a successful send", async () => {
    api.fetchCategories.mockResolvedValue([{ id: 1, name: "Sports" }]);
    api.createMessage.mockResolvedValue({ id: 1 });

    renderAt(<App />);
    await waitForCategory("Sports");

    const field = screen.getByLabelText(/message/i);
    await userEvent.type(field, "Hello");
    await userEvent.click(screen.getByRole("button", { name: /add message/i }));

    expect(await screen.findByText(/sent to all subscribers/i)).toBeInTheDocument();
    await waitFor(() => expect(field).toHaveValue(""));
  });

  test("surfaces an API failure instead of failing silently", async () => {
    api.fetchCategories.mockResolvedValue([{ id: 1, name: "Sports" }]);
    api.createMessage.mockRejectedValue(new Error("network down"));

    renderAt(<App />);
    await waitForCategory("Sports");

    await userEvent.type(screen.getByLabelText(/message/i), "Hello");
    await userEvent.click(screen.getByRole("button", { name: /add message/i }));

    expect(await screen.findByText(/could not reach the api/i)).toBeInTheDocument();
  });

  test("tells the user how to seed when no categories exist", async () => {
    api.fetchCategories.mockResolvedValue([]);

    renderAt(<App />);

    expect(await screen.findByText(/seed_demo/)).toBeInTheDocument();
  });
});

describe("Logs", () => {
  test("renders each returned log line", async () => {
    api.fetchLogs.mockResolvedValue([
      { log: "2024-01-01 -- Test user 1 -- E-Mail -- Sports -- Match tonight" },
      { log: "2024-01-01 -- Test user 2 -- SMS -- Sports -- Match tonight" },
    ]);

    renderAt(<Logs />);

    expect(await screen.findByText(/Test user 1/)).toBeInTheDocument();
    expect(screen.getByText(/Test user 2/)).toBeInTheDocument();
    expect(screen.getByText(/2 entries/)).toBeInTheDocument();
  });

  test("renders duplicate log lines without collapsing them", async () => {
    // Regression: the log text was used as the React key, so identical lines
    // (the same message fanned out to several users) collided.
    const line = { log: "same line" };
    api.fetchLogs.mockResolvedValue([line, line, line]);

    renderAt(<Logs />);

    expect(await screen.findAllByText("same line")).toHaveLength(3);
  });

  test("shows an empty state rather than a blank page", async () => {
    api.fetchLogs.mockResolvedValue([]);

    renderAt(<Logs />);

    expect(await screen.findByText(/no notifications yet/i)).toBeInTheDocument();
  });

  test("shows a retry affordance when the API is unreachable", async () => {
    api.fetchLogs.mockRejectedValue(new Error("offline"));

    renderAt(<Logs />);

    expect(await screen.findByText(/could not load logs/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });
});
