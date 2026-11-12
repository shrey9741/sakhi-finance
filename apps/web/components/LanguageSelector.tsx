"use client";

import { LOCALES, LOCALE_NAMES } from "@/lib/i18n/locales";
import { useI18n } from "@/lib/i18n/provider";

export function LanguageSelector() {
  const { locale, setLocale, t } = useI18n();

  return (
    <div role="group" aria-label={t("language.label")} className="flex flex-wrap gap-2">
      {LOCALES.map((code) => {
        const selected = code === locale;
        return (
          <button
            key={code}
            type="button"
            lang={code}
            aria-pressed={selected}
            onClick={() => setLocale(code)}
            className={`h-11 min-w-20 rounded-full border px-4 text-base font-medium transition-colors ${
              selected
                ? "border-foreground bg-foreground text-background"
                : "border-foreground/30 hover:bg-foreground/10"
            }`}
          >
            {LOCALE_NAMES[code]}
          </button>
        );
      })}
    </div>
  );
}
