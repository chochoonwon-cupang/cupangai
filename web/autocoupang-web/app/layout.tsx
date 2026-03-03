import "./globals.css";
import type { Metadata } from "next";
import { LayoutSwitch } from "@/components/layout/LayoutSwitch";

export const metadata: Metadata = {
  title: "autocoupang - 쿠팡파트너스 자동포스팅",
  description: "70원부터, 워커가 자동 발행",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>
        <LayoutSwitch>{children}</LayoutSwitch>
      </body>
    </html>
  );
}
