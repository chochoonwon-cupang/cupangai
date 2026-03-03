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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/supabaseClient";

const navItems = [
  { href: "/dashboard", label: "대시보드", icon: LayoutDashboard },
  { href: "/dashboard", label: "발행계획", icon: Calendar },
  { href: "/dashboard", label: "작업내역", icon: ListTodo },
  { href: "/dashboard", label: "충전/월렛", icon: Wallet },
  { href: "/admin", label: "관리자", icon: Settings },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
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

  return (
    <div className="min-h-screen bg-zinc-100 dark:bg-zinc-950">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 transform border-r border-zinc-200 bg-white transition-transform duration-200 dark:border-zinc-800 dark:bg-zinc-900 lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-zinc-200 px-4 dark:border-zinc-800">
          <span className="font-semibold text-zinc-900 dark:text-zinc-50">
            쿠팡파트너스 자동포스팅
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="size-5" />
          </Button>
        </div>
        <nav className="flex flex-col gap-1 p-4">
          {navItems.map((item) => {
            const isActive =
              item.href === "/admin"
                ? pathname.startsWith("/admin")
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href + item.label}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50"
                    : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-50"
                )}
              >
                <item.icon className="size-5 shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-zinc-200 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="size-5" />
          </Button>
          <div className="flex-1" />
          <div className="flex items-center gap-4">
            <div className="hidden text-sm sm:block">
              <span className="text-zinc-500 dark:text-zinc-400">잔액 </span>
              <span className="font-semibold">{balance?.toLocaleString() ?? 0}원</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="hidden max-w-[180px] truncate text-sm text-zinc-600 dark:text-zinc-400 sm:block">
                {email}
              </span>
              <Button variant="ghost" size="sm" onClick={onLogout}>
                <LogOut className="size-4" />
              </Button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
