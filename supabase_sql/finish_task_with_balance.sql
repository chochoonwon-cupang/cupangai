-- ============================================================
-- finish_task RPC — 작업 완료 + 잔액 차감
-- ============================================================
-- posting_worker가 finish_task(vm_name, task_id, result_url) 호출 시
-- 1) post_tasks: status='done', published_url 저장, finished_at 갱신
-- 2) profiles.balance: 해당 태스크 cost만큼 차감
-- assigned_vm_name으로 매칭 (assigned_vm_id 대신)
-- ============================================================
-- RPC 시그니처: finish_task(p_vm_name text, p_task_id uuid, p_result_url text) -> void
-- ============================================================
-- 적용: Supabase SQL Editor에서 전체 복사 후 Run 실행
-- ============================================================

-- 필요한 컬럼 추가
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS published_url TEXT;
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS assigned_vm_name TEXT;
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ;
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

CREATE OR REPLACE FUNCTION public.finish_task(
  p_vm_name TEXT,
  p_task_id UUID,
  p_result_url TEXT DEFAULT ''
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- task_id로 매칭 (assigned_vm_name 무관). status != 'done' 만 업데이트 + 잔액 차감
  WITH updated AS (
    UPDATE post_tasks
    SET
      status = 'done',
      published_url = COALESCE(NULLIF(TRIM(p_result_url), ''), published_url),
      finished_at = now(),
      updated_at = now()
    WHERE id = p_task_id
      AND status != 'done'
    RETURNING user_id, cost
  )
  UPDATE profiles p
  SET balance = GREATEST(0, COALESCE(p.balance, 0) - COALESCE(u.cost, 0))
  FROM updated u
  WHERE p.user_id = u.user_id
    AND COALESCE(u.cost, 0) > 0;
END;
$$;
