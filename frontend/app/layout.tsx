import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";


export const metadata: Metadata = {
  title: "AegisPR — Evidence-backed pull request verification",
  description: "Autonomous differential verification powered by NVIDIA Nemotron on Nebius Token Factory.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <Link className="brand" href="/" aria-label="AegisPR home">
            <span className="brand-shield">A</span>
            <span>AegisPR</span>
          </Link>
          <nav aria-label="Primary navigation">
            <a href="/#how-it-works">How it works</a>
            <a href="/#features">Features</a>
            <a href="/#architecture">Architecture</a>
            <a href="https://github.com/Hari-Aditya-003/AegisPR" rel="noreferrer">GitHub</a>
          </nav>
        </header>
        <main>{children}</main>
        <footer>
          <span>AegisPR</span>
          <p>Don&apos;t trust a PR. Prove it.</p>
          <p>Built for the Nebius × NVIDIA Global AI Hackathon.</p>
        </footer>
      </body>
    </html>
  );
}

