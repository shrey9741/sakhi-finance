import { ApiError } from "./api";
import type { MessageKey } from "./i18n/messages";

export type AuthStep = "phone" | "code";

// Branch on status, never on the English message text.
export function authErrorKey(error: unknown, step: AuthStep): MessageKey {
  if (!(error instanceof ApiError)) return "error.generic";
  switch (error.status) {
    case 0:
      return "error.network";
    case 401:
      return "error.invalidCode";
    case 422:
      return step === "phone" ? "error.invalidPhone" : "error.invalidCode";
    case 429:
      return "error.tooMany";
    case 500:
    case 502:
    case 503:
    case 504:
      return "error.unavailable";
    default:
      return "error.generic";
  }
}
