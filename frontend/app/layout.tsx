import type { Metadata } from "next";
import Link from "next/link";
import { DeploymentControls } from "@/components/deployment-controls";

import "./globals.css";


export const metadata: Metadata = {
  title: "AegisPR — Evidence-backed pull request verification",
  description: "Autonomous differential verification powered by NVIDIA Nemotron on Nebius Token Factory.",
  icons: { icon: "/brand/aegispr-logo.jpg", apple: "/brand/aegispr-logo.jpg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <a href="#main-content" className="skip-link">Skip to content</a>
        <header className="site-header">
          <Link className="brand" href="/" aria-label="AegisPR home">
            <span className="brand-shield" aria-hidden="true" />
            <span>Aegis<span className="brand-light">PR</span></span>
          </Link>
          <nav aria-label="Primary navigation">
            <a href="/#how-it-works">How it works</a>
            <a href="/#features">Features</a>
            <a href="/#architecture">Architecture</a>
            <a href="https://github.com/Hari-Aditya-003/AegisPR" rel="noreferrer">GitHub</a>
          </nav>
          <a className="header-action" href="/#verify-title">Start verification <span aria-hidden="true">↗</span></a>
        </header>
        <DeploymentControls />
        <main id="main-content">{children}</main>
        <footer>
          <span>AegisPR</span>
          <p>Don&apos;t trust a PR. Prove it.</p>
          <p>Built for the Nebius × NVIDIA Global AI Hackathon.</p>
        </footer>
      </body>
    </html>
  );
}
