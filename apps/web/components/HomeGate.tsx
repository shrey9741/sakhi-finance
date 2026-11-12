"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { getMe, logout, type UserMe } from "@/lib/auth";
import { authErrorKey } from "@/lib/auth-errors";
import type { MessageKey } from "@/lib/i18n/messages";
import { useI18n } from "@/lib/i18n/provider";

export function HomeGate() {
  const { t } = useI18n();
  const router = useRouter();
  const [user, setUser] = useState<UserMe | null>(null);
  const [errorKey, setErrorKey] = useState<MessageKey | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          router.replace("/login");
        } else {
          setErrorKey(authErrorKey(error, "phone"));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function onLogout() {
    try {
      await logout();
    } catch {
      // Even if the request fails, send the user to the login page.
    }
    router.replace("/login");
  }

  if (errorKey) {
    return (
      <p role="alert" className="text-base font-medium text-red-600 dark:text-red-400">
        {t(errorKey)}
      </p>
    );
  }

  if (user === null) return <p className="text-base">{t("common.loading")}</p>;

  return (
    <div className="flex flex-col gap-6">
      <p className="text-xl font-semibold">{t("home.welcome")}</p>
      <button
        type="button"
        onClick={() => void onLogout()}
        className="h-12 w-full rounded-full border border-foreground/30 text-base font-medium"
      >
        {t("home.logout")}
      </button>
    </div>
  );
}
