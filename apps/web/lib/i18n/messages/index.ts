import type { Locale } from "../locales";
import { enIN, type MessageKey } from "./en-IN";
import { hiIN } from "./hi-IN";
import { orIN } from "./or-IN";

export type { MessageKey };

export const messages: Record<Locale, Record<MessageKey, string>> = {
  "en-IN": enIN,
  "hi-IN": hiIN,
  "or-IN": orIN,
};
