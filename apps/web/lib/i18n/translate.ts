import type { Locale } from "./locales";
import { messages, type MessageKey } from "./messages";

type Params = Record<string, string | number>;

// Falls back to English, then to the key itself, so a missing string never crashes a page.
export function translate(locale: Locale, key: MessageKey, params?: Params): string {
  const template = messages[locale][key] ?? messages["en-IN"][key] ?? key;
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in params ? String(params[name]) : match,
  );
}
