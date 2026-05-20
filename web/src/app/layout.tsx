import type { Metadata } from "next";
import { Cinzel, Outfit } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/Nav";

const outfit = Outfit({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-outfit",
});

const cinzel = Cinzel({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  variable: "--font-cinzel",
});

export const metadata: Metadata = {
  title: "Kitab — Vedic Astrology",
  description: "Live Vedic charts, Prashna readings, and Today's Sky.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${outfit.variable} ${cinzel.variable} antialiased`}>
      <body>
        <div className="background-effects">
          <div className="orb orb-1" />
          <div className="orb orb-2" />
          <div className="orb orb-3" />
        </div>
        <main className="relative z-10 mx-auto w-full max-w-5xl px-4 py-8 md:px-6 md:py-12">
          <Nav />
          {children}
        </main>
      </body>
    </html>
  );
}
