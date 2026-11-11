import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest } from "./api";

function mockFetch(result: Response | Error) {
  const fn = vi.fn(async () => {
    if (result instanceof Error) throw result;
    return result;
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("apiRequest", () => {
  it("returns parsed JSON on success", async () => {
    mockFetch(Response.json({ status: "ok" }));
    expect(await apiRequest("/health/live")).toEqual({ status: "ok" });
  });

  it("sends a JSON body with a content type", async () => {
    const fn = mockFetch(Response.json({ status: "ok" }));
    await apiRequest("/auth/otp/request", { method: "POST", body: { phone_number: "9876543210" } });
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/auth/otp/request");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ phone_number: "9876543210" }));
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
  });

  it("returns undefined for 204", async () => {
    mockFetch(new Response(null, { status: 204 }));
    expect(await apiRequest("/auth/logout", { method: "POST" })).toBeUndefined();
  });

  it("maps string detail and Retry-After into ApiError", async () => {
    mockFetch(
      Response.json(
        { detail: "Too many requests. Please try again later." },
        { status: 429, headers: { "Retry-After": "42" } },
      ),
    );
    const error = await apiRequest("/auth/otp/request").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(429);
    expect((error as ApiError).retryAfter).toBe(42);
    expect((error as ApiError).message).toContain("Too many requests");
  });

  it("uses the first message from a validation error array", async () => {
    mockFetch(Response.json({ detail: [{ msg: "String should match pattern" }] }, { status: 422 }));
    const error = await apiRequest("/auth/otp/verify").catch((e: unknown) => e);
    expect((error as ApiError).status).toBe(422);
    expect((error as ApiError).message).toBe("String should match pattern");
    expect((error as ApiError).retryAfter).toBeNull();
  });

  it("wraps network failures as status 0", async () => {
    mockFetch(new TypeError("fetch failed"));
    const error = await apiRequest("/users/me").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
  });

  it("falls back to the status text when the body is not JSON", async () => {
    mockFetch(new Response("oops", { status: 500, statusText: "Server Error" }));
    const error = await apiRequest("/users/me").catch((e: unknown) => e);
    expect((error as ApiError).status).toBe(500);
    expect((error as ApiError).message).toBe("Server Error");
  });
});
