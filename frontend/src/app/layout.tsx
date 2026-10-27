import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReviewLens AI — Cross-Platform E-Commerce Sentiment & Authenticity Radar",
  description:
    "Cross-platform sentiment analysis and review authenticity engine for Amazon.in and Flipkart with Hinglish normalization, ABSA radar, and anti-bot trust scoring.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-950 text-slate-100 selection:bg-emerald-500/30 selection:text-emerald-200">
        {children}
      </body>
    </html>
  );
}
