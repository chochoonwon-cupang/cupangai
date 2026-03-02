-- ============================================================
-- agent_cafe_lists + cafe_join_policy — Supabase 최소 설정
-- 검색 기반 카페 가입 → agent_cafe_lists 저장 → 글작성에 사용
-- Supabase Dashboard → SQL Editor에서 실행
-- ============================================================

-- 1. cafe_join_policy (검색 기반 가입 정책)
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

INSERT INTO cafe_join_policy (id, run_days, created_year_min, created_year_max, recent_post_days, recent_post_enabled, target_count, search_keyword)
VALUES (1, ARRAY[4,14,24], 2020, 2025, 7, TRUE, 50, '')
ON CONFLICT (id) DO NOTHING;

-- 2. agent_cafe_lists (가입 결과 저장, 글작성 시 사용)
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

CREATE INDEX IF NOT EXISTS idx_agent_cafe_lists_username ON agent_cafe_lists(program_username);
CREATE INDEX IF NOT EXISTS idx_agent_cafe_lists_status ON agent_cafe_lists(program_username, status);

-- 3. RLS: 워커/GUI는 service_role 사용 → RLS 우회됨. anon 접근만 차단.
ALTER TABLE agent_cafe_lists ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Deny anon agent_cafe_lists" ON agent_cafe_lists;
CREATE POLICY "Deny anon agent_cafe_lists" ON agent_cafe_lists FOR ALL USING (false);
