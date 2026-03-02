-- cafe_join_policy: expire_days 컬럼 추가 (10일 경과 카페 삭제 → 관리자 설정 가능)
-- target_count는 이미 존재. expire_days만 추가.
-- Supabase SQL Editor에서 실행

ALTER TABLE cafe_join_policy ADD COLUMN IF NOT EXISTS expire_days INTEGER DEFAULT 10;

-- 기존 행에 기본값 적용
UPDATE cafe_join_policy SET expire_days = 10 WHERE id = 1 AND expire_days IS NULL;

-- admin_get_cafe_join_policy에 expire_days 추가
CREATE OR REPLACE FUNCTION admin_get_cafe_join_policy()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  r RECORD;
BEGIN
  IF NOT (SELECT is_admin()) THEN
    RAISE EXCEPTION '관리자만 접근 가능합니다.';
  END IF;

  SELECT * INTO r FROM cafe_join_policy WHERE id = 1 LIMIT 1;
  IF r IS NULL THEN
    RETURN jsonb_build_object(
      'run_days', ARRAY[4,14,24],
      'start_time', '09:00',
      'created_year_min', 2020,
      'created_year_max', 2025,
      'recent_post_days', 7,
      'recent_post_enabled', true,
      'target_count', 50,
      'expire_days', 10,
      'search_keyword', ''
    );
  END IF;

  RETURN jsonb_build_object(
    'run_days', COALESCE(r.run_days, ARRAY[4,14,24]),
    'start_time', COALESCE(r.start_time, '09:00'),
    'created_year_min', COALESCE(r.created_year_min, 2020),
    'created_year_max', COALESCE(r.created_year_max, 2025),
    'recent_post_days', COALESCE(r.recent_post_days, 7),
    'recent_post_enabled', COALESCE(r.recent_post_enabled, true),
    'target_count', COALESCE(r.target_count, 50),
    'expire_days', COALESCE(r.expire_days, 10),
    'search_keyword', COALESCE(r.search_keyword, '')
  );
END;
$$;

-- admin_upsert_cafe_join_policy에 p_expire_days 추가
CREATE OR REPLACE FUNCTION admin_upsert_cafe_join_policy(
  p_run_days INTEGER[] DEFAULT NULL,
  p_start_time TEXT DEFAULT NULL,
  p_created_year_min INTEGER DEFAULT NULL,
  p_created_year_max INTEGER DEFAULT NULL,
  p_recent_post_days INTEGER DEFAULT NULL,
  p_recent_post_enabled BOOLEAN DEFAULT NULL,
  p_target_count INTEGER DEFAULT NULL,
  p_expire_days INTEGER DEFAULT NULL,
  p_search_keyword TEXT DEFAULT NULL
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF NOT (SELECT is_admin()) THEN
    RAISE EXCEPTION '관리자만 접근 가능합니다.';
  END IF;

  INSERT INTO cafe_join_policy (
    id, run_days, start_time, created_year_min, created_year_max,
    recent_post_days, recent_post_enabled, target_count, expire_days, search_keyword, updated_at
  ) VALUES (
    1,
    CASE WHEN p_run_days IS NULL OR array_length(p_run_days, 1) IS NULL THEN ARRAY[4,14,24] ELSE p_run_days END,
    COALESCE(NULLIF(TRIM(p_start_time), ''), '09:00'),
    COALESCE(p_created_year_min, 2020),
    COALESCE(p_created_year_max, 2025),
    COALESCE(p_recent_post_days, 7),
    COALESCE(p_recent_post_enabled, true),
    COALESCE(p_target_count, 50),
    COALESCE(p_expire_days, 10),
    COALESCE(NULLIF(TRIM(p_search_keyword), ''), ''),
    now()
  )
  ON CONFLICT (id) DO UPDATE SET
    run_days = COALESCE(EXCLUDED.run_days, cafe_join_policy.run_days),
    start_time = COALESCE(EXCLUDED.start_time, cafe_join_policy.start_time),
    created_year_min = COALESCE(EXCLUDED.created_year_min, cafe_join_policy.created_year_min),
    created_year_max = COALESCE(EXCLUDED.created_year_max, cafe_join_policy.created_year_max),
    recent_post_days = COALESCE(EXCLUDED.recent_post_days, cafe_join_policy.recent_post_days),
    recent_post_enabled = COALESCE(EXCLUDED.recent_post_enabled, cafe_join_policy.recent_post_enabled),
    target_count = COALESCE(EXCLUDED.target_count, cafe_join_policy.target_count),
    expire_days = COALESCE(EXCLUDED.expire_days, cafe_join_policy.expire_days),
    search_keyword = COALESCE(EXCLUDED.search_keyword, cafe_join_policy.search_keyword),
    updated_at = now();
END;
$$;
