-- ============================================================
-- 검색 기반 카페 가입 흐름 (run_cafe_join_job) — Supabase 설정
-- section.cafe.naver.com 키워드 검색 → 정책 확인 → 가입 → agent_cafe_lists 저장
-- Supabase SQL Editor에서 실행
--
-- 전제: is_admin() RPC가 이미 존재해야 함 (어드민 페이지에서 사용 중)
-- ============================================================

-- 1. cafe_join_policy 테이블 (없으면 생성, 컬럼 보강)
CREATE TABLE IF NOT EXISTS cafe_join_policy (
    id              INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    run_days        INTEGER[] DEFAULT '{4,14,24}',
    start_time      TEXT DEFAULT '09:00',
    created_year_min INTEGER DEFAULT 2020,
    created_year_max INTEGER DEFAULT 2025,
    recent_post_days INTEGER DEFAULT 7,
    recent_post_enabled BOOLEAN DEFAULT TRUE,
    target_count    INTEGER DEFAULT 50,
    search_keyword  TEXT DEFAULT '',
    updated_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE cafe_join_policy ADD COLUMN IF NOT EXISTS search_keyword TEXT DEFAULT '';
ALTER TABLE cafe_join_policy ADD COLUMN IF NOT EXISTS start_time TEXT DEFAULT '09:00';

INSERT INTO cafe_join_policy (id, run_days, created_year_min, created_year_max, recent_post_days, recent_post_enabled, target_count, search_keyword)
VALUES (1, ARRAY[4,14,24], 2020, 2025, 7, TRUE, 50, '')
ON CONFLICT (id) DO NOTHING;

-- 2. agent_cafe_lists 테이블 (가입 결과 저장)
CREATE TABLE IF NOT EXISTS agent_cafe_lists (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    owner_user_id   UUID,
    program_username TEXT NOT NULL,
    cafe_url        TEXT NOT NULL,
    cafe_id         TEXT,
    menu_id         TEXT,
    status          TEXT NOT NULL DEFAULT 'saved' CHECK (status IN ('saved','joined','rejected')),
    reject_reason   TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE agent_cafe_lists ADD COLUMN IF NOT EXISTS reject_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_agent_cafe_lists_username ON agent_cafe_lists(program_username);
CREATE INDEX IF NOT EXISTS idx_agent_cafe_lists_status ON agent_cafe_lists(program_username, status);

-- 3. RLS: cafe_join_policy — 관리자만 읽기/쓰기
-- is_admin() 함수가 Supabase에 있어야 함. (어드민 페이지에서 이미 사용 중)
ALTER TABLE cafe_join_policy ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin only cafe_join_policy" ON cafe_join_policy;
CREATE POLICY "Admin only cafe_join_policy" ON cafe_join_policy
  FOR ALL USING (COALESCE((SELECT is_admin()), false));

-- 4. RPC: 관리자 전용 카페 가입 정책 조회/저장
-- is_admin RPC가 이미 있다고 가정. 없으면 먼저 생성 필요.

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
    'search_keyword', COALESCE(r.search_keyword, '')
  );
END;
$$;

CREATE OR REPLACE FUNCTION admin_upsert_cafe_join_policy(
  p_run_days INTEGER[] DEFAULT NULL,
  p_start_time TEXT DEFAULT NULL,
  p_created_year_min INTEGER DEFAULT NULL,
  p_created_year_max INTEGER DEFAULT NULL,
  p_recent_post_days INTEGER DEFAULT NULL,
  p_recent_post_enabled BOOLEAN DEFAULT NULL,
  p_target_count INTEGER DEFAULT NULL,
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
    recent_post_days, recent_post_enabled, target_count, search_keyword, updated_at
  ) VALUES (
    1,
    CASE WHEN p_run_days IS NULL OR array_length(p_run_days, 1) IS NULL THEN ARRAY[4,14,24] ELSE p_run_days END,
    COALESCE(NULLIF(TRIM(p_start_time), ''), '09:00'),
    COALESCE(p_created_year_min, 2020),
    COALESCE(p_created_year_max, 2025),
    COALESCE(p_recent_post_days, 7),
    COALESCE(p_recent_post_enabled, true),
    COALESCE(p_target_count, 50),
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
    search_keyword = COALESCE(EXCLUDED.search_keyword, cafe_join_policy.search_keyword),
    updated_at = now();
END;
$$;

-- 5. agent_cafe_lists RLS (워커/GUI는 service_role 사용 — RLS 우회)
-- 일반 유저는 본인 데이터만 조회 가능하도록 할 수 있음 (선택)
-- 현재 run_cafe_join_job은 service_role로 insert하므로 RLS 비활성화 또는 service_role 사용 유지
ALTER TABLE agent_cafe_lists ENABLE ROW LEVEL SECURITY;
-- 워커가 service_role 사용 시 RLS 우회됨. anon 접근 차단용 기본 정책
DROP POLICY IF EXISTS "Deny anon agent_cafe_lists" ON agent_cafe_lists;
CREATE POLICY "Deny anon agent_cafe_lists" ON agent_cafe_lists
  FOR ALL USING (false);  -- anon은 접근 불가. service_role만 접근
