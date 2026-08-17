import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Academic AI Study Tutor",
  description: "AI Powered Interactive Education & Knowledge Retrieval",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#fdfbf7] text-slate-800 flex h-screen overflow-hidden antialiased">
        <main className="flex-1 overflow-y-auto bg-[#fdfbf7]">
          {children}
        </main>
      </body>
    </html>
  );
}