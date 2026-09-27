import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ProofFix — BUG COURT",
  description:
    "Scientific Debugging & Adversarial Repair Verification — IBM Bob Hackathon Demo",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
