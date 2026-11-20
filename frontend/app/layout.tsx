import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinSight",
  description: "A clearer view of your finances",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
