export const LOCALES = ["or-IN", "hi-IN", "en-IN"] as const;
export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "or-IN";

// Each language is shown in its own script so people can find it without reading English.
export const LOCALE_NAMES: Record<Locale, string> = {
  "or-IN": "ଓଡ଼ିଆ",
  "hi-IN": "हिन्दी",
  "en-IN": "English",
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}