"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "@/lib/api";
import { requestOtp, verifyOtp } from "@/lib/auth";
import { authErrorKey, type AuthStep } from "@/lib/auth-errors";
import type { MessageKey } from "@/lib/i18n/messages";
import { useI18n } from "@/lib/i18n/provider";
import { normalizeIndianMobile } from "@/lib/phone";

const RESEND_SECONDS = 60;

const inputClass =
  "h-12 w-full rounded-lg border border-foreground/30 bg-transparent px-4 text-lg";
const primaryButton =
  "h-12 w-full rounded-full bg-foreground text-base font-medium text-background disabled:opacity-50";
const secondaryButton =
  "h-12 w-full rounded-full border border-foreground/30 text-base font-medium disabled:opacity-50";

export function LoginForm() {
  const { t } = useI18n();
  const router = useRouter();
  const [step, setStep] = useState<AuthStep>("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [errorKey, setErrorKey] = useState<MessageKey | null>(null);
  const [busy, setBusy] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);

  // Counts down one second at a time; each tick schedules the next.
  useEffect(() => {
    if (secondsLeft <= 0) return;
    const id = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(id);
  }, [secondsLeft]);

  async function sendCode(normalized: string) {
    setBusy(true);
    setErrorKey(null);
    try {
      await requestOtp(normalized);
      setPhone(normalized);
      setCode("");
      setStep("code");
      setSecondsLeft(RESEND_SECONDS);
    } catch (error) {
      setErrorKey(authErrorKey(error, "phone"));
      if (error instanceof ApiError && error.status === 429 && error.retryAfter) {
        setSecondsLeft(error.retryAfter);
      }
    } finally {
      setBusy(false);
    }
  }

  function onPhoneSubmit(event: FormEvent) {
    event.preventDefault();
    const normalized = normalizeIndianMobile(phone);
    if (normalized === null) {
      setErrorKey("error.invalidPhone");
      return;
    }
    void sendCode(normalized);
  }

  async function onCodeSubmit(event: FormEvent) {
    event.preventDefault();
    if (!/^\d{6}$/.test(code)) {
      setErrorKey("error.invalidCode");
      return;
    }
    setBusy(true);
    setErrorKey(null);
    try {
      await verifyOtp(phone, code);
      router.replace("/");
    } catch (error) {
      setErrorKey(authErrorKey(error, "code"));
      setCode("");
      setBusy(false);
    }
  }

  function changeNumber() {
    setStep("phone");
    setCode("");
    setErrorKey(null);
  }

  const errorMessage = errorKey ? (
    <p role="alert" className="text-base font-medium text-red-600 dark:text-red-400">
      {t(errorKey)}
    </p>
  ) : null;

  if (step === "phone") {
    return (
      <form onSubmit={onPhoneSubmit} className="flex flex-col gap-4" noValidate>
        <h1 className="text-xl font-semibold">{t("login.title")}</h1>
        <label htmlFor="phone" className="text-base font-medium">
          {t("login.phoneLabel")}
        </label>
        <div className="flex items-center gap-2">
          <span className="text-lg" aria-hidden="true">
            +91
          </span>
          <input
            id="phone"
            name="phone"
            type="tel"
            inputMode="numeric"
            autoComplete="tel-national"
            maxLength={16}
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className={inputClass}
          />
        </div>
        {errorMessage}
        <button type="submit" disabled={busy} className={primaryButton}>
          {t("login.sendCode")}
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={onCodeSubmit} className="flex flex-col gap-4" noValidate>
      <h1 className="text-xl font-semibold">{t("login.title")}</h1>
      <p className="text-base">{t("login.codeSentTo", { phone: `+91 ${phone}` })}</p>
      <label htmlFor="code" className="text-base font-medium">
        {t("login.codeLabel")}
      </label>
      <input
        id="code"
        name="code"
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        className={`${inputClass} tracking-widest`}
      />
      {errorMessage}
      <button type="submit" disabled={busy} className={primaryButton}>
        {t("login.verify")}
      </button>
      {secondsLeft > 0 ? (
        <p className="text-center text-base">{t("login.resendIn", { seconds: secondsLeft })}</p>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={() => void sendCode(phone)}
          className={secondaryButton}
        >
          {t("login.resend")}
        </button>
      )}
      <button type="button" onClick={changeNumber} className={secondaryButton}>
        {t("login.changeNumber")}
      </button>
    </form>
  );
}
