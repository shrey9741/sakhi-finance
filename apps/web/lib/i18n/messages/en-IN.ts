export const enIN = {
  "app.name": "Sakhi Finance",
  "language.label": "Language",
  "login.title": "Log in",
  "login.phoneLabel": "Mobile number",
  "login.sendCode": "Send code",
  "login.codeLabel": "6-digit code",
  "login.codeSentTo": "Code sent to {phone}",
  "login.resendIn": "Resend code in {seconds} seconds",
  "login.verify": "Verify",
  "error.invalidPhone": "Please enter a valid mobile number",
  "error.invalidCode": "The code is wrong or has expired",
  "error.tooMany": "Too many attempts. Please try again later",
  "error.network": "Network problem. Please try again",
  "error.unavailable": "The service is not available right now. Please try later",
} as const;

export type MessageKey = keyof typeof enIN;
