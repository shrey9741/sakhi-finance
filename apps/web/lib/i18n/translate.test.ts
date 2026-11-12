import { describe, expect, it } from "vitest";

import { LOCALES, isLocale } from "./locales";
import { messages, type MessageKey } from "./messages";
import { translate } from "./translate";

const keys = (locale: (typeof LOCALES)[number]) => Object.keys(messages[locale]).sort();
const placeholders = (text: string) =>
  [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("translate", () => {
  it("returns the message for each locale", () => {
    expect(translate("en-IN", "login.title")).toBe("Log in");
    expect(translate("hi-IN", "login.title")).not.toBe("Log in");
    expect(translate("or-IN", "login.title")).not.toBe("Log in");
  });

  it("interpolates params", () => {
    expect(translate("en-IN", "login.codeSentTo", { phone: "+919876543210" })).toBe(
      "Code sent to +919876543210",
    );
  });

  it("leaves unknown placeholders untouched", () => {
    expect(translate("en-IN", "login.resendIn", {})).toContain("{seconds}");
  });

  it("falls back to the key when a message is missing", () => {
    expect(translate("en-IN", "does.not.exist" as MessageKey)).toBe("does.not.exist");
  });
});

describe("catalogs", () => {
  it("has exactly the same keys in every locale", () => {
    const english = keys("en-IN");
    for (const locale of LOCALES) expect(keys(locale)).toEqual(english);
  });

  it("uses the same placeholders in every locale", () => {
    for (const key of Object.keys(messages["en-IN"]) as MessageKey[]) {
      for (const locale of LOCALES) {
        expect(placeholders(messages[locale][key])).toEqual(placeholders(messages["en-IN"][key]));
      }
    }
  });

  it("has no empty messages", () => {
    for (const locale of LOCALES) {
      for (const text of Object.values(messages[locale])) expect(text.trim()).not.toBe("");
    }
  });
});

describe("isLocale", () => {
  it("accepts only supported locales", () => {
    expect(isLocale("or-IN")).toBe(true);
    expect(isLocale("fr-FR")).toBe(false);
    expect(isLocale(undefined)).toBe(false);
  });
});
