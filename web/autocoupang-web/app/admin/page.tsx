"use client";

import { useEffect, useState, useMemo } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useRouter } from "next/navigation";

type UserBalanceRow = {
  user_id: string;
  email: string | null;
  balance: number;
  total_charged: number;
  cost_per_post: number;
  referral_reward_total: number;
  admin_bonus_total: number;
};

type SortKey = "email" | "balance" | "total_charged" | "cost_per_post" | "referral_reward_total" | "admin_bonus_total";

export default function AdminPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [isAdmin, setIsAdmin] = useState(false);

  const [globalPercent, setGlobalPercent] = useState<number>(10);

  const [globalPostCost, setGlobalPostCost] = useState<number>(70);
  const [savingGlobalCost, setSavingGlobalCost] = useState(false);
  const [applyToAll, setApplyToAll] = useState(true);

  const [targetEmail, setTargetEmail] = useState("");
  const [costPerPost, setCostPerPost] = useState<number>(70);
  const [overridePercent, setOverridePercent] = useState<number | "">("");

  const [bonusEmail, setBonusEmail] = useState("");
  const [bonusAmount, setBonusAmount] = useState<number>(1000);
  const [bonusCharging, setBonusCharging] = useState(false);

  // 카페 자동가입 정책 (검색 기반 run_cafe_join_job)
  const [cafeJoinPolicy, setCafeJoinPolicy] = useState({
    run_days: [4, 14, 24] as number[],
    start_time: "09:00",
    created_year_min: 2020,
    created_year_max: 2025,
    recent_post_days: 7,
    recent_post_enabled: true,
    target_count: 50,
    expire_days: 10,
    search_keyword: "",
  });
  const [cafeJoinLoading, setCafeJoinLoading] = useState(true);
  const [cafeJoinSaving, setCafeJoinSaving] = useState(false);

  // 사용자별 금액확인
  const [userBalanceList, setUserBalanceList] = useState<UserBalanceRow[]>([]);
  const [userBalanceLoading, setUserBalanceLoading] = useState(false);
  const [userBalanceSearch, setUserBalanceSearch] = useState("");
  const [userBalanceSortKey, setUserBalanceSortKey] = useState<SortKey>("email");
  const [userBalanceSortAsc, setUserBalanceSortAsc] = useState(true);
  const [showUserSelectModal, setShowUserSelectModal] = useState(false);

  useEffect(() => {
    const init = async () => {
      const { data } = await supabase.auth.getUser();
      if (!data.user) return router.push("/login");

      const userEmail = data.user.email ?? "";
      setEmail(userEmail);

      // 서버에서 최종 판정(보안)
      const { data: adminOk, error } = await supabase.rpc("is_admin");
      if (error || !adminOk) {
        alert("관리자만 접근 가능합니다.");
        router.push("/dashboard");
        return;
      }
      setIsAdmin(true);

      // 전역 퍼센트 로드
      const { data: row } = await supabase
        .from("app_settings")
        .select("value")
        .eq("key", "referral_percent")
        .single();

      const v = row?.value;
      const num = typeof v === "number" ? v : Number(v);
      if (!Number.isNaN(num)) setGlobalPercent(num);

      // 전역 발행당 비용 로드
      const { data: costRow } = await supabase
        .from("app_settings")
        .select("value")
        .eq("key", "global_post_cost")
        .single();

      const costNum = Number((costRow?.value as unknown) ?? 70);
      if (!Number.isNaN(costNum)) setGlobalPostCost(costNum);

      // 카페 자동가입 정책 로드 (관리자 전용)
      setCafeJoinLoading(true);
      try {
        const { data: policyData, error: policyErr } = await supabase.rpc("admin_get_cafe_join_policy");
        if (!policyErr && policyData) {
          const p = policyData as Record<string, unknown>;
          const runDays = Array.isArray(p.run_days) ? (p.run_days as number[]) : [4, 14, 24];
          setCafeJoinPolicy({
            run_days: runDays,
            start_time: (p.start_time as string) ?? "09:00",
            created_year_min: Number(p.created_year_min) ?? 2020,
            created_year_max: Number(p.created_year_max) ?? 2025,
            recent_post_days: Number(p.recent_post_days) ?? 7,
            recent_post_enabled: Boolean(p.recent_post_enabled ?? true),
            target_count: Number(p.target_count) ?? 50,
            expire_days: Number(p.expire_days) ?? 10,
            search_keyword: (p.search_keyword as string) ?? "",
          });
        }
      } catch {
        // RPC 없으면 무시
      } finally {
        setCafeJoinLoading(false);
      }
    };

    init();
  }, [router]);

  const saveGlobalPercent = async () => {
    const { error } = await supabase.rpc("admin_set_referral_percent", {
      p_percent: globalPercent,
    });
    if (error) return alert("저장 실패: " + error.message);
    alert("전역 추천인 % 저장 완료");
  };

  const saveGlobalPostCost = async () => {
    try {
      setSavingGlobalCost(true);
      const p_cost = Number(globalPostCost);

      const { error: e1 } = await supabase.rpc("admin_set_global_post_cost", { p_cost });
      if (e1) return alert(e1.message);

      if (applyToAll) {
        const { error: e2 } = await supabase.rpc("admin_apply_global_post_cost_to_all", { p_cost });
        if (e2) return alert(e2.message);
      }

      alert("저장 완료!");
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setSavingGlobalCost(false);
    }
  };

  const saveUserSettings = async () => {
    const { error } = await supabase.rpc("admin_update_user_settings", {
      p_user_email: targetEmail,
      p_cost_per_post: costPerPost,
      p_referral_percent_override:
        overridePercent === "" ? null : Number(overridePercent),
    });
    if (error) return alert("저장 실패: " + error.message);
    alert("유저 설정 저장 완료");
  };

  const chargeBonus = async () => {
    if (!bonusEmail.trim()) return alert("이메일을 입력해주세요.");
    if (!bonusAmount || bonusAmount <= 0) return alert("충전 금액을 입력해주세요.");
    setBonusCharging(true);
    try {
      const { data, error } = await supabase.rpc("admin_charge_user_by_email", {
        p_email: bonusEmail.trim(),
        p_amount: bonusAmount,
      });
      if (error) throw new Error(error.message);
      const res = data as { success?: boolean; message?: string };
      alert(res?.message ?? (res?.success ? "보너스충전 완료" : "실패"));
      if (res?.success) setBonusEmail("");
    } catch (e) {
      alert(e instanceof Error ? e.message : "보너스충전 실패");
    } finally {
      setBonusCharging(false);
    }
  };

  const loadUserBalances = async (search?: string) => {
    setUserBalanceLoading(true);
    try {
      const { data, error } = await supabase.rpc("admin_get_user_balances", {
        p_search: search !== undefined ? search : userBalanceSearch,
      });
      if (error) throw new Error(error.message);
      const rows = (data ?? []) as UserBalanceRow[];
      setUserBalanceList(rows);
    } catch (e) {
      alert(e instanceof Error ? e.message : "사용자 목록 조회 실패");
    } finally {
      setUserBalanceLoading(false);
    }
  };

  const sortedUserBalances = useMemo(() => {
    const arr = [...userBalanceList];
    const key = userBalanceSortKey;
    const asc = userBalanceSortAsc;
    arr.sort((a, b) => {
      const va = a[key] ?? "";
      const vb = b[key] ?? "";
      if (typeof va === "number" && typeof vb === "number") {
        return asc ? va - vb : vb - va;
      }
      const sa = String(va);
      const sb = String(vb);
      return asc ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });
    return arr;
  }, [userBalanceList, userBalanceSortKey, userBalanceSortAsc]);

  const handleSort = (key: SortKey) => {
    if (userBalanceSortKey === key) {
      setUserBalanceSortAsc((prev) => !prev);
    } else {
      setUserBalanceSortKey(key);
      setUserBalanceSortAsc(true);
    }
  };

  const saveCafeJoinPolicy = async () => {
    setCafeJoinSaving(true);
    try {
      const { error } = await supabase.rpc("admin_upsert_cafe_join_policy", {
        p_run_days: cafeJoinPolicy.run_days,
        p_start_time: cafeJoinPolicy.start_time,
        p_created_year_min: cafeJoinPolicy.created_year_min,
        p_created_year_max: cafeJoinPolicy.created_year_max,
        p_recent_post_days: cafeJoinPolicy.recent_post_days,
        p_recent_post_enabled: cafeJoinPolicy.recent_post_enabled,
        p_target_count: cafeJoinPolicy.target_count,
        p_expire_days: cafeJoinPolicy.expire_days,
        p_search_keyword: cafeJoinPolicy.search_keyword,
      });
      if (error) throw new Error(error.message);
      alert("카페 자동가입 정책 저장 완료");
    } catch (e) {
      alert("저장 실패: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setCafeJoinSaving(false);
    }
  };

  if (!isAdmin) return <div className="p-8">관리자 확인중...</div>;

  return (
    <div className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">관리자 설정</h1>
      <div className="text-sm text-gray-600">로그인: {email}</div>

      {/* 사용자별 금액확인 */}
      <div className="border rounded-xl p-4 space-y-3 bg-slate-50">
        <div className="font-bold">사용자별 금액확인</div>
        <div className="flex gap-2 items-center flex-wrap">
          <input
            className="border rounded-lg p-2 w-64"
            placeholder="아이디(이메일) 검색"
            value={userBalanceSearch}
            onChange={(e) => setUserBalanceSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadUserBalances()}
          />
          <button
            className="border rounded-lg px-3 py-2 bg-white hover:bg-gray-50"
            onClick={() => loadUserBalances()}
            disabled={userBalanceLoading}
          >
            검색
          </button>
          <button
            className="border rounded-lg px-3 py-2 bg-white hover:bg-gray-50"
            onClick={() => {
              setUserBalanceSearch("");
              loadUserBalances("");
            }}
            disabled={userBalanceLoading}
          >
            전체 조회
          </button>
          <button
            className="border rounded-lg px-3 py-2 bg-white hover:bg-gray-50"
            onClick={() => {
              setShowUserSelectModal(true);
              if (userBalanceList.length === 0) loadUserBalances("");
            }}
          >
            아이디 선택
          </button>
        </div>
        {userBalanceLoading ? (
          <div className="text-sm text-gray-500">로딩중...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b bg-white">
                  <th
                    className="p-2 text-left cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort("email")}
                  >
                    아이디 {userBalanceSortKey === "email" && (userBalanceSortAsc ? "↑" : "↓")}
                  </th>
                  <th
                    className="p-2 text-right cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort("balance")}
                  >
                    총잔액 {userBalanceSortKey === "balance" && (userBalanceSortAsc ? "↑" : "↓")}
                  </th>
                  <th
                    className="p-2 text-right cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort("total_charged")}
                  >
                    총충전금액 {userBalanceSortKey === "total_charged" && (userBalanceSortAsc ? "↑" : "↓")}
                  </th>
                  <th
                    className="p-2 text-right cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort("cost_per_post")}
                  >
                    포스팅당비용 {userBalanceSortKey === "cost_per_post" && (userBalanceSortAsc ? "↑" : "↓")}
                  </th>
                  <th
                    className="p-2 text-right cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort("referral_reward_total")}
                  >
                    추천인보너스 {userBalanceSortKey === "referral_reward_total" && (userBalanceSortAsc ? "↑" : "↓")}
                  </th>
                  <th
                    className="p-2 text-right cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort("admin_bonus_total")}
                  >
                    관리자보너스 {userBalanceSortKey === "admin_bonus_total" && (userBalanceSortAsc ? "↑" : "↓")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedUserBalances.map((row) => (
                  <tr key={row.user_id} className="border-b hover:bg-gray-50">
                    <td className="p-2 text-left">{row.email ?? row.user_id ?? "-"}</td>
                    <td className="p-2 text-right">{row.balance.toLocaleString()}</td>
                    <td className="p-2 text-right">{row.total_charged.toLocaleString()}</td>
                    <td className="p-2 text-right">{row.cost_per_post.toLocaleString()}</td>
                    <td className="p-2 text-right">{row.referral_reward_total.toLocaleString()}</td>
                    <td className="p-2 text-right">{row.admin_bonus_total.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {sortedUserBalances.length === 0 && !userBalanceLoading && (
              <div className="p-4 text-center text-gray-500">조회 결과가 없습니다.</div>
            )}
          </div>
        )}
      </div>

      {/* 아이디 선택 모달 */}
      {showUserSelectModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowUserSelectModal(false)}
        >
          <div
            className="bg-white rounded-xl p-4 max-w-lg w-full max-h-[80vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="font-bold mb-2">아이디 선택</div>
            <div className="flex-1 overflow-y-auto border rounded-lg p-2 mb-2">
              {userBalanceList.length === 0 ? (
                <div className="text-sm text-gray-500">먼저 전체 조회 또는 검색을 실행해주세요.</div>
              ) : (
                <div className="space-y-1">
                  {userBalanceList.map((row) => (
                    <button
                      key={row.user_id}
                      className="block w-full text-left p-2 rounded hover:bg-gray-100 text-sm"
                      onClick={() => {
                        setUserBalanceSearch(row.email ?? row.user_id ?? "");
                        setShowUserSelectModal(false);
                        loadUserBalances(row.email ?? row.user_id ?? "");
                      }}
                    >
                      {row.email ?? row.user_id ?? "-"}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <button
              className="border rounded-lg px-3 py-2"
              onClick={() => setShowUserSelectModal(false)}
            >
              닫기
            </button>
          </div>
        </div>
      )}

      <div className="border rounded-xl p-4 space-y-3">
        <div className="font-bold">전역 추천인 적립 % (프로모션)</div>
        <div className="flex gap-2 items-center">
          <input
            className="border rounded-lg p-2 w-32"
            type="number"
            value={globalPercent}
            onChange={(e) => setGlobalPercent(Number(e.target.value))}
          />
          <button className="border rounded-lg px-3 py-2" onClick={saveGlobalPercent}>
            저장
          </button>
        </div>
        <div className="text-xs text-gray-500">
          * 모든 유저에게 적용 (단, 유저별 override가 있으면 override 우선)
        </div>
      </div>

      <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8, marginBottom: 12 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>전체 발행당 비용(기본값)</div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="number"
            value={globalPostCost}
            onChange={(e) => setGlobalPostCost(Number(e.target.value))}
            className="border rounded-lg p-2 w-32"
            min={1}
          />
          <button
            className="border rounded-lg px-3 py-2 disabled:opacity-50"
            onClick={saveGlobalPostCost}
            disabled={savingGlobalCost}
          >
            {savingGlobalCost ? "저장중..." : "저장"}
          </button>
        </div>
        <div style={{ fontSize: 12, color: "#666", marginTop: 6 }}>
          * 신규 유저 기본값/전체 기본 발행비용으로 사용됩니다. (유저별 override가 있으면 override 우선)
        </div>
        <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={applyToAll}
            onChange={(e) => setApplyToAll(e.target.checked)}
          />
          <span>전체 유저 cost_per_post도 함께 {globalPostCost}으로 변경(강제 적용)</span>
        </label>
      </div>

      <div className="border rounded-xl p-4 space-y-3">
        <div className="font-bold">유저별 설정</div>

        <input
          className="border rounded-lg p-2 w-full"
          placeholder="대상 유저 이메일 (예: user@gmail.com)"
          value={targetEmail}
          onChange={(e) => setTargetEmail(e.target.value)}
        />

        <div className="flex gap-2 items-center">
          <div className="w-40 text-sm">발행당 비용(원)</div>
          <input
            className="border rounded-lg p-2 w-32"
            type="number"
            value={costPerPost}
            onChange={(e) => setCostPerPost(Number(e.target.value))}
          />
        </div>

        <div className="flex gap-2 items-center">
          <div className="w-40 text-sm">추천인 % override</div>
          <input
            className="border rounded-lg p-2 w-32"
            type="number"
            placeholder="비우면 전역"
            value={overridePercent}
            onChange={(e) => setOverridePercent(e.target.value === "" ? "" : Number(e.target.value))}
          />
        </div>

        <button className="border rounded-lg px-3 py-2" onClick={saveUserSettings}>
          유저 설정 저장
        </button>
      </div>

      <div className="border rounded-xl p-4 space-y-3 bg-blue-50/50">
        <div className="font-bold">보너스충전</div>
        <div className="text-xs text-gray-600 mb-2">
          특정 유저 이메일로 보너스 금액을 충전합니다. balance와 total_charged가 증가합니다.
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          <input
            className="border rounded-lg p-2 w-64"
            placeholder="대상 유저 이메일"
            value={bonusEmail}
            onChange={(e) => setBonusEmail(e.target.value)}
          />
          <input
            className="border rounded-lg p-2 w-28"
            type="number"
            min={1}
            value={bonusAmount}
            onChange={(e) => setBonusAmount(Number(e.target.value) || 0)}
          />
          <span className="text-sm">원</span>
          <button
            className="border rounded-lg px-3 py-2 disabled:opacity-50"
            onClick={chargeBonus}
            disabled={bonusCharging}
          >
            {bonusCharging ? "충전중..." : "보너스 충전"}
          </button>
        </div>
      </div>

      {/* 카페 자동가입 정책 (검색 기반 run_cafe_join_job) — 관리자 전용 */}
      <div className="border rounded-xl p-4 space-y-3 bg-amber-50/50">
        <div className="font-bold">카페 자동가입 정책 (검색 기반)</div>
        <div className="text-xs text-gray-600 mb-2">
          section.cafe.naver.com 키워드 검색 → 정책 확인(생성년도·최근글) → 가입 → agent_cafe_lists 저장. 워커/GUI에서 run_cafe_join_job 실행 시 사용.
        </div>
        {cafeJoinLoading ? (
          <div className="text-sm text-gray-500">로딩중...</div>
        ) : (
          <>
            <div className="flex gap-2 items-center flex-wrap">
              <span className="w-36 text-sm">검색 키워드</span>
              <div className="flex-1 min-w-[200px]">
                <input
                  className="border rounded-lg p-2 w-full"
                  placeholder="쉼표로 구분 (예: 건강, 다이어트, 요리, 여행)"
                  value={cafeJoinPolicy.search_keyword}
                  onChange={(e) => setCafeJoinPolicy((p) => ({ ...p, search_keyword: e.target.value }))}
                />
                <span className="text-xs text-gray-500">여러 개 입력 시 가입 시 랜덤 선택 — 중복 가입 방지</span>
              </div>
            </div>
            <div className="flex gap-2 items-center flex-wrap">
              <span className="w-36 text-sm">경과일 삭제</span>
              <input
                className="border rounded-lg p-2 w-20"
                type="number"
                min={1}
                max={365}
                value={cafeJoinPolicy.expire_days}
                onChange={(e) => setCafeJoinPolicy((p) => ({ ...p, expire_days: Number(e.target.value) || 10 }))}
              />
              <span className="text-xs text-gray-500">last_posted_at 기준 N일 경과 카페 자동 삭제</span>
            </div>
            <div className="flex gap-2 items-center flex-wrap">
              <span className="w-36 text-sm">목표 가입 수</span>
              <input
                className="border rounded-lg p-2 w-20"
                type="number"
                min={1}
                value={cafeJoinPolicy.target_count}
                onChange={(e) => setCafeJoinPolicy((p) => ({ ...p, target_count: Number(e.target.value) || 50 }))}
              />
              <span className="text-xs text-gray-500">네이버 아이디당 유지할 카페 개수 (이 이하면 자동 가입)</span>
            </div>
            <div className="flex gap-2 items-center flex-wrap">
              <span className="w-36 text-sm">생성년도 범위</span>
              <input
                className="border rounded-lg p-2 w-20"
                type="number"
                value={cafeJoinPolicy.created_year_min}
                onChange={(e) => setCafeJoinPolicy((p) => ({ ...p, created_year_min: Number(e.target.value) || 2020 }))}
              />
              <span>~</span>
              <input
                className="border rounded-lg p-2 w-20"
                type="number"
                value={cafeJoinPolicy.created_year_max}
                onChange={(e) => setCafeJoinPolicy((p) => ({ ...p, created_year_max: Number(e.target.value) || 2025 }))}
              />
            </div>
            <div className="flex gap-2 items-center flex-wrap">
              <span className="w-36 text-sm">최근글 정책</span>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={cafeJoinPolicy.recent_post_enabled}
                  onChange={(e) => setCafeJoinPolicy((p) => ({ ...p, recent_post_enabled: e.target.checked }))}
                />
                <span>최근 N일 이내 글 없음</span>
              </label>
              <input
                className="border rounded-lg p-2 w-16"
                type="number"
                min={1}
                value={cafeJoinPolicy.recent_post_days}
                onChange={(e) => setCafeJoinPolicy((p) => ({ ...p, recent_post_days: Number(e.target.value) || 7 }))}
              />
              <span className="text-sm">일</span>
            </div>
            <button
              className="border rounded-lg px-3 py-2 disabled:opacity-50"
              onClick={saveCafeJoinPolicy}
              disabled={cafeJoinSaving}
            >
              {cafeJoinSaving ? "저장중..." : "카페 가입 정책 저장"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
