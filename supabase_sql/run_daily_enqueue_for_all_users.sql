-- ============================================================
-- 매일 자동 enqueue: 전체 남은 발행량을 채울 때까지
-- ============================================================
-- 남은 발행이 있는 모든 유저에게 매일 하루분(post_tasks) 자동 등록
-- Supabase SQL Editor에서 1) 실행 후, 2) 또는 3) 중 하나 선택
-- ============================================================

-- 1) run_daily_enqueue_for_all_users: 남은 발행이 있는 모든 유저에게 하루분 enqueue
CREATE OR REPLACE FUNCTION public.run_daily_enqueue_for_all_users()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  r RECORD;
  v_remaining INT;
  v_count INT;
  v_cost INT;
  v_result JSONB;
  v_total_inserted INT := 0;
  v_users_processed INT := 0;
BEGIN
  FOR r IN
    SELECT
      p.user_id,
      COALESCE(p.daily_post_limit, 0)::INT AS daily_limit,
      COALESCE(p.total_post_limit, 0)::INT AS total_limit,
      COALESCE(p.total_posts_count, 0)::INT AS posts_done,
      COALESCE(p.cost_per_post, 70)::INT AS cost_val
    FROM profiles p
    WHERE COALESCE(p.daily_post_limit, 0) > 0
      AND COALESCE(p.total_post_limit, 0) > COALESCE(p.total_posts_count, 0)
      AND p.coupang_access_key IS NOT NULL AND TRIM(p.coupang_access_key) != ''
      AND p.coupang_secret_key IS NOT NULL AND TRIM(p.coupang_secret_key) != ''
  LOOP
    v_remaining := r.total_limit - r.posts_done;
    v_count := LEAST(r.daily_limit, v_remaining);
    v_cost := r.cost_val;

    IF v_count > 0 THEN
      v_result := enqueue_post_tasks_paid(
        r.user_id,
        'cafe',
        v_count,
        v_cost,
        '{}'::JSONB
      );
      v_total_inserted := v_total_inserted + COALESCE((v_result->>'inserted')::INT, 0);
      v_users_processed := v_users_processed + 1;
    END IF;
  END LOOP;

  RETURN jsonb_build_object(
    'ok', true,
    'users_processed', v_users_processed,
    'total_inserted', v_total_inserted,
    'message', v_users_processed || '명 유저, ' || v_total_inserted || '개 작업 등록'
  );
END;
$$;

-- 2) pg_cron 스케줄 (매일 UTC 00:00 = 한국시간 09:00)
-- Supabase Dashboard → Database → Extensions → pg_cron 활성화 후 아래 실행
-- SELECT cron.schedule(
--   'daily-enqueue-post-tasks',
--   '0 0 * * *',
--   $$SELECT run_daily_enqueue_for_all_users()$$
-- );

-- 3) pg_cron 없을 때: API /api/cron/daily-enqueue 사용
--    - Vercel: vercel.json에 cron 설정됨. SUPABASE_SERVICE_ROLE_KEY 필요
--    - 외부 cron: cron-job.org 등에서 GET https://도메인/api/cron/daily-enqueue
--      Header: Authorization: Bearer CRON_SECRET (CRON_SECRET 설정 시)
