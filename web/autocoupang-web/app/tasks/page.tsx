"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { CheckCircle, Clock, Calendar, Package } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { FileText } from "lucide-react";

type Profile = {
  user_id: string;
  daily_post_limit: number;
  total_posts_count: number;
  total_post_limit: number;
};

type PostTask = {
  id: string;
  keyword: string;
  status: string;
  created_at: string;
  updated_at: string | null;
  published_url: string | null;
  assigned_vm_name: string | null;
};

const STATUS_ORDER: Record<string, number> = { pending: 0, assigned: 1, done: 2, failed: 3 };

export default function TasksPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [postTasks, setPostTasks] = useState<PostTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [postTasksPage, setPostTasksPage] = useState(1);
  const [postTasksSortKey, setPostTasksSortKey] = useState<"keyword" | "status" | "assigned_vm_name" | "created_at" | "updated_at" | "published_url">("created_at");
  const [postTasksSortAsc, setPostTasksSortAsc] = useState(false);
  const [postTasksStatusFilter, setPostTasksStatusFilter] = useState<string>("all");
  const [postTasksKeywordSearch, setPostTasksKeywordSearch] = useState("");
  const [selectedTask, setSelectedTask] = useState<PostTask | null>(null);
  const POST_TASKS_PER_PAGE = 10;

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
  }, [postTasksFiltered, postTasksSortKey, postTasksSortAsc]);

  const postTasksTotalPages = useMemo(
    () => Math.max(1, Math.ceil(postTasksFiltered.length / POST_TASKS_PER_PAGE)),
    [postTasksFiltered.length]
  );

  const postTasksPaginated = useMemo(() => {
    const start = (postTasksPage - 1) * POST_TASKS_PER_PAGE;
    return postTasksSorted.slice(start, start + POST_TASKS_PER_PAGE);
  }, [postTasksSorted, postTasksPage]);

  const todayDoneCount = useMemo(() => {
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    return postTasks.filter(
      (t) => t.status === "done" && t.updated_at && new Date(t.updated_at) >= todayStart
    ).length;
  }, [postTasks]);

  const pendingCount = postTasks.filter((t) => t.status === "pending" || t.status === "assigned").length;

  const dailyLimit = Number(profile?.daily_post_limit ?? 0);
  const totalDone = Number(profile?.total_posts_count ?? 0);
  const totalLimit = Number(profile?.total_post_limit ?? 0);
  const remainingPosts = Math.max(totalLimit - totalDone, 0);

  const daysNeeded = dailyLimit > 0 ? Math.ceil(remainingPosts / dailyLimit) : null;
  let expectedEndDateText = "계산 불가";
  if (daysNeeded !== null && daysNeeded > 0) {
    const kst = new Date(Date.now() + 9 * 60 * 60 * 1000);
    const kstToday = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate()));
    const end = new Date(kstToday.getTime() + (daysNeeded - 1) * 24 * 60 * 60 * 1000);
    const y = end.getUTCFullYear();
    const m = String(end.getUTCMonth() + 1).padStart(2, "0");
    const d = String(end.getUTCDate()).padStart(2, "0");
    expectedEndDateText = `${y}-${m}-${d}`;
  } else if (remainingPosts === 0) {
    expectedEndDateText = "완료";
  }

  const handlePostTasksSort = (key: typeof postTasksSortKey) => {
    if (postTasksSortKey === key) {
      setPostTasksSortAsc((prev) => !prev);
    } else {
      setPostTasksSortKey(key);
      setPostTasksSortAsc(key === "created_at" ? false : true);
    }
    setPostTasksPage(1);
  };

  const loadAll = async () => {
    const { data: userData } = await supabase.auth.getUser();
    if (!userData.user) {
      router.push("/login");
      return;
    }

    const uid = userData.user.id;
    const { data: profileRow } = await supabase
      .from("profiles")
      .select("user_id, daily_post_limit, total_posts_count, total_post_limit")
      .eq("user_id", uid)
      .maybeSingle();

    if (!profileRow) {
      const { data: byId } = await supabase
        .from("profiles")
        .select("user_id, daily_post_limit, total_posts_count, total_post_limit")
        .eq("id", uid)
        .maybeSingle();
      if (byId) setProfile(byId as Profile);
    } else {
      setProfile(profileRow as Profile);
    }

    const { data: tasks } = await supabase
      .from("post_tasks")
      .select("id, keyword, status, created_at, updated_at, published_url, assigned_vm_name")
      .eq("user_id", uid)
      .order("created_at", { ascending: false })
      .limit(500);

    setPostTasks((tasks ?? []) as PostTask[]);
    setPostTasksPage(1);
    setLoading(false);
  };

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (postTasksPage > postTasksTotalPages) setPostTasksPage(1);
  }, [postTasksPage, postTasksTotalPages]);

  if (loading) {
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
      <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">작업내역</h1>

      {/* KPI 4개: 오늘완료, 대기중, 전체남은수량, 완료예상일 (잔액 없음) */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
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
            <CardTitle className="text-sm font-medium text-zinc-500">전체 남은 수량</CardTitle>
            <Package className="size-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{remainingPosts.toLocaleString()}개</div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl border shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-zinc-500">완료 예상일</CardTitle>
            <Calendar className="size-4 text-zinc-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{expectedEndDateText}</div>
            {dailyLimit > 0 && remainingPosts > 0 && (
              <p className="text-xs text-zinc-500 mt-1">
                하루 {dailyLimit}개 × {daysNeeded}일
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 작업목록 */}
      <Card className="rounded-2xl border shadow-sm">
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>작업목록</CardTitle>
          </div>
          <Button variant="outline" size="default" onClick={loadAll} disabled={loading}>
            새로고침
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
          {postTasks.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="아직 작업이 없어요"
              description="대시보드에서 발행 시작 버튼을 눌러 작업을 등록해보세요."
            />
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="cursor-pointer hover:bg-zinc-100" onClick={() => handlePostTasksSort("keyword")}>
                      키워드 {postTasksSortKey === "keyword" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-zinc-100" onClick={() => handlePostTasksSort("status")}>
                      현재작업상황 {postTasksSortKey === "status" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-zinc-100" onClick={() => handlePostTasksSort("assigned_vm_name")}>
                      담당VM {postTasksSortKey === "assigned_vm_name" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-zinc-100" onClick={() => handlePostTasksSort("created_at")}>
                      등록일 {postTasksSortKey === "created_at" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-zinc-100" onClick={() => handlePostTasksSort("updated_at")}>
                      완료일 {postTasksSortKey === "updated_at" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-zinc-100" onClick={() => handlePostTasksSort("published_url")}>
                      작업링크 {postTasksSortKey === "published_url" && (postTasksSortAsc ? "↑" : "↓")}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {postTasksPaginated.map((t) => (
                    <TableRow key={t.id} className="cursor-pointer" onClick={() => setSelectedTask(t)}>
                      <TableCell className="font-medium">{t.keyword || "-"}</TableCell>
                      <TableCell>
                        <StatusBadge status={t.status} />
                      </TableCell>
                      <TableCell className="text-zinc-600">{t.assigned_vm_name || "-"}</TableCell>
                      <TableCell className="text-zinc-600">{new Date(t.created_at).toLocaleString("ko-KR")}</TableCell>
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
                    <span className="font-medium text-zinc-500">완료일</span>
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
    </div>
  );
}
