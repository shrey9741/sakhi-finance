"use client";

import type { ReactNode } from "react";

import { LanguageSelector } from "@/components/LanguageSelector";
import { useI18n } from "@/lib/i18n/provider";

export function AppShell({ children }: { children?: ReactNode }) {
  const { t } = useI18n();

  return (
    <div className="mx-auto flex w-full max-w-md flex-1 flex-col gap-8 px-5 py-6">
      <header className="flex flex-col gap-4">
        <span className="text-2xl font-bold">{t("app.name")}</span>
        <LanguageSelector />
      </header>
      <main className="flex flex-1 flex-col gap-6">{children}</main>
    </div>
  );
}
