"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Calendar,
  ListTodo,
  Wallet,
  Settings,
  Menu,
  LogOut,
  X,
  HelpCircle,
  Key,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/supabaseClient";

const navItems = [
  { href: "/dashboard", label: "대시보드", icon: LayoutDashboard },
  { href: "/plan", label: "발행계획", icon: Calendar },
  { href: "/tasks", label: "작업내역", icon: ListTodo },
  { href: "/dashboard", label: "충전/월렛", icon: Wallet },
  { href: "/faq", label: "자주묻는질문", icon: HelpCircle },
  { href: "/api-keys", label: "API 키 설정", icon: Key },
  { href: "/admin", label: "관리자", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [balance, setBalance] = React.useState(0);
  const [email, setEmail] = React.useState("");

  React.useEffect(() => {
    const init = async () => {
      const { data } = await supabase.auth.getUser();
      if (data.user) {
        setEmail(data.user.email ?? "");
        const { data: bal } = await supabase.rpc("get_wallet_balance");
        setBalance(Number(bal ?? 0));
      }
    };
    init();
  }, []);

  const onLogout = async () => {
    const { supabase } = await import("@/lib/supabaseClient");
    await supabase.auth.signOut();
    router.push("/login");
  };

  const isActive = (item: (typeof navItems)[0]) =>
    item.href === "/admin"
      ? pathname.startsWith("/admin")
      : item.href === "/faq" || item.href === "/api-keys" || item.href === "/tasks" || item.href === "/plan"
        ? pathname === item.href
        : pathname.startsWith(item.href);

  return (
    <div className="min-h-screen bg-zinc-100 dark:bg-zinc-950">
      {/* Mobile menu overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden
        />
      )}

      {/* Top bar - 쿠팡파트너스 페이지 스타일 */}
      <header className="sticky top-0 z-50 flex h-14 items-center border-b border-zinc-200 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900">
        {/* 모바일: 햄버거 */}
        <div className="flex w-10 shrink-0 items-center lg:hidden">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(true)}
            aria-label="메뉴 열기"
          >
            <Menu className="size-5" />
          </Button>
        </div>

        {/* 데스크톱: 로고 (왼쪽) */}
        <div className="hidden shrink-0 lg:block">
          <Link href="/dashboard" className="font-semibold text-zinc-900 dark:text-zinc-50">
            쿠팡파트너스 자동포스팅
          </Link>
        </div>

        {/* 모바일: 가운데 브랜딩 (쿠팡파트너스처럼) */}
        <div className="flex flex-1 justify-center lg:hidden">
          <span className="font-semibold text-zinc-900 dark:text-zinc-50 text-center">
            쿠팡파트너스 자동포스팅
          </span>
        </div>

        {/* 데스크톱: 상단 가로 메뉴 */}
        <nav className="hidden flex-1 items-center justify-center gap-0 lg:flex">
          {navItems.map((item) => (
            <Link
              key={item.href + item.label}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive(item)
                  ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                  : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-50"
              )}
            >
              <item.icon className="size-4 shrink-0" />
              {item.label}
            </Link>
          ))}
        </nav>

        {/* 오른쪽: 잔액, 이메일, 로그아웃 */}
        <div className="flex shrink-0 items-center gap-2">
          <div className="text-xs sm:text-sm">
            <span className="text-zinc-500 dark:text-zinc-400">잔액 </span>
            <span className="font-semibold">{balance?.toLocaleString() ?? 0}원</span>
          </div>
          <span className="hidden max-w-[140px] truncate text-sm text-zinc-600 dark:text-zinc-400 md:block">
            {email}
          </span>
          <Button variant="ghost" size="sm" onClick={onLogout} title="로그아웃">
            <LogOut className="size-4" />
          </Button>
        </div>
      </header>

      {/* 모바일 메뉴 드로어 */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-72 transform border-r border-zinc-200 bg-white transition-transform duration-200 dark:border-zinc-800 dark:bg-zinc-900 lg:hidden",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-zinc-200 px-4 dark:border-zinc-800">
          <span className="font-semibold text-zinc-900 dark:text-zinc-50">
            메뉴
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="메뉴 닫기"
          >
            <X className="size-5" />
          </Button>
        </div>
        <nav className="flex flex-col gap-1 p-4">
          {navItems.map((item) => (
            <Link
              key={item.href + item.label}
              href={item.href}
              onClick={() => setMobileMenuOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                isActive(item)
                  ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                  : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-50"
              )}
            >
              <item.icon className="size-5 shrink-0" />
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* Page content - 쿠팡파트너스처럼 가운데 정렬, 전체 너비 미사용 */}
      <main className="p-4 sm:p-6">
        <div className="mx-auto max-w-5xl">
          {children}
        </div>
      </main>
    </div>
  );
}
