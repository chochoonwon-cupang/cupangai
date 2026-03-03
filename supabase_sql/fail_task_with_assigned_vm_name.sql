-- ============================================================
-- fail_task RPC — assigned_vm_name으로 매칭
-- ============================================================
-- finish_task와 동일하게 assigned_vm_name 사용
-- RPC 시그니처: fail_task(p_vm_name text, p_task_id uuid, p_error text, p_last_step text) -> void
-- ============================================================
-- 적용: Supabase SQL Editor에서 전체 복사 후 Run 실행
-- ============================================================

-- 필요한 컬럼 추가 (없으면)
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS last_step TEXT;
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ;
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

CREATE OR REPLACE FUNCTION public.fail_task(
  p_vm_name TEXT,
  p_task_id UUID,
  p_error TEXT DEFAULT '',
  p_last_step TEXT DEFAULT ''
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE public.post_tasks
  SET
    status = 'failed',
    error_message = p_error,
    last_step = p_last_step,
    finished_at = now(),
    lease_expires_at = null,
    updated_at = now()
  WHERE id = p_task_id
    AND TRIM(COALESCE(assigned_vm_name, '')) = TRIM(COALESCE(p_vm_name, ''));
END;
$$;
