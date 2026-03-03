"use client";

import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useRouter } from "next/navigation";
import { CheckCircle, Clock, XCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

async function parseTxtFile(file: File) {
  const text = await file.text();
  const arr = text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const uniq = Array.from(new Set(arr));
  return uniq;
}

type Profile = {
  user_id: string;
  phone: string | null;
  cost_per_post?: number | null;
  daily_post_limit: number;
  total_posts_count: number;
  total_post_limit: number;
  referrer_user_id: string | null;
  referrer_locked: boolean;
  referral_code: string | null;
  coupang_access_key?: string | null;
  coupang_secret_key?: string | null;
  balance?: number | null;
  total_charged?: number | null;
  referral_reward_total?: number | null;
  admin_bonus_total?: number | null;
};

export default function DashboardPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [balance, setBalance] = useState<number>(0);
  const [totalCharged, setTotalCharged] = useState<number>(0);

  const [phoneInput, setPhoneInput] = useState("");
  const [refCodeInput, setRefCodeInput] = useState("");

  const [referredCount, setReferredCount] = useState<number>(0);
  const [referrerBonusTotal, setReferrerBonusTotal] = useState<number>(0);
  const [effectiveReferralPercent, setEffectiveReferralPercent] = useState<number>(10);

  const [planDaily, setPlanDaily] = useState<number>(0);
  const [planTotal, setPlanTotal] = useState<number>(0);
  const [planMsg, setPlanMsg] = useState<string>("");
  const [planErr, setPlanErr] = useState<string>("");

  const [todayBase, setTodayBase] = useState<number>(0);
  const [todayCarry, setTodayCarry] = useState<number>(0);
  const [todayTarget, setTodayTarget] = useState<number>(0);
  const [remainingTotal, setRemainingTotal] = useState<number>(0);

  const [keywordInput, setKeywordInput] = useState("");
  const [kwMsg, setKwMsg] = useState("");

  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [bulkKeywords, setBulkKeywords] = useState<string[]>([]);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [bulkMsg, setBulkMsg] = useState<string>("");

  const [kwList, setKwList] = useState<{ id: string; keyword: string; created_at: string }[]>([]);
  const [kwSearch, setKwSearch] = useState("");
  const [kwLoading, setKwLoading] = useState(false);

  const [appSettings, setAppSettings] = useState<{ global_post_cost?: number }>({});

  const [postTasks, setPostTasks] = useState<
    { id: string; keyword: string; status: string; created_at: string; updated_at: string | null; published_url: string | null; assigned_vm_name: string | null }[]
  >([]);
  const [postTasksLoading, setPostTasksLoading] = useState(false);

  const canSetReferrer = useMemo(() => {
    if (!profile) return false;
    return !profile.referrer_locked && !profile.referrer_user_id;
  }, [profile]);

  const filteredKeywords = useMemo(() => {
    const q = kwSearch.trim().toLowerCase();
    if (!q) return kwList;
    return kwList.filter((k) => k.keyword.toLowerCase().includes(q));
  }, [kwList, kwSearch]);

  const posted = Number(profile?.total_posts_count ?? 0);
  const cost = Number(profile?.cost_per_post ?? appSettings?.global_post_cost ?? 70);
  const todayDoneCount = useMemo(() => {
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    return (postTasks ?? []).filter(
      (t) => t && t.status === "done" && t.updated_at && new Date(t.updated_at) >= todayStart
    ).length;
  }, [postTasks]);
  const pendingCount = (postTasks ?? []).filter((t) => t && (t.status === "pending" || t.status === "assigned")).length;
  const failedCount = (postTasks ?? []).filter((t) => t && t.status === "failed").length;
  const remaining = Math.max(planTotal - posted, 0);
  const neededBudget = remaining * cost; // 앞으로 남은 발행분 전체 필요 예산

  const totalLimit = Number(profile?.total_post_limit ?? 0);
  const possibleByBalance = cost > 0 ? Math.floor(balance / cost) : 0;

  // 한국시간(KST) 기준 오늘 날짜
  const now = new Date();
  const kst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  const kstToday = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate()));
  // ↑ "KST의 오늘 00:00" 느낌으로 날짜만 맞추기

  const dailyLimit = Number(profile?.daily_post_limit ?? 0);
  const totalDone = Number(profile?.total_posts_count ?? 0);
  const remainingPosts = Math.max(totalLimit - totalDone, 0);

  // 남은 일수(오늘 포함): 하루 0이면 완료예정일 계산 불가
  const daysNeeded =
    dailyLimit > 0 ? Math.ceil(remainingPosts / dailyLimit) : null;

  // 완료 예정일 (KST 기준)
  let expectedEndDateText = "계산 불가";
  if (daysNeeded !== null) {
    // 오늘을 1일차로 계산 → (daysNeeded - 1)일 더하기
    const end = new Date(kstToday.getTime() + (daysNeeded - 1) * 24 * 60 * 60 * 1000);
    const y = end.getUTCFullYear();
    const m = String(end.getUTCMonth() + 1).padStart(2, "0");
    const d = String(end.getUTCDate()).padStart(2, "0");
    expectedEndDateText = `${y}-${m}-${d}`;
  }

  const loadAll = async () => {
    const { data: userData } = await supabase.auth.getUser();
    if (!userData.user) {
      router.push("/login");
      return;
    }
    setEmail(userData.user.email ?? "");

    const uid = userData.user.id;
    let p: unknown = null;
    let pErr: { message: string } | null = null;
    // profiles 스키마: id 또는 user_id 사용 (user_id 우선 시도 — id 없는 스키마 대응)
    const { data: byUserId, error: e2 } = await supabase.from("profiles").select("*").eq("user_id", uid).maybeSingle();
    if (byUserId) {
      p = byUserId;
    } else if (!e2) {
      const { data: byId, error: e1 } = await supabase.from("profiles").select("*").eq("id", uid).maybeSingle();
      p = byId;
      pErr = e1;
    } else {
      pErr = e2;
    }

    if (pErr) {
      alert("profiles 조회 실패: " + pErr.message);
      return;
    }
    if (!p) {
      alert("프로필이 없습니다. Supabase profiles 테이블에 user_id=" + uid + " 로 행을 추가해주세요.");
      return;
    }
    const profileRow = p as Profile & { id?: string; phone_num?: string; max_daily_post_count?: number; current_post_cnt?: number; total_post_limit?: number };
    if (!profileRow.user_id) profileRow.user_id = profileRow.id ?? uid;
    if (profileRow.phone === undefined && profileRow.phone_num !== undefined) profileRow.phone = profileRow.phone_num;
    if (profileRow.daily_post_limit === undefined && profileRow.max_daily_post_count !== undefined) profileRow.daily_post_limit = profileRow.max_daily_post_count;
    if (profileRow.total_posts_count === undefined && profileRow.current_post_cnt !== undefined) profileRow.total_posts_count = profileRow.current_post_cnt;

    setProfile(profileRow as Profile);
    setPhoneInput(profileRow.phone ?? "");
    setPlanDaily(Number(profileRow.daily_post_limit ?? 0));
    setPlanTotal(Number(profileRow.total_post_limit ?? 0));

    // 잔액 RPC
    const { data: bal, error: bErr } = await supabase.rpc("get_wallet_balance");
    if (bErr) {
      alert("잔액 조회 실패: " + bErr.message);
      return;
    }
    setBalance(Number(bal ?? 0));

    // 충전금액 (profiles.total_charged)
    setTotalCharged(Number(profileRow.total_charged ?? 0));

    // 추천 통계
    const { data: stats, error: sErr } = await supabase.rpc("get_referral_stats");
    if (sErr) {
      alert("추천 통계 조회 실패: " + sErr.message);
    } else if (Array.isArray(stats) && stats[0]) {
      setReferredCount(Number(stats[0].referred_count ?? 0));
      setReferrerBonusTotal(Number(stats[0].total_referrer_bonus ?? 0));
    }

    // 추천 % (내 적용 퍼센트)
    const { data: pct, error: pctErr } = await supabase.rpc("get_effective_referral_percent");
    if (pctErr) {
      alert("추천 % 조회 실패: " + pctErr.message);
    } else {
      setEffectiveReferralPercent(Number(pct ?? 10));
    }

    const { data: tgt, error: tErr } = await supabase.rpc("get_today_target_with_carry");
    if (!tErr && Array.isArray(tgt) && tgt[0]) {
      setTodayBase(Number(tgt[0].base_daily ?? 0));
      setTodayCarry(Number(tgt[0].carry_over ?? 0));
      setTodayTarget(Number(tgt[0].today_target ?? 0));
      setRemainingTotal(Number(tgt[0].remaining_total ?? 0));
    }

    // app_settings.global_post_cost 로드 (유저별 override 없을 때 사용)
    const { data: costRow } = await supabase
      .from("app_settings")
      .select("value")
      .eq("key", "global_post_cost")
      .single();

    const costNum = Number((costRow?.value as unknown) ?? 70);
    if (!Number.isNaN(costNum)) {
      setAppSettings((prev) => ({ ...prev, global_post_cost: costNum }));
    }

    await loadKeywords();
    await loadPostTasks();
  };

  const loadPostTasks = async () => {
    const { data: userData } = await supabase.auth.getUser();
    if (!userData.user) return;

    setPostTasksLoading(true);
    const { data, error } = await supabase
      .from("post_tasks")
      .select("id, keyword, status, created_at, updated_at, published_url, assigned_vm_name")
      .eq("user_id", userData.user.id)
      .order("created_at", { ascending: false })
      .limit(100);

    setPostTasksLoading(false);
    if (error) {
      console.error("post_tasks 조회 실패:", error);
      return;
    }
    setPostTasks((data ?? []) as { id: string; keyword: string; status: string; created_at: string; updated_at: string | null; published_url: string | null; assigned_vm_name: string | null }[]);
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
    if (!confirm("이 키워드를 삭제할까?")) return;

    const { error } = await supabase.from("user_keywords").delete().eq("id", id);
    if (error) return setKwMsg("❌ 삭제 실패: " + error.message);

    setKwMsg("✅ 삭제 완료");
    await loadKeywords();
  };

  const clearAllKeywords = async (skipConfirm?: boolean) => {
    if (!skipConfirm && !confirm("정말 전체 키워드를 삭제할까? (되돌릴 수 없음)")) return;

    const { data, error } = await supabase.rpc("clear_my_keywords");
    if (error) throw new Error(error.message);

    setKwMsg(`✅ 전체 삭제 완료 (${data ?? 0}개 삭제)`);
    await loadKeywords();
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addKeywords = async (keywords: string[]) => {
    const { data, error } = await supabase.rpc("add_user_keywords_limited", {
      p_keywords: keywords,
    });
    if (error) throw error;
    const row = Array.isArray(data) ? data[0] : data;
    return row as { inserted: number; skipped: number; remaining_after: number; message: string };
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

  const savePhone = async () => {
    if (!profile) return;

    const { error } = await supabase
      .from("profiles")
      .update({ phone_num: phoneInput })
      .eq("user_id", profile.user_id);

    if (error) {
      const { error: e2 } = await supabase.from("profiles").update({ phone: phoneInput }).eq("user_id", profile.user_id);
      if (e2) return alert("전화번호 저장 실패: " + e2.message);
    }

    alert("전화번호 저장 완료");
    await loadAll();
  };

  const setReferrer = async () => {
    if (!canSetReferrer) return;
    if (!refCodeInput.trim()) return alert("추천인 코드를 입력해줘.");

    const { error } = await supabase.rpc("set_referrer_by_code", {
      p_code: refCodeInput.trim(),
    });

    if (error) return alert("추천인 설정 실패: " + error.message);

    alert("추천인 설정 완료! (이후 변경 불가)");
    setRefCodeInput("");
    await loadAll();
  };

  const savePlan = async () => {
    setPlanMsg("");
    setPlanErr("");

    if (!profile) return;

    const d = Number(planDaily);
    const t = Number(planTotal);

    if (!Number.isFinite(d) || !Number.isFinite(t)) {
      setPlanErr("❌ 숫자만 입력해줘.");
      return;
    }

    if (d < 0 || t < 0) {
      setPlanErr("❌ 0 이상으로 입력해줘.");
      return;
    }

    // ✅ total=0은 미설정으로 허용, 그 외엔 total >= daily 강제
    if (t !== 0 && t < d) {
      setPlanErr("❌ 전체 발행 개수는 하루 발행 개수보다 크거나 같아야 합니다.");
      return;
    }

    if (t !== 0 && t < posted) {
      setPlanErr(`❌ 전체 발행개수는 이미 발행한 ${posted}개보다 작을 수 없어.`);
      return;
    }

    // 잔액으로 충분한지 UI에서도 먼저 안내
    if (balance < neededBudget) {
      setPlanErr(
        `❌ 잔액 부족: 필요한 예산 ${neededBudget.toLocaleString()}원 (현재 ${balance.toLocaleString()}원)`
      );
      return;
    }

    const { error } = await supabase.rpc("update_post_plan", {
      p_daily_limit: d,
      p_total_limit: t,
    });

    if (error) {
      setPlanErr("❌ 저장 실패: " + error.message);
      return;
    }

    setPlanMsg("✅ 저장 완료!");
    await loadAll();
  };

  const logout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  if (!profile) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="rounded-2xl border shadow-sm">
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-20" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card className="rounded-2xl border shadow-sm">
          <CardHeader>
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-4 w-64" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* KPI 3 cards (잔액/충전은 관리자 페이지로 이동) */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="rounded-2xl border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-zinc-500">오늘 완료</CardTitle>
            <CheckCircle className="size-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{todayDoneCount}건</div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-zinc-500">대기중</CardTitle>
            <Clock className="size-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pendingCount}건</div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-zinc-500">실패</CardTitle>
            <XCircle className="size-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{failedCount}건</div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-2xl border shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">요약</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
        <div>내 추천코드: <b>{profile.referral_code ?? "-"}</b></div>
        <div>발행당 비용: {cost.toLocaleString()}원</div>
        <div>하루 발행 제한: {Number(profile?.daily_post_limit ?? 0).toLocaleString()}개</div>
        <div>
          오늘 발행 목표: {todayBase}개{" "}
          {todayCarry > 0 && (
            <>
              + <span style={{ color: "red", fontWeight: 700 }}>
                어제 미작업분 {todayCarry}개
              </span>
            </>
          )}
          {" "}/ 남은 예정 개수 {todayTarget}개
        </div>
        <div className="text-xs text-gray-500">
          * 시간 지연/예약 작업량으로 당일 발행이 부족하면, 미작업분은 다음날 목표에 자동 합산됩니다.
        </div>
        <div>전체 발행 제한: {totalLimit.toLocaleString()}개</div>
        <div>전체발행 완료 예정일(KST): {expectedEndDateText}</div>
        <div>누적 발행: {Number(profile?.total_posts_count ?? 0).toLocaleString()}개</div>
        <div className="text-xs text-gray-500">
          * 예정일은 "하루 발행 개수 × 전체 발행 개수" 기준의 계산값입니다. <br />
          * 작업량/예약/시간 지연으로 1~2일 오차가 생길 수 있으며, 당일 미발행분은 다음날로 이월될 수 있습니다.
        </div>
        <div className="pt-2 border-t mt-2">
          <div className="font-bold">추천 현황</div>
          <div>내 추천인 수: {referredCount.toLocaleString()}명</div>
          <div>현재 추천 적립율: {effectiveReferralPercent}%</div>
          <div>추천 적립 누적: {referrerBonusTotal.toLocaleString()}원</div>
        </div>
        </CardContent>
      </Card>

      <div className="border rounded-xl p-4 space-y-3">
        <div className="font-bold">발행 계획 설정</div>

        <div className="flex gap-3 items-center">
          <div className="w-40 text-sm">하루 발행 개수</div>
          <input
            className="border rounded-lg p-2 w-32"
            type="number"
            value={planDaily}
            onChange={(e) => setPlanDaily(Number(e.target.value))}
          />
        </div>

        <div className="flex gap-3 items-center">
          <div className="w-40 text-sm">전체 발행 개수</div>
          <input
            className="border rounded-lg p-2 w-32"
            type="number"
            value={planTotal}
            onChange={(e) => setPlanTotal(Number(e.target.value))}
          />
        </div>

        <div className="text-sm text-gray-700 border-t pt-3">
          <div>이미 발행: <b>{posted.toLocaleString()}</b>개</div>
          <div>남은 발행: <b>{remaining.toLocaleString()}</b>개</div>
          <div>
            발행당 비용: <b>{cost.toLocaleString()}</b>원
            {" "}→ 필요한 예산: <b>{neededBudget.toLocaleString()}</b>원
          </div>
          <div className="text-xs text-gray-500">
            <span className="inline-block rounded-lg border border-emerald-200 bg-emerald-50/90 px-3 py-2 text-sm font-medium text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">
            * 전체 발행 개수만큼 발행이 끝날 때까지, 매일 "하루 발행 개수"만큼 진행됩니다.
          </span>
          </div>
        </div>

        <button className="border rounded-lg px-3 py-2" onClick={savePlan}>
          계획 저장
        </button>

        {planErr && (
          <div style={{ color: "red", marginTop: 8, fontWeight: 600 }}>
            {planErr}
          </div>
        )}
        {planMsg && (
          <div style={{ color: "green", marginTop: 8, fontWeight: 600 }}>
            {planMsg}
          </div>
        )}
      </div>

      <div className="border rounded-xl p-4 space-y-3">
        <div className="font-bold">전화번호</div>
        <div className="flex gap-2 items-center">
          <input
            className="border rounded-lg p-2 w-64"
            placeholder="010-1234-5678"
            value={phoneInput}
            onChange={(e) => setPhoneInput(e.target.value)}
          />
          <button className="border rounded-lg px-3 py-2" onClick={savePhone}>
            저장
          </button>
        </div>
      </div>

      <div className="border rounded-xl p-4 space-y-3">
        <div className="font-bold">키워드 등록</div>
        <div className="text-xs text-gray-500">* 최대 1,000개까지 등록가능합니다.</div>

        <div className="flex gap-2 items-center">
          <input
            className="border rounded-lg p-2 flex-1"
            value={keywordInput}
            onChange={(e) => setKeywordInput(e.target.value)}
            placeholder="키워드 1개 입력"
          />
          <button className="border rounded-lg px-3 py-2" onClick={addOneKeyword}>
            + 1개 등록
          </button>
        </div>

        <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 12 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>TXT 일괄등록</div>

          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <label
              style={{
                display: "inline-block",
                padding: "10px 14px",
                border: "1px solid #ccc",
                borderRadius: 8,
                cursor: "pointer",
                background: "#fafafa",
                fontWeight: 600,
              }}
            >
              📄 TXT 파일 선택
              <input
                type="file"
                accept=".txt,text/plain"
                style={{ display: "none" }}
                onChange={async (e) => {
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
                }}
              />
            </label>

            {bulkFile && (
              <button
                type="button"
                onClick={() => {
                  setBulkFile(null);
                  setBulkKeywords([]);
                  setBulkMsg("일괄등록 취소됨");
                }}
                style={{
                  padding: "10px 14px",
                  border: "1px solid #ccc",
                  borderRadius: 8,
                  cursor: "pointer",
                  background: "#fff",
                  fontWeight: 600,
                }}
              >
                ❌ 취소
              </button>
            )}
          </div>

          <div style={{ marginTop: 10, fontSize: 14, color: "#333" }}>
            {!bulkFile ? (
              <div style={{ color: "#666" }}>파일을 선택하면 키워드 개수/미리보기가 표시됩니다.</div>
            ) : (
              <div
                style={{
                  marginTop: 8,
                  padding: 10,
                  borderRadius: 8,
                  background: "#f7f7f7",
                  border: "1px dashed #ccc",
                }}
              >
                <div><b>선택된 파일:</b> {bulkFile.name}</div>
                <div><b>키워드 개수:</b> {bulkKeywords.length.toLocaleString()}개</div>
                <div style={{ marginTop: 6, color: "#666" }}>
                  <b>미리보기:</b>{" "}
                  {bulkKeywords.slice(0, 20).join(", ")}
                  {bulkKeywords.length > 20 ? " ..." : ""}
                </div>
              </div>
            )}

            {bulkMsg && <div style={{ marginTop: 8, color: "#0a7" }}>✅ {bulkMsg}</div>}
          </div>

          <div style={{ marginTop: 12 }}>
            <button
              type="button"
              disabled={!bulkFile || bulkKeywords.length === 0 || bulkLoading}
              onClick={async () => {
                if (!bulkKeywords.length) return;

                const MAX = 1000;
                const currentCount = kwList.length;
                const remaining = Math.max(0, MAX - currentCount);

                if (remaining <= 0) {
                  alert("최대 1,000개까지 등록가능합니다. 더 이상 등록할 수 없습니다.");
                  return;
                }

                let kws = [...bulkKeywords];
                if (kws.length > remaining) {
                  alert(`최대 1,000개까지 등록가능합니다.\n이번에는 ${remaining}개까지만 등록됩니다.`);
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
              style={{
                padding: "10px 14px",
                border: "1px solid #0a7",
                borderRadius: 8,
                cursor: !bulkFile ? "not-allowed" : "pointer",
                background: bulkFile ? "#0a7" : "#ccc",
                color: "#fff",
                fontWeight: 700,
              }}
            >
              {bulkLoading ? "등록 중..." : "✅ 일괄 등록"}
            </button>
          </div>
        </div>

        {kwMsg && <div className="text-sm mt-2">{kwMsg}</div>}
      </div>

      <div className="border rounded-xl p-4 space-y-3">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
          <div className="font-bold" style={{ margin: 0 }}>내 키워드 목록</div>
          <button
            type="button"
            onClick={async () => {
              if (!confirm("정말 전체 키워드를 삭제할까요? (복구 불가)")) return;
              if (!confirm("진짜로 삭제합니다. 마지막 확인!")) return;

              try {
                await clearAllKeywords(true);
                setBulkMsg("전체 삭제 완료");
              } catch (err: unknown) {
                alert(err instanceof Error ? err.message : "전체 삭제 실패");
              }
            }}
            style={{
              padding: "10px 14px",
              border: "1px solid #d33",
              borderRadius: 8,
              cursor: "pointer",
              background: "#fff",
              color: "#d33",
              fontWeight: 800,
            }}
          >
            🗑 전체 삭제
          </button>
        </div>

        <div className="flex gap-2 items-center">
          <input
            className="border rounded-lg p-2 flex-1"
            value={kwSearch}
            onChange={(e) => setKwSearch(e.target.value)}
            placeholder="검색어 입력 (예: 로지텍마우스, 계란방석...)"
          />
          <button className="border rounded-lg px-3 py-2" onClick={loadKeywords}>
            새로고침
          </button>
        </div>

        <div className="text-sm text-gray-600">
          총 <b>{kwList.length.toLocaleString()}</b>개 / 표시 <b>{filteredKeywords.length.toLocaleString()}</b>개
          {kwLoading ? " (불러오는 중...)" : ""}
        </div>

        <div style={{ maxHeight: 320, overflow: "auto", border: "1px solid #eee", borderRadius: 10 }}>
          {filteredKeywords.length === 0 ? (
            <div style={{ padding: 12, opacity: 0.7 }}>키워드가 없거나 검색 결과가 없어.</div>
          ) : (
            filteredKeywords.map((k) => (
              <div
                key={k.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 10,
                  padding: "10px 12px",
                  borderBottom: "1px solid #f0f0f0",
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 700, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {k.keyword}
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>
                    {new Date(k.created_at).toLocaleString("ko-KR")}
                  </div>
                </div>

                <button className="border rounded-lg px-3 py-2" onClick={() => deleteKeyword(k.id)}>
                  삭제
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="border rounded-xl p-4 space-y-3">
        <div className="font-bold">추천인 설정 (1회)</div>

        {canSetReferrer ? (
          <div className="flex gap-2 items-center">
            <input
              className="border rounded-lg p-2 w-64"
              placeholder="추천인 코드 입력"
              value={refCodeInput}
              onChange={(e) => setRefCodeInput(e.target.value)}
            />
            <button className="border rounded-lg px-3 py-2" onClick={setReferrer}>
              추천인 등록
            </button>
          </div>
        ) : (
          <div className="text-sm text-gray-600">
            추천인은 이미 설정되어 변경할 수 없습니다.
          </div>
        )}
      </div>

      <button className="border rounded-lg px-3 py-2" onClick={logout}>
        로그아웃
      </button>
    </div>
  );
}
