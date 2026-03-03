"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Calendar, FileText, List, Rocket } from "lucide-react";
import { cn } from "@/lib/utils";

async function parseTxtFile(file: File) {
  const text = await file.text();
  const arr = text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return Array.from(new Set(arr));
}

type Profile = {
  user_id: string;
  daily_post_limit: number;
  total_posts_count: number;
  total_post_limit: number;
  cost_per_post?: number | null;
  coupang_access_key?: string | null;
  coupang_secret_key?: string | null;
};

export default function PlanPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [balance, setBalance] = useState<number>(0);
  const [appSettings, setAppSettings] = useState<{ global_post_cost?: number }>({});

  const [planDaily, setPlanDaily] = useState<number>(0);
  const [planTotal, setPlanTotal] = useState<number>(0);
  const [planMsg, setPlanMsg] = useState<string>("");
  const [planErr, setPlanErr] = useState<string>("");

  const [keywordInput, setKeywordInput] = useState("");
  const [kwMsg, setKwMsg] = useState("");
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [bulkKeywords, setBulkKeywords] = useState<string[]>([]);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [bulkMsg, setBulkMsg] = useState<string>("");

  const [kwList, setKwList] = useState<{ id: string; keyword: string; created_at: string }[]>([]);
  const [kwSearch, setKwSearch] = useState("");
  const [kwLoading, setKwLoading] = useState(false);

  const [todayTarget, setTodayTarget] = useState<number>(0);
  const [remainingTotal, setRemainingTotal] = useState<number>(0);
  const [enqueueLoading, setEnqueueLoading] = useState(false);
  const [enqueueMsg, setEnqueueMsg] = useState<string>("");

  const filteredKeywords = useMemo(() => {
    const q = kwSearch.trim().toLowerCase();
    if (!q) return kwList;
    return kwList.filter((k) => k.keyword.toLowerCase().includes(q));
  }, [kwList, kwSearch]);

  const posted = Number(profile?.total_posts_count ?? 0);
  const cost = Number(profile?.cost_per_post ?? appSettings?.global_post_cost ?? 70);

  // 예산으로 가능한 최대 개수 (내 예산 기준)
  const possibleByBudget = cost > 0 ? Math.floor(balance / cost) : 0;
  const maxTotalByBudget = posted + possibleByBudget; // 전체 발행 개수 최대
  const maxDailyByBudget = possibleByBudget; // 하루 발행 개수 최대

  const costPerPost = Number(profile?.cost_per_post ?? appSettings?.global_post_cost ?? 70);

  const startEnqueue = async () => {
    setEnqueueMsg("");
    if (!profile) return;

    const ak = (profile.coupang_access_key ?? "").toString().trim();
    const sk = (profile.coupang_secret_key ?? "").toString().trim();
    if (!ak || !sk) {
      setEnqueueMsg("❌ 쿠팡파트너스 키를 등록 후 진행하세요. (API 키 설정 메뉴)");
      return;
    }

    const dailyLimit = Number(profile.daily_post_limit ?? 0);
    if (dailyLimit <= 0) {
      setEnqueueMsg("❌ 하루 발행 개수를 먼저 설정해주세요.");
      return;
    }

    const { data: userData } = await supabase.auth.getUser();
    if (!userData.user) {
      setEnqueueMsg("❌ 로그인 정보가 없습니다.");
      return;
    }

    const userId = profile.user_id ?? userData.user.id;

    setEnqueueLoading(true);
    try {
      const { data, error } = await supabase.rpc("enqueue_post_tasks_paid", {
        p_user_id: userId,
        p_channel: "cafe",
        p_count: dailyLimit,
        p_cost: costPerPost,
        p_payload: { meta: {} },
      });

      if (error) {
        setEnqueueMsg("❌ 발행시작 실패: " + error.message);
        return;
      }

      const inserted = Number((data as { inserted?: number })?.inserted ?? 0);
      const msg = (data as { message?: string })?.message ?? "";
      if (inserted === 0 && msg) {
        setEnqueueMsg("❌ " + msg);
        return;
      }

      setEnqueueMsg(`✅ 발행시작 완료! ${inserted}개 작업이 post_tasks에 등록되었습니다.`);
      await loadAll();
    } catch (err: unknown) {
      setEnqueueMsg("❌ 오류: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setEnqueueLoading(false);
    }
  };

  const addKeywords = async (keywords: string[]) => {
    const { data, error } = await supabase.rpc("add_user_keywords_limited", {
      p_keywords: keywords,
    });
    if (error) throw error;
    const row = Array.isArray(data) ? data[0] : data;
    return row as { inserted: number; skipped: number; remaining_after: number; message: string };
  };

  const loadKeywords = async () => {
    setKwLoading(true);
    const { data, error } = await supabase
      .from("user_keywords")
      .select("id, keyword, created_at")
      .order("created_at", { ascending: false })
      .limit(2000);
    setKwLoading(false);
    if (error) {
      setKwMsg("❌ 키워드 불러오기 실패: " + error.message);
      return;
    }
    setKwList(data ?? []);
  };

  const deleteKeyword = async (id: string) => {
    if (!confirm("이 키워드를 삭제할까요?")) return;
    const { error } = await supabase.from("user_keywords").delete().eq("id", id);
    if (error) return setKwMsg("❌ 삭제 실패: " + error.message);
    setKwMsg("✅ 삭제 완료");
    await loadKeywords();
  };

  const clearAllKeywords = async (skipConfirm?: boolean) => {
    if (!skipConfirm && !confirm("정말 전체 키워드를 삭제할까요? (되돌릴 수 없음)")) return;
    const { data, error } = await supabase.rpc("clear_my_keywords");
    if (error) throw new Error(error.message);
    setKwMsg(`✅ 전체 삭제 완료 (${data ?? 0}개 삭제)`);
    await loadKeywords();
  };

  const addOneKeyword = async () => {
    setKwMsg("");
    const k = keywordInput.trim();
    if (!k) return;
    try {
      const result = await addKeywords([k]);
      alert(`${result.message}\n등록: ${result.inserted} / 제외: ${result.skipped}\n남은 등록 가능: ${result.remaining_after}`);
      setKeywordInput("");
      await loadKeywords();
    } catch (err: unknown) {
      setKwMsg("❌ 등록 실패: " + (err instanceof Error ? err.message : String(err)));
    }
  };

  const savePlan = async () => {
    setPlanMsg("");
    setPlanErr("");
    if (!profile) return;

    const d = Number(planDaily);
    const t = Number(planTotal);

    if (!Number.isFinite(d) || !Number.isFinite(t)) {
      setPlanErr("❌ 숫자만 입력해주세요.");
      return;
    }
    if (d < 0 || t < 0) {
      setPlanErr("❌ 0 이상으로 입력해주세요.");
      return;
    }
    if (t !== 0 && t < d) {
      setPlanErr("❌ 전체 발행 개수는 하루 발행 개수보다 크거나 같아야 합니다.");
      return;
    }

    // 예산 기준 검증: 내 예산으로 가능한 개수까지만 설정 가능
    if (t > maxTotalByBudget) {
      setPlanErr(`❌ 전체 발행 개수는 예산 기준 최대 ${maxTotalByBudget.toLocaleString()}개까지 가능합니다. (현재 잔액: ${balance.toLocaleString()}원, 1건당 ${cost.toLocaleString()}원)`);
      return;
    }
    if (d > maxDailyByBudget) {
      setPlanErr(`❌ 하루 발행 개수는 예산 기준 최대 ${maxDailyByBudget.toLocaleString()}개까지 가능합니다. (현재 잔액: ${balance.toLocaleString()}원, 1건당 ${cost.toLocaleString()}원)`);
      return;
    }

    const { error } = await supabase
      .from("profiles")
      .update({
        daily_post_limit: d,
        total_post_limit: t,
        updated_at: new Date().toISOString(),
      })
      .eq("user_id", profile.user_id);

    if (error) {
      setPlanErr("❌ 저장 실패: " + error.message);
      return;
    }
    setPlanMsg("✅ 계획 저장 완료!");
    const { data: p } = await supabase.from("profiles").select("daily_post_limit, total_post_limit").eq("user_id", profile.user_id).single();
    if (p) {
      setPlanDaily(Number(p.daily_post_limit ?? 0));
      setPlanTotal(Number(p.total_post_limit ?? 0));
    }
  };

  const loadAll = async () => {
    const { data: userData } = await supabase.auth.getUser();
    if (!userData.user) {
      router.push("/login");
      return;
    }

    const uid = userData.user.id;
    const { data: profileRow } = await supabase.from("profiles").select("user_id, daily_post_limit, total_posts_count, total_post_limit, cost_per_post, coupang_access_key, coupang_secret_key").eq("user_id", uid).maybeSingle();

    let p = profileRow;
    if (!p) {
      const { data: byId } = await supabase.from("profiles").select("user_id, daily_post_limit, total_posts_count, total_post_limit, cost_per_post, coupang_access_key, coupang_secret_key").eq("id", uid).maybeSingle();
      p = byId;
    }

    if (p) {
      setProfile(p as Profile);
      setPlanDaily(Number(p.daily_post_limit ?? 0));
      setPlanTotal(Number(p.total_post_limit ?? 0));
    }

    const { data: costRow } = await supabase.from("app_settings").select("value").eq("key", "global_post_cost").single();
    const costNum = Number((costRow?.value as unknown) ?? 70);
    if (!Number.isNaN(costNum)) setAppSettings((prev) => ({ ...prev, global_post_cost: costNum }));

    const { data: bal } = await supabase.rpc("get_wallet_balance");
    setBalance(Number(bal ?? 0));

    const { data: tgt } = await supabase.rpc("get_today_target_with_carry");
    if (Array.isArray(tgt) && tgt[0]) {
      setTodayTarget(Number(tgt[0].today_target ?? 0));
      setRemainingTotal(Number(tgt[0].remaining_total ?? 0));
    }

    await loadKeywords();
  };

  useEffect(() => {
    loadAll();
  }, []);

  if (!profile) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-64 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">발행계획</h1>

      {/* 발행 현황 - 버튼형, 모바일 2x3 그리드 */}
      <Card className="rounded-2xl border shadow-sm overflow-hidden">
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 px-5 py-4">
          <div className="flex items-center justify-center rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm font-medium shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
            <span className="text-zinc-500 dark:text-zinc-400">하루발행</span>{" "}
            <span className="ml-1 font-bold tabular-nums">{planDaily.toLocaleString()}개</span>
          </div>
          <div className="flex items-center justify-center rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm font-medium shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
            <span className="text-zinc-500 dark:text-zinc-400">전체발행</span>{" "}
            <span className="ml-1 font-bold tabular-nums">{planTotal.toLocaleString()}개</span>
          </div>
          <div className="flex items-center justify-center rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm font-medium shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
            <span className="text-zinc-500 dark:text-zinc-400">발행완료</span>{" "}
            <span className="ml-1 font-bold tabular-nums">{posted.toLocaleString()}개</span>
          </div>
          <div className="flex items-center justify-center rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm font-medium shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
            <span className="text-zinc-500 dark:text-zinc-400">남은발행</span>{" "}
            <span className="ml-1 font-bold tabular-nums">{remainingTotal.toLocaleString()}개</span>
          </div>
          <div className="flex items-center justify-center rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm font-medium shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
            <span className="text-zinc-500 dark:text-zinc-400">발행금액</span>{" "}
            <span className="ml-1 font-bold text-emerald-600 tabular-nums dark:text-emerald-500">{costPerPost.toLocaleString()}원</span>
          </div>
          <Button
            size="lg"
            disabled={enqueueLoading || Number(profile?.daily_post_limit ?? 0) <= 0}
            onClick={startEnqueue}
            className="w-full bg-emerald-600 hover:bg-emerald-700"
          >
            <Rocket className="size-5 shrink-0" />
            {enqueueLoading ? "등록 중..." : "발행 시작"}
          </Button>
        </div>
        {enqueueMsg && (
          <div
            className={cn(
              "border-t px-5 py-2 text-sm font-medium",
              enqueueMsg.startsWith("✅") ? "text-green-600" : "text-red-600"
            )}
          >
            {enqueueMsg}
          </div>
        )}
      </Card>

      {/* 발행 계획 설정 - 필수 */}
      <Card className="rounded-2xl border-2 border-emerald-500/60 bg-emerald-50/30 shadow-sm dark:border-emerald-500/40 dark:bg-emerald-950/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="size-5" />
            발행 계획 설정
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 입력 필드 먼저 */}
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex gap-2 items-center">
              <label className="text-sm font-medium whitespace-nowrap">하루 발행 개수</label>
              <Input type="number" value={planDaily} onChange={(e) => setPlanDaily(Number(e.target.value))} className="w-24" max={maxDailyByBudget} />
            </div>
            <div className="flex gap-2 items-center">
              <label className="text-sm font-medium whitespace-nowrap">전체 발행 개수</label>
              <Input type="number" value={planTotal} onChange={(e) => setPlanTotal(Number(e.target.value))} className="w-24" max={maxTotalByBudget} />
            </div>
            <Button onClick={savePlan}>계획 저장</Button>
          </div>
          {planErr && <p className="text-sm font-medium text-red-600">{planErr}</p>}
          {planMsg && <p className="text-sm font-medium text-green-600">{planMsg}</p>}

          {/* 설명은 아래 */}
          <div className="border-t pt-4 space-y-2 text-sm text-zinc-500 dark:text-zinc-400">
            <p>예산(잔액) 기준으로 설정 가능한 최대 개수가 제한됩니다.</p>
            <p>회원님은 잔액기준 최대 <b className="text-zinc-700 dark:text-zinc-300">{maxTotalByBudget.toLocaleString()}개</b> 까지 발행가능합니다.</p>
            <p className="rounded-lg border border-emerald-200 bg-emerald-50/90 px-3 py-2 text-sm font-medium text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
              * 전체 발행 개수만큼 발행이 끝날 때까지, 매일 &quot;하루 발행 개수&quot;만큼 진행됩니다.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 키워드 등록 */}
      <Card className="rounded-2xl border shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="size-5" />
            키워드 등록
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input value={keywordInput} onChange={(e) => setKeywordInput(e.target.value)} placeholder="키워드 1개 입력" className="flex-1" disabled={kwList.length >= 1000} />
            <Button onClick={addOneKeyword} disabled={kwList.length >= 1000}>+ 1개 등록</Button>
          </div>

          <div className="rounded-xl border border-zinc-200 p-4 space-y-3 dark:border-zinc-800">
            <div className="font-semibold">TXT 일괄등록</div>
            {kwList.length >= 1000 ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm dark:border-amber-900/50 dark:bg-amber-950/30">
                <p className="font-medium text-amber-800 dark:text-amber-200">
                  {kwList.length.toLocaleString()}개가 등록되었습니다. 재등록은 아래 &quot;내 키워드 목록&quot;에서 키워드를 삭제 후 등록해주세요.
                </p>
              </div>
            ) : (
              <>
                <div className="flex gap-2 items-center flex-wrap">
                  <label className="inline-flex items-center justify-center rounded-lg border border-zinc-300 bg-zinc-50 px-4 py-2 text-sm font-medium cursor-pointer hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:hover:bg-zinc-700">
                    📄 TXT 파일 선택
                    <input type="file" accept=".txt,text/plain" className="hidden" onChange={async (e) => {
                      const f = e.target.files?.[0] ?? null;
                      if (!f) return;
                      setBulkMsg("");
                      setBulkFile(f);
                      setBulkLoading(true);
                      try {
                        const kws = await parseTxtFile(f);
                        setBulkKeywords(kws);
                      } catch (err: unknown) {
                        setBulkFile(null);
                        setBulkKeywords([]);
                        setBulkMsg(err instanceof Error ? err.message : "파일 읽기 실패");
                      } finally {
                        setBulkLoading(false);
                      }
                    }} />
                  </label>
                  {bulkFile && (
                    <Button variant="outline" size="sm" onClick={() => { setBulkFile(null); setBulkKeywords([]); setBulkMsg("일괄등록 취소됨"); }}>
                      ❌ 취소
                    </Button>
                  )}
                </div>
                {bulkFile ? (
                  <div className="rounded-lg border border-dashed border-zinc-300 bg-zinc-50 p-3 text-sm dark:border-zinc-700 dark:bg-zinc-800">
                    <div><b>선택된 파일:</b> {bulkFile.name}</div>
                    <div><b>키워드 개수:</b> {bulkKeywords.length.toLocaleString()}개</div>
                    <div className="mt-1 text-zinc-600 dark:text-zinc-400">
                      <b>미리보기:</b> {bulkKeywords.slice(0, 20).join(", ")}{bulkKeywords.length > 20 ? " ..." : ""}
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500">파일을 선택하면 키워드 개수/미리보기가 표시됩니다.</p>
                )}
                {bulkMsg && <p className="text-sm text-green-600">✅ {bulkMsg}</p>}
                <Button
                  disabled={!bulkFile || bulkKeywords.length === 0 || bulkLoading}
                  onClick={async () => {
                if (!bulkKeywords.length) return;
                const MAX = 1000;
                const currentCount = kwList.length;
                const remaining = Math.max(0, MAX - currentCount);
                if (remaining <= 0) {
                  alert("최대 1,000개까지 등록가능합니다.");
                  return;
                }
                let kws = [...bulkKeywords];
                if (kws.length > remaining) {
                  alert(`이번에는 ${remaining}개까지만 등록됩니다.`);
                  kws = kws.slice(0, remaining);
                }
                if (!confirm(`키워드 ${kws.length.toLocaleString()}개를 일괄 등록할까요?`)) return;
                setBulkLoading(true);
                setBulkMsg("");
                try {
                  const result = await addKeywords(kws);
                  alert(`${result.message}\n등록: ${result.inserted} / 제외: ${result.skipped}\n남은 등록 가능: ${result.remaining_after}`);
                  setBulkMsg(`일괄등록 완료 (${kws.length.toLocaleString()}개)`);
                  setBulkFile(null);
                  setBulkKeywords([]);
                  await loadKeywords();
                } catch (err: unknown) {
                  alert(err instanceof Error ? err.message : "일괄등록 실패");
                } finally {
                  setBulkLoading(false);
                }
              }}
            >
              {bulkLoading ? "등록 중..." : "✅ 일괄 등록"}
            </Button>
              </>
            )}
          </div>
          {kwMsg && <p className="text-sm">{kwMsg}</p>}

          {/* 설명은 아래 */}
          <div className="border-t pt-4 space-y-2 text-sm text-zinc-500 dark:text-zinc-400">
            <p>최대 1,000개까지 등록가능합니다.</p>
            <p>원하는 키워드로 포스팅하려면 키워드를 등록하세요.</p>
            <p className="rounded-lg border border-emerald-200 bg-emerald-50/90 px-3 py-2 text-sm font-medium text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
              등록하지 않으셔도 관리자가 등록한 키워드로 랜덤 자동 포스팅이 진행됩니다.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 내 키워드 목록 */}
      <Card className="rounded-2xl border shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <List className="size-5" />
              내 키워드 목록
            </CardTitle>
          </div>
          <Button variant="destructive" size="sm" onClick={async () => {
            if (!confirm("정말 전체 키워드를 삭제할까요? (복구 불가)")) return;
            if (!confirm("진짜로 삭제합니다. 마지막 확인!")) return;
            try {
              await clearAllKeywords(true);
              setBulkMsg("전체 삭제 완료");
            } catch (err: unknown) {
              alert(err instanceof Error ? err.message : "전체 삭제 실패");
            }
          }}>
            🗑 전체 삭제
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input value={kwSearch} onChange={(e) => setKwSearch(e.target.value)} placeholder="검색어 입력 (예: 로지텍마우스, 계란방석...)" className="flex-1" />
            <Button variant="outline" onClick={loadKeywords}>새로고침</Button>
          </div>
          <p className="text-sm text-zinc-600">
            총 <b>{kwList.length.toLocaleString()}</b>개 / 표시 <b>{filteredKeywords.length.toLocaleString()}</b>개
            {kwLoading ? " (불러오는 중...)" : ""}
          </p>
          <div className="max-h-80 overflow-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
            {filteredKeywords.length === 0 ? (
              <div className="p-4 text-center text-zinc-500">키워드가 없거나 검색 결과가 없습니다.</div>
            ) : (
              filteredKeywords.map((k) => (
                <div key={k.id} className="flex items-center justify-between gap-4 border-b border-zinc-100 px-4 py-3 last:border-0 dark:border-zinc-800">
                  <div className="min-w-0 flex-1">
                    <div className="font-medium truncate">{k.keyword}</div>
                    <div className="text-xs text-zinc-500">{new Date(k.created_at).toLocaleString("ko-KR")}</div>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => deleteKeyword(k.id)}>삭제</Button>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
