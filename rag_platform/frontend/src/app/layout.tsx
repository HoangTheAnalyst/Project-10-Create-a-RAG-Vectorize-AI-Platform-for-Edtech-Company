import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Study Platform",
  description: "AI Powered Interactive Education & Knowledge Retrieval",
  icons: {
    icon: "/LogoHTA.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#fdfbf7] text-slate-800 flex h-screen overflow-hidden antialiased">
        <main className="flex-1 h-full w-full overflow-hidden bg-[#fdfbf7]">
          {children}
        </main>
      </body>
    </html>
  );
}