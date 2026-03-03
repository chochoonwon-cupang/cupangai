-- ============================================================
-- 잔액 차감 안 될 때 진단용 쿼리
-- ============================================================
-- Supabase SQL Editor에서 아래 쿼리들을 하나씩 실행해보세요.
-- ============================================================

-- 1) 최근 완료(done)된 태스크: cost, user_id 확인 (cost가 0이면 차감 안 됨)
SELECT id, user_id, status, cost, assigned_vm_name, finished_at
FROM post_tasks
WHERE status = 'done'
ORDER BY finished_at DESC NULLS LAST
LIMIT 10;

-- 2) 해당 user_id의 profiles 잔액 확인 (user_id로 매칭)
SELECT p.user_id, p.balance, p.total_charged
FROM profiles p
WHERE p.user_id IN (SELECT user_id FROM post_tasks WHERE status = 'done' LIMIT 5);

-- 3) finish_task 함수 정의 확인 (profiles 업데이트 있는지)
SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'finish_task';
