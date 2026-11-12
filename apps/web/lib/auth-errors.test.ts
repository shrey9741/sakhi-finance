import { describe, expect, it } from "vitest";

import { ApiError } from "./api";
import { authErrorKey } from "./auth-errors";

describe("authErrorKey", () => {
  it("maps network and server failures", () => {
    expect(authErrorKey(new ApiError(0, "x"), "phone")).toBe("error.network");
    expect(authErrorKey(new ApiError(503, "x"), "phone")).toBe("error.unavailable");
    expect(authErrorKey(new ApiError(500, "x"), "code")).toBe("error.unavailable");
  });

  it("treats 422 according to the step", () => {
    expect(authErrorKey(new ApiError(422, "x"), "phone")).toBe("error.invalidPhone");
    expect(authErrorKey(new ApiError(422, "x"), "code")).toBe("error.invalidCode");
  });

  it("maps 401 and 429", () => {
    expect(authErrorKey(new ApiError(401, "x"), "code")).toBe("error.invalidCode");
    expect(authErrorKey(new ApiError(429, "x", 30), "phone")).toBe("error.tooMany");
  });

  it("falls back to a generic message", () => {
    expect(authErrorKey(new ApiError(418, "x"), "phone")).toBe("error.generic");
    expect(authErrorKey(new Error("boom"), "phone")).toBe("error.generic");
  });
});
