import type { Metadata } from "next";
import { Masthead, SiteFooter } from "./components/Chrome";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "CS Magazine · City Sight",
    template: "%s · City Sight",
  },
  description: "香港城市變化雜誌 — 用一張圖、一條數，講清楚城市點變。",
  metadataBase: new URL("https://www.citysight.net"),
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-HK">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Noto+Sans+TC:wght@400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="site-shell">
          <Masthead />
          {children}
        </div>
        <SiteFooter />
      </body>
    </html>
  );
}
