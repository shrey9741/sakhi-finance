import type { Metadata } from "next";
import { Geist, Geist_Mono, Noto_Sans_Devanagari, Noto_Sans_Oriya } from "next/font/google";
import "./globals.css";
import { LanguageProvider } from "@/lib/i18n/provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const notoDevanagari = Noto_Sans_Devanagari({
  variable: "--font-devanagari",
  subsets: ["devanagari"],
  weight: ["400", "700"],
});

const notoOriya = Noto_Sans_Oriya({
  variable: "--font-oriya",
  subsets: ["oriya"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "Sakhi Finance",
  description: "Simple financial guidance in your language",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${notoDevanagari.variable} ${notoOriya.variable} h-full antialiased`}
    >
      <body
        className="min-h-full flex flex-col"
        style={{
          fontFamily:
            "var(--font-geist-sans), var(--font-oriya), var(--font-devanagari), system-ui, sans-serif",
        }}
      >
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
