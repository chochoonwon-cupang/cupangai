-- ============================================================
-- profiles 테이블 (Supabase Auth 연동)
-- ============================================================
-- Supabase SQL Editor에서 실행
-- auth.users.id를 PK로 사용, username/login_id로 이메일 조회 가능
-- ============================================================

-- profiles: auth.users 확장 (id = auth.users.id)
CREATE TABLE IF NOT EXISTS public.profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username        TEXT,
    login_id        TEXT,
    email           TEXT,
    coupang_access_key  TEXT,
    coupang_secret_key   TEXT,
    distribute_keyword   TEXT,
    distribute_category TEXT DEFAULT '기타',
    cost_per_post       INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- username 또는 login_id로 이메일 조회용 인덱스
CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_profiles_login_id ON profiles(login_id) WHERE login_id IS NOT NULL;

-- cost_per_post (기존 테이블에 컬럼 추가)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS cost_per_post INTEGER DEFAULT 0;

-- RLS (service_role은 우회)
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- user_keywords가 user_id로 profiles.id 참조하도록 (선택)
-- 기존 user_keywords.user_id는 UUID이므로 auth.users.id와 호환됨
