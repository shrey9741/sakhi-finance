import { describe, expect, it } from "vitest";

import { normalizeIndianMobile } from "./phone";

describe("normalizeIndianMobile", () => {
  it("accepts common Indian mobile formats", () => {
    for (const input of ["9876543210", "+91 98765 43210", "09876543210", "919876543210", "98765-43210"]) {
      expect(normalizeIndianMobile(input)).toBe("9876543210");
    }
  });

  it("rejects invalid numbers", () => {
    for (const input of ["", "12345", "5876543210", "98765432101", "abcdefghij", "+1 9876543210"]) {
      expect(normalizeIndianMobile(input)).toBeNull();
    }
  });
});
