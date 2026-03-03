"use client";

import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useRouter } from "next/navigation";
import { Rocket, Wallet, CheckCircle, Clock, XCircle, FileText } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { StatusBadge } from "@/lib/ui/status";
import { EmptyState } from "@/components/common/EmptyState";
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
  const [chargeAmount, setChargeAmount] = useState<number>(1000);

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

  const [accessKey, setAccessKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [keyMsg, setKeyMsg] = useState("");

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

  const [enqueueLoading, setEnqueueLoading] = useState(false);
  const [enqueueMsg, setEnqueueMsg] = useState<string>("");

  const [postTasks, setPostTasks] = useState<
    { id: string; keyword: string; status: string; created_at: string; updated_at: string | null; published_url: string | null; assigned_vm_name: string | null }[]
  >([]);
  const [postTasksLoading, setPostTasksLoading] = useState(false);
  const [postTasksPage, setPostTasksPage] = useState(1);
  const [postTasksSortKey, setPostTasksSortKey] = useState<"keyword" | "status" | "assigned_vm_name" | "created_at" | "updated_at" | "published_url">("created_at");
  const [postTasksSortAsc, setPostTasksSortAsc] = useState(false);
  const [postTasksStatusFilter, setPostTasksStatusFilter] = useState<string>("all");
  const [postTasksKeywordSearch, setPostTasksKeywordSearch] = useState("");
  const [selectedTask, setSelectedTask] = useState<{
    id: string;
    keyword: string;
    status: string;
    created_at: string;
    updated_at: string | null;
    published_url: string | null;
    assigned_vm_name: string | null;
  } | null>(null);
  const POST_TASKS_PER_PAGE = 10;

  const canSetReferrer = useMemo(() => {
    if (!profile) return false;
    return !profile.referrer_locked && !profile.referrer_user_id;
  }, [profile]);

  const filteredKeywords = useMemo(() => {
    const q = kwSearch.trim().toLowerCase();
    if (!q) return kwList;
    return kwList.filter((k) => k.keyword.toLowerCase().includes(q));
  }, [kwList, kwSearch]);

  const STATUS_ORDER: Record<string, number> = { pending: 0, assigned: 1, done: 2, failed: 3 };
  const postTasksFiltered = useMemo(() => {
    let arr = postTasks;
    if (postTasksStatusFilter !== "all") {
      arr = arr.filter((t) => t.status === postTasksStatusFilter);
    }
    if (postTasksKeywordSearch.trim()) {
      const q = postTasksKeywordSearch.trim().toLowerCase();
      arr = arr.filter((t) => (t.keyword || "").toLowerCase().includes(q));
    }
    return arr;
  }, [postTasks, postTasksStatusFilter, postTasksKeywordSearch]);
  const postTasksSorted = useMemo(() => {
    const arr = [...postTasksFiltered];
    const key = postTasksSortKey;
    const asc = postTasksSortAsc;
    arr.sort((a, b) => {
      if (key === "keyword") {
        const sa = a.keyword || "";
        const sb = b.keyword || "";
        return asc ? sa.localeCompare(sb, "ko") : sb.localeCompare(sa, "ko");
      }
      if (key === "status") {
        const va = STATUS_ORDER[a.status] ?? 99;
        const vb = STATUS_ORDER[b.status] ?? 99;
        return asc ? va - vb : vb - va;
      }
      if (key === "assigned_vm_name") {
        const sa = a.assigned_vm_name || "";
        const sb = b.assigned_vm_name || "";
        return asc ? sa.localeCompare(sb, "ko") : sb.localeCompare(sa, "ko");
      }
      if (key === "created_at") {
        const da = new Date(a.created_at).getTime();
        const db = new Date(b.created_at).getTime();
        return asc ? da - db : db - da;
      }
      if (key === "updated_at") {
        const da = a.updated_at ? new Date(a.updated_at).getTime() : 0;
        const db = b.updated_at ? new Date(b.updated_at).getTime() : 0;
        return asc ? da - db : db - da;
      }
      if (key === "published_url") {
        const ha = a.published_url ? 1 : 0;
        const hb = b.published_url ? 1 : 0;
        return asc ? ha - hb : hb - ha;
      }
      return 0;
    });
    return arr;
  }, [postTasks, postTasksSortKey, postTasksSortAsc]);

  const postTasksTotalPages = useMemo(
    () => Math.max(1, Math.ceil(postTasksFiltered.length / POST_TASKS_PER_PAGE)),
    [postTasksFiltered.length]
  );
  const postTasksPaginated = useMemo(() => {
    const start = (postTasksPage - 1) * POST_TASKS_PER_PAGE;
    return postTasksSorted.slice(start, start + POST_TASKS_PER_PAGE);
  }, [postTasksSorted, postTasksPage]);

  const handlePostTasksSort = (key: typeof postTasksSortKey) => {
    if (postTasksSortKey === key) {
      setPostTasksSortAsc((prev) => !prev);
    } else {
      setPostTasksSortKey(key);
      setPostTasksSortAsc(key === "created_at" ? false : true); // 등록일은 기본 최신순
    }
    setPostTasksPage(1);
  };

  useEffect(() => {
    if (postTasksPage > postTasksTotalPages) setPostTasksPage(1);
  }, [postTasksPage, postTasksTotalPages]);

  const posted = Number(profile?.total_posts_count ?? 0);
  const cost = Number(profile?.cost_per_post ?? appSettings?.global_post_cost ?? 70);
  const todayDoneCount = useMemo(() => {
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    return postTasks.filter(
      (t) => t.status === "done" && t.updated_at && new Date(t.updated_at) >= todayStart
    ).length;
  }, [postTasks]);
  const pendingCount = postTasks.filter((t) => t.status === "pending" || t.status === "assigned").length;
  const failedCount = postTasks.filter((t) => t.status === "failed").length;
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
    setAccessKey(profileRow.coupang_access_key ?? "");
    setSecretKey(profileRow.coupang_secret_key ?? "");

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
    setPostTasksPage(1);
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

  const saveCoupangKeys = async () => {
    setKeyMsg("");
    if (!profile) return;

    const { error } = await supabase
      .from("profiles")
      .update({
        coupang_access_key: accessKey.trim(),
        coupang_secret_key: secretKey.trim(),
        updated_at: new Date().toISOString(),
      })
      .eq("user_id", profile.user_id);

    if (error) return setKeyMsg("❌ 저장 실패: " + error.message);
    setKeyMsg("✅ 쿠팡 키 저장 완료!");
    await loadAll();
  };

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

  const charge = async () => {
    if (!chargeAmount || chargeAmount <= 0) return alert("충전 금액을 입력해줘.");

    const { error } = await supabase.rpc("charge_wallet", {
      p_amount: chargeAmount,
    });

    if (error) return alert("충전 실패: " + error.message);

    alert("충전 완료 (테스트)");
    await loadAll(); // balance + total_charged 갱신
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

  const startEnqueue = async () => {
    setEnqueueMsg("");
    if (!profile) return;

    const ak = (profile.coupang_access_key ?? "").toString().trim();
    const sk = (profile.coupang_secret_key ?? "").toString().trim();
    if (!ak || !sk) {
      setEnqueueMsg("❌ 쿠팡파트너스 키를 등록후 진행하세요.");
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
    const costVal = Number(profile?.cost_per_post ?? appSettings?.global_post_cost ?? 70);

    setEnqueueLoading(true);
    try {
      const { data, error } = await supabase.rpc("enqueue_post_tasks_paid", {
        p_user_id: userId,
        p_channel: "cafe",
        p_count: dailyLimit,
        p_cost: costVal,
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
      {/* Hero */}
      <Card className="rounded-2xl border shadow-sm overflow-hidden">
        <div className="flex flex-col gap-6 p-6 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              쿠팡파트너스 자동포스팅
            </h1>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              70원부터, 워커가 자동 발행
            </p>
            <div className="mt-4 flex flex-wrap gap-4 text-xs text-zinc-600 dark:text-zinc-400">
              <span>오늘 남은 발행량: {todayTarget}개</span>
              <span>전체 남은 발행량: {remainingTotal}개</span>
            </div>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Button
              size="lg"
              disabled={enqueueLoading || Number(profile?.daily_post_limit ?? 0) <= 0}
              onClick={startEnqueue}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              <Rocket className="size-5" />
              {enqueueLoading ? "등록 중..." : "발행 시작"}
            </Button>
          </div>
        </div>
        {enqueueMsg && (
          <div
            className={cn(
              "border-t px-6 py-2 text-sm font-medium",
              enqueueMsg.startsWith("✅") ? "text-green-600" : "text-red-600"
            )}
          >
            {enqueueMsg}
          </div>
        )}
      </Card>

      {/* KPI 4 cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="rounded-2xl border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-zinc-500">현재 잔액</CardTitle>
            <Wallet className="size-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{balance.toLocaleString()}원</div>
          </CardContent>
        </Card>
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

      {/* 작업 테이블 카드 */}
      <Card className="rounded-2xl border shadow-sm">
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>내 포스트 태스크</CardTitle>
            <CardDescription>등록한 발행 작업 목록</CardDescription>
          </div>
          <Button variant="outline" size="default" onClick={loadPostTasks} disabled={postTasksLoading}>
            {postTasksLoading ? "불러오는 중..." : "새로고침"}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Input
              placeholder="키워드 검색"
              value={postTasksKeywordSearch}
              onChange={(e) => setPostTasksKeywordSearch(e.target.value)}
              className="max-w-xs"
            />
            <div className="flex flex-wrap gap-1">
              {[
                { value: "all", label: "전체" },
                { value: "pending", label: "대기" },
                { value: "assigned", label: "진행" },
                { value: "done", label: "완료" },
                { value: "failed", label: "실패" },
              ].map(({ value, label }) => (
                <Button
                  key={value}
                  variant={postTasksStatusFilter === value ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    setPostTasksStatusFilter(value);
                    setPostTasksPage(1);
                  }}
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>
          {postTasksLoading ? (
            <Skeleton className="h-64 w-full rounded-xl" />
          ) : postTasks.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="아직 작업이 없어요"
              description="발행 시작 버튼을 눌러 작업을 등록해보세요."
              action={{ label: "발행 시작", onClick: startEnqueue }}
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead
                      className="cursor-pointer hover:bg-zinc-100"
                      onClick={() => handlePostTasksSort("keyword")}
                    >
                      키워드 {postTasksSortKey === "keyword" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-zinc-100"
                      onClick={() => handlePostTasksSort("status")}
                    >
                      현재작업상황 {postTasksSortKey === "status" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-zinc-100"
                      onClick={() => handlePostTasksSort("assigned_vm_name")}
                    >
                      담당VM {postTasksSortKey === "assigned_vm_name" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-zinc-100"
                      onClick={() => handlePostTasksSort("created_at")}
                    >
                      등록일 {postTasksSortKey === "created_at" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-zinc-100"
                      onClick={() => handlePostTasksSort("updated_at")}
                    >
                      작업완료시 {postTasksSortKey === "updated_at" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-zinc-100"
                      onClick={() => handlePostTasksSort("published_url")}
                    >
                      작업링크 {postTasksSortKey === "published_url" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {postTasksPaginated.map((t) => (
                    <TableRow
                      key={t.id}
                      className="cursor-pointer"
                      onClick={() => setSelectedTask(t)}
                    >
                      <TableCell className="font-medium">{t.keyword || "-"}</TableCell>
                      <TableCell>
                        <StatusBadge status={t.status} />
                      </TableCell>
                      <TableCell className="text-zinc-600">{t.assigned_vm_name || "-"}</TableCell>
                      <TableCell className="text-zinc-600">
                        {new Date(t.created_at).toLocaleString("ko-KR")}
                      </TableCell>
                      <TableCell className="text-zinc-600">
                        {(t.status === "done" || t.status === "failed") && t.updated_at
                          ? new Date(t.updated_at).toLocaleString("ko-KR")
                          : "-"}
                      </TableCell>
                      <TableCell>
                        {t.published_url ? (
                          <a
                            href={t.published_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            링크
                          </a>
                        ) : (
                          <span className="text-zinc-400">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {postTasksFiltered.length > POST_TASKS_PER_PAGE && (
                <div className="flex justify-center gap-1 pt-4">
                  {Array.from({ length: postTasksTotalPages }, (_, i) => i + 1).map((p) => (
                    <Button
                      key={p}
                      variant={p === postTasksPage ? "default" : "outline"}
                      size="icon"
                      onClick={() => setPostTasksPage(p)}
                    >
                      {p}
                    </Button>
                  ))}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* 작업 상세 Dialog */}
      <Dialog open={!!selectedTask} onOpenChange={(open) => !open && setSelectedTask(null)}>
        <DialogContent showClose={true}>
          {selectedTask && (
            <>
              <DialogHeader>
                <DialogTitle>작업 상세</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 text-sm">
                <div>
                  <span className="font-medium text-zinc-500">키워드</span>
                  <p className="mt-1 font-medium">{selectedTask.keyword || "-"}</p>
                </div>
                <div>
                  <span className="font-medium text-zinc-500">상태</span>
                  <p className="mt-1">
                    <StatusBadge status={selectedTask.status} />
                  </p>
                </div>
                <div>
                  <span className="font-medium text-zinc-500">담당 VM</span>
                  <p className="mt-1">{selectedTask.assigned_vm_name || "-"}</p>
                </div>
                <div>
                  <span className="font-medium text-zinc-500">등록일</span>
                  <p className="mt-1">{new Date(selectedTask.created_at).toLocaleString("ko-KR")}</p>
                </div>
                {(selectedTask.status === "done" || selectedTask.status === "failed") && selectedTask.updated_at && (
                  <div>
                    <span className="font-medium text-zinc-500">작업완료시</span>
                    <p className="mt-1">{new Date(selectedTask.updated_at).toLocaleString("ko-KR")}</p>
                  </div>
                )}
                {selectedTask.published_url && (
                  <div>
                    <span className="font-medium text-zinc-500">작업 링크</span>
                    <p className="mt-1">
                      <a
                        href={selectedTask.published_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline break-all"
                      >
                        {selectedTask.published_url}
                      </a>
                    </p>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

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
        <div>현재 잔액 기준 총 발행가능: {possibleByBalance.toLocaleString()}개</div>
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

      <Card className="rounded-2xl border shadow-sm">
        <CardHeader>
          <CardTitle>잔액</CardTitle>
          <CardDescription>충전 및 사용 내역</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
        <div className="text-2xl font-bold">{balance.toLocaleString()}원</div>
        <div className="text-sm text-zinc-500">누적 충전금액: {totalCharged.toLocaleString()}원</div>
        <div className="text-sm text-zinc-600 space-y-1">
          <div>추천 적립 누적: {referrerBonusTotal.toLocaleString()}원</div>
          <div>관리자 보너스 충전 누적: {(profile?.admin_bonus_total ?? 0).toLocaleString()}원</div>
        </div>
        <div className="flex gap-2 items-center">
          <Input
            type="number"
            value={chargeAmount}
            onChange={(e) => setChargeAmount(Number(e.target.value) || 0)}
            className="w-40"
          />
          <Button variant="outline" onClick={charge}>
            테스트 충전
          </Button>
        </div>
        <div className="text-xs text-zinc-500">
          * 실제 결제 붙이기 전 테스트용 충전 버튼
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
            * 전체 발행 개수만큼 발행이 끝날 때까지, 매일 "하루 발행 개수"만큼 진행됩니다.
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
        <div className="font-bold">쿠팡파트너스 키 설정</div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Access Key 등록</label>
            <input
              className="border rounded-lg p-2 w-full"
              value={accessKey}
              onChange={(e) => setAccessKey(e.target.value)}
              placeholder="Access Key 입력"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Secret Key 등록</label>
            <input
              className="border rounded-lg p-2 w-full"
              value={secretKey}
              onChange={(e) => setSecretKey(e.target.value)}
              placeholder="Secret Key 입력"
            />
          </div>
        </div>
        <div className="flex gap-2 items-center">
          <button className="border rounded-lg px-3 py-2" onClick={saveCoupangKeys}>
            저장
          </button>
        </div>
        {keyMsg && <div className="text-sm mt-2">{keyMsg}</div>}
      </div>

      <div className="border rounded-xl p-4 space-y-3">
        <div className="font-bold">키워드 등록</div>
        <div className="text-xs text-gray-500">* 키워드는 아이디당 최대 1,000개까지 등록됩니다.</div>

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
                  alert("키워드는 아이디당 최대 1000개까지 등록됩니다. 더 이상 등록할 수 없습니다.");
                  return;
                }

                let kws = [...bulkKeywords];
                if (kws.length > remaining) {
                  alert(`키워드는 아이디당 최대 1000개까지 등록됩니다.\n이번에는 ${remaining}개까지만 등록됩니다.`);
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
            placeholder="검색어 입력 (예: 강남, 계란방석...)"
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
