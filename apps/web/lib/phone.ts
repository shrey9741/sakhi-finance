// Mirrors the backend rule: Indian mobile, optional +91 / 91 / 0 prefix.
// Returns the 10-digit number, or null when it is not valid.
export function normalizeIndianMobile(raw: string): string | null {
  const cleaned = raw.replace(/[\s\-()]/g, "");
  const match = /^(?:\+91|91|0)?([6-9]\d{9})$/.exec(cleaned);
  return match ? match[1] : null;
}
