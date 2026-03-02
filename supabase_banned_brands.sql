-- ============================================================
-- banned_brands 테이블 (쿠팡 활동금지 업체/브랜드)
-- ============================================================
-- Supabase SQL Editor에서 실행하세요.
-- 키워드에 금지 브랜드가 포함되면 해당 키워드로 포스팅하지 않습니다.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.banned_brands (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    brand_name  TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE banned_brands ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon read banned_brands" ON banned_brands;
CREATE POLICY "Allow anon read banned_brands" ON banned_brands FOR SELECT USING (true);

-- 활동금지 브랜드 등록 예시 (선택):
-- INSERT INTO banned_brands (brand_name) VALUES ('락토핏'), ('종근당'), ('업체명')
-- ON CONFLICT (brand_name) DO NOTHING;
