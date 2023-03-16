import axios from "axios";

// REACT_APP_API_URL was read directly in each component with no fallback. When
// it was unset - which it always was, since no .env was committed - the request
// URL became the literal string "undefinedadd/" and every call failed.
const DEFAULT_BASE_URL = "http://localhost:8000/";

export const baseURL = (
  process.env.REACT_APP_API_URL || DEFAULT_BASE_URL
).replace(/\/*$/, "/");

const client = axios.create({ baseURL, timeout: 10000 });

/** Post a new message. Returns the created message. */
export async function createMessage({ message, category }) {
  const { data } = await client.post("add/", { message, category });
  return data;
}

/**
 * Fetch rendered log lines.
 *
 * The API is paginated, so the rows live under `results`. Older unpaginated
 * responses returned a bare array; both shapes are handled.
 */
export async function fetchLogs() {
  const { data } = await client.get("logs/string");
  return Array.isArray(data) ? data : data.results ?? [];
}

/** Fetch the selectable message categories. */
export async function fetchCategories() {
  const { data } = await client.get("categories/");
  return Array.isArray(data) ? data : data.results ?? [];
}

export default client;
