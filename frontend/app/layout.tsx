import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "DONGGUK AI", description: "동국대학교 학생 AI Assistant" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="ko"><body>{children}</body></html>; }
