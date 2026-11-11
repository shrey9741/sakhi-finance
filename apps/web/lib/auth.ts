import { apiRequest } from "./api";

export type UserMe = {
  id: string;
  status: string;
  preferred_language: string | null;
  onboarding_completed: boolean;
};

export const requestOtp = (phoneNumber: string) =>
  apiRequest<{ status: string }>("/auth/otp/request", {
    method: "POST",
    body: { phone_number: phoneNumber },
  });

export const verifyOtp = (phoneNumber: string, otp: string) =>
  apiRequest<{ status: string }>("/auth/otp/verify", {
    method: "POST",
    body: { phone_number: phoneNumber, otp },
  });

export const logout = () => apiRequest<void>("/auth/logout", { method: "POST" });

export const getMe = () => apiRequest<UserMe>("/users/me");
