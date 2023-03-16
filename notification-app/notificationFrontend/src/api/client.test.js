import { baseURL, fetchLogs } from "./client";
import client from "./client";

describe("API client", () => {
  test("falls back to a usable base URL when REACT_APP_API_URL is unset", () => {
    // Regression: the components interpolated an undefined env var straight
    // into the path, producing requests to "undefinedadd/".
    expect(baseURL).not.toContain("undefined");
    expect(baseURL).toMatch(/^https?:\/\/.+\/$/);
  });

  test("unwraps the paginated envelope", async () => {
    jest
      .spyOn(client, "get")
      .mockResolvedValue({ data: { count: 1, results: [{ log: "x" }] } });

    await expect(fetchLogs()).resolves.toEqual({
      rows: [{ log: "x" }],
      total: 1,
    });
  });

  test("still accepts a bare array response", async () => {
    jest.spyOn(client, "get").mockResolvedValue({ data: [{ log: "y" }] });

    await expect(fetchLogs()).resolves.toEqual({
      rows: [{ log: "y" }],
      total: 1,
    });
  });

  test("reports the server total, not the page length", async () => {
    jest.spyOn(client, "get").mockResolvedValue({
      data: { count: 120, results: [{ log: "a" }, { log: "b" }] },
    });

    await expect(fetchLogs()).resolves.toEqual({
      rows: [{ log: "a" }, { log: "b" }],
      total: 120,
    });
  });

  test("returns an empty list when the envelope has no results", async () => {
    jest.spyOn(client, "get").mockResolvedValue({ data: { count: 0 } });

    await expect(fetchLogs()).resolves.toEqual({ rows: [], total: 0 });
  });
});
