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
 * Fetch the newest page of rendered log lines.
 *
 * The API is paginated: `rows` is this page and `total` is the server's
 * `count`, which is larger than `rows.length` once there are more entries than
 * PAGE_SIZE. A bare array (older unpaginated API) counts as one full page.
 */
export async function fetchLogs() {
  const { data } = await client.get("logs/string");
  if (Array.isArray(data)) return { rows: data, total: data.length };
  const rows = data.results ?? [];
  return { rows, total: data.count ?? rows.length };
}

/** Fetch the selectable message categories. */
export async function fetchCategories() {
  const { data } = await client.get("categories/");
  return Array.isArray(data) ? data : data.results ?? [];
}

export default client;
