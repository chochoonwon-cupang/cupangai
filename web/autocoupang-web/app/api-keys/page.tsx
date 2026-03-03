"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Key, ExternalLink } from "lucide-react";

export default function APIKeysPage() {
  const router = useRouter();
  const [accessKey, setAccessKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [keyMsg, setKeyMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [profileUserId, setProfileUserId] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        router.push("/login");
        return;
      }

      const { data: byUserId } = await supabase
        .from("profiles")
        .select("user_id, coupang_access_key, coupang_secret_key")
        .eq("user_id", user.id)
        .maybeSingle();

      let row = byUserId as { user_id?: string; id?: string; coupang_access_key?: string; coupang_secret_key?: string } | null;
      if (!row) {
        const { data: byId } = await supabase
          .from("profiles")
          .select("id, user_id, coupang_access_key, coupang_secret_key")
          .eq("id", user.id)
          .maybeSingle();
        row = byId;
      }

      if (row) {
        const uid = row.user_id ?? row.id ?? user.id;
        setProfileUserId(uid);
        setAccessKey((row.coupang_access_key ?? "") as string);
        setSecretKey((row.coupang_secret_key ?? "") as string);
      }
      setLoading(false);
    };
    load();
  }, [router]);

  const saveCoupangKeys = async () => {
    if (!profileUserId) return;
    setKeyMsg("");
    setSaving(true);

    const { error } = await supabase
      .from("profiles")
      .update({
        coupang_access_key: accessKey.trim(),
        coupang_secret_key: secretKey.trim(),
        updated_at: new Date().toISOString(),
      })
      .eq("user_id", profileUserId);

    setSaving(false);
    if (error) {
      setKeyMsg("❌ 저장 실패: " + error.message);
      return;
    }
    setKeyMsg("✅ 쿠팡 파트너스 API 키 저장 완료!");
  };

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <div className="h-8 w-48 animate-pulse rounded bg-zinc-200 dark:bg-zinc-800" />
        <div className="h-64 animate-pulse rounded-2xl bg-zinc-200 dark:bg-zinc-800" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-2">
        <Key className="size-8 text-emerald-600 dark:text-emerald-500" />
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
          쿠팡파트너스 API 키 설정
        </h1>
      </div>

      {/* 안내 카드 */}
      <Card className="rounded-2xl border border-amber-200 bg-amber-50/80 dark:border-amber-900/50 dark:bg-amber-950/30">
        <CardHeader>
          <CardTitle className="text-base">API 키 발급 안내</CardTitle>
          <div className="mt-2 space-y-2 text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
            <p>
              API 키는 <strong className="text-zinc-900 dark:text-zinc-100">최종 승인된 쿠팡 파트너스 회원</strong>에게만 제공됩니다.
              최종 승인된 회원은 파트너스 센터에서 생성 버튼 클릭 시 Access Key와 Secret Key를 바로 받을 수 있습니다.
            </p>
            <p>
              <strong className="text-zinc-900 dark:text-zinc-100">쿠팡 파트너스 최종 승인</strong>을 위해서는 파트너스 링크를 통한 판매가 <strong>15만원 이상</strong>이 되어야 합니다.
              처음 빠르게 승인받으려는 분들은 다른 계정(가족·지인 등)으로 자신의 파트너스 링크를 통해 구매하는 방법을 사용합니다.
            </p>
            <p className="text-amber-700 dark:text-amber-400 font-medium">
              ⚠️ 쿠팡파트너스 아이디와 구매하는 아이디가 같으면 실적으로 인정되지 않습니다. 유의해 주세요.
            </p>
          </div>
        </CardHeader>
      </Card>

      <Card className="rounded-2xl border shadow-sm">
        <CardHeader>
          <CardTitle>API 키 발급</CardTitle>
          <CardDescription>
            쿠팡 파트너스 센터 설정에서 발급받은 Access Key와 Secret Key를 입력하세요.
            포스팅 자동 발행에 사용됩니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <a
            href="https://partners.coupang.com/settings/api-key"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300"
          >
            <ExternalLink className="size-4" />
            파트너스 API 키 발급 페이지로 이동 (설정 &gt; API 키 발급)
          </a>

          <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Access Key
              </label>
              <Input
                type="text"
                placeholder="Access Key 입력"
                value={accessKey}
                onChange={(e) => setAccessKey(e.target.value)}
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Secret Key
              </label>
              <Input
                type="password"
                placeholder="Secret Key 입력"
                value={secretKey}
                onChange={(e) => setSecretKey(e.target.value)}
                className="font-mono"
              />
            </div>
          </div>

          <Button onClick={saveCoupangKeys} disabled={saving}>
            {saving ? "저장 중..." : "저장"}
          </Button>

          {keyMsg && (
            <p
              className={`text-sm font-medium ${
                keyMsg.startsWith("✅") ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
              }`}
            >
              {keyMsg}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
