-- ============================================================
-- enqueue_post_tasks_paid RPC
-- ============================================================
-- 하루 발행 개수만큼 post_tasks에 등록
-- 키워드: user_keywords 우선 → 없으면 admin_keywords
-- ============================================================

-- post_tasks 테이블이 없다면 먼저 생성 (예시 스키마)
-- CREATE TABLE IF NOT EXISTS post_tasks (
--   id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
--   user_id UUID NOT NULL,
--   platform TEXT DEFAULT 'cafe',
--   channel TEXT DEFAULT 'cafe',
--   status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'done', 'failed')),
--   keyword TEXT,
--   published_url TEXT,
--   payload JSONB DEFAULT '{}',
--   cost INTEGER DEFAULT 0,
--   created_at TIMESTAMPTZ DEFAULT now()
-- );

CREATE OR REPLACE FUNCTION enqueue_post_tasks_paid(
  p_user_id UUID,
  p_channel TEXT DEFAULT 'cafe',
  p_count INTEGER DEFAULT 1,
  p_cost INTEGER DEFAULT 0,
  p_payload JSONB DEFAULT '{}'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_keywords TEXT[] := '{}';
  v_kw TEXT;
  v_i INT := 0;
  v_inserted INT := 0;
  v_user_kws TEXT[];
  v_admin_kws TEXT[];
  v_ak TEXT;
  v_sk TEXT;
BEGIN
  -- 0) 쿠팡키 미등록 시 태스크 등록 불가 (profiles.user_id = auth.users.id)
  SELECT coupang_access_key, coupang_secret_key INTO v_ak, v_sk
  FROM profiles WHERE user_id = p_user_id LIMIT 1;
  IF v_ak IS NULL OR TRIM(v_ak) = '' OR v_sk IS NULL OR TRIM(v_sk) = '' THEN
    RETURN jsonb_build_object('inserted', 0, 'message', '쿠팡파트너스 키를 등록후 진행하세요.');
  END IF;

  -- 1) user_keywords에서 키워드 가져오기
  SELECT ARRAY_AGG(keyword ORDER BY RANDOM())
  INTO v_user_kws
  FROM (
    SELECT keyword FROM user_keywords
    WHERE user_id = p_user_id AND (keyword IS NOT NULL AND TRIM(keyword) != '')
    LIMIT p_count * 2
  ) t;

  -- 2) user_keywords가 있으면 사용, 없으면 admin_keywords
  IF v_user_kws IS NOT NULL AND array_length(v_user_kws, 1) > 0 THEN
    v_keywords := v_user_kws;
  ELSE
    SELECT ARRAY_AGG(keyword ORDER BY RANDOM())
    INTO v_admin_kws
    FROM (
      SELECT keyword FROM admin_keywords
      WHERE keyword IS NOT NULL AND TRIM(keyword) != ''
      LIMIT p_count * 2
    ) t;
    IF v_admin_kws IS NOT NULL AND array_length(v_admin_kws, 1) > 0 THEN
      v_keywords := v_admin_kws;
    END IF;
  END IF;

  -- 3) 키워드가 없으면 빈 키워드로라도 작업 생성 (또는 0개 반환)
  IF array_length(v_keywords, 1) IS NULL OR array_length(v_keywords, 1) = 0 THEN
    RETURN jsonb_build_object('inserted', 0, 'message', '키워드가 없습니다. user_keywords 또는 admin_keywords를 등록해주세요.');
  END IF;

  -- 4) p_count만큼 post_tasks에 insert (키워드 순환 사용)
  FOR v_i IN 1..p_count LOOP
    v_kw := v_keywords[1 + ((v_i - 1) % array_length(v_keywords, 1))];

    INSERT INTO post_tasks (user_id, platform, channel, status, keyword, payload, cost)
    VALUES (
      p_user_id,
      COALESCE(p_channel, 'cafe'),
      COALESCE(p_channel, 'cafe'),
      'pending',
      v_kw,
      COALESCE(p_payload, '{}'::jsonb),
      COALESCE(p_cost, 0)
    );
    v_inserted := v_inserted + 1;
  END LOOP;

  RETURN jsonb_build_object('inserted', v_inserted, 'message', v_inserted || '개 작업 등록 완료');
END;
$$;

-- published_url 컬럼 추가 (기존 post_tasks 테이블용)
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS published_url TEXT;

-- updated_at 컬럼 추가 (작업 완료 시각 표시용)
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- assigned_vm_name: 선점한 VM 이름 (다중 VM 중복 방지·할당 추적)
ALTER TABLE post_tasks ADD COLUMN IF NOT EXISTS assigned_vm_name TEXT;

-- RLS: 사용자가 본인 post_tasks 조회 가능 (대시보드용)
-- DROP POLICY IF EXISTS "Users can read own post_tasks" ON post_tasks;
-- CREATE POLICY "Users can read own post_tasks" ON post_tasks
--   FOR SELECT USING (auth.uid() = user_id);
