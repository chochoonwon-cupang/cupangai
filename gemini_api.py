# ============================================================
# Gemini API 연동 모듈
# ============================================================
# Google Gemini API를 사용하여 상품 정보를 바탕으로
# 카테고리별 다른 구조로 게시글 생성
# - 건강식품 / 생활용품 / 가전제품 / 유아출산 / 기타
# ============================================================

import random
import re
import requests
import json

from config import GEMINI_API_KEY

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"

CATEGORIES = ["건강식품", "생활용품", "가전제품", "유아/출산", "기타"]


# ─────────────────────────────────────────────────────────────
# length_mode: short / medium
# ─────────────────────────────────────────────────────────────
LENGTH_MODES = ["short", "medium"]

# short: 3~4문단, 핵심 2가지, 가격 가볍게, 800~1200자
# medium: 5~7문단, 특징+장점 3가지, 추천대상, 가격, 1500~2200자
LENGTH_MODE_RULES = {
    "short": """
[분량 모드: short - 짧고 핵심 위주]
- 도입부: 150~200자 (짧게)
- 전체 문단 수: 3~4개
- 핵심 특징 2가지 정도만
- 가격은 가볍게 언급
- 총 분량: 800~1200자
- 이미지 1장 기준으로 어색하지 않게 구성
- short와 medium은 문단 수·문장 수·정보 깊이가 확실히 다르게 느껴지도록
""",
    "medium": """
[분량 모드: medium - 충실한 정보형]
- 도입부: 250~350자 (충실하게)
- 전체 문단 수: 5~7개
- 특징 + 장점 3가지
- 추천 대상 포함
- 가격 언급
- 총 분량: 1500~2200자
- 이미지 1장 기준 자연스러운 분량
- short와 medium은 문단 수·문장 수·정보 깊이가 확실히 다르게 느껴지도록
""",
}


# ─────────────────────────────────────────────────────────────
# 카테고리별 프롬프트 생성
# ─────────────────────────────────────────────────────────────
def _get_category_prompt(category, keyword, items_text, length_mode="medium"):
    """카테고리별 + length_mode별 Gemini 프롬프트 반환"""
    length_rules = LENGTH_MODE_RULES.get(length_mode, LENGTH_MODE_RULES["medium"])

    base_rules = """
- 상업적 문구 과도 사용 금지, 구매 강요 금지.
- 자연스러운 정보형 문체 (~해요, ~이더라고요).
- 절대 * 문자(별표)를 사용하지 마세요. 마크다운 서식 금지.
- [파트 A], [파트 B], ## 파트 A, ## 파트 B, 상품별 요약, 건강식품 형식, 공감형 도입 등 작성 지침/구조 표시를 본문에 절대 포함하지 마세요. 이는 구조 안내일 뿐 출력하면 안 됩니다.
- 문단 사이 줄바꿈은 1~3줄 랜덤 적용.
- 가독성: 주요 단락·소제목 앞에 반드시 ✅ 이모티콘을 붙이세요. 예) ✅ 오늘의 추천 상품: {상품명}
- 가격·혜택: 가격(예: 12,000원), 로켓배송, 무료배송 등 핵심 정보는 문장 내에서 구분되게 작성.
- 색상 남용 금지: 소제목과 핵심 가격/혜택에만 강조를 두세요.
"""
    base_rules += length_rules

    prompts = {
        "건강식품": f"""당신은 네이버 카페 블로그 전문 리뷰어입니다.
발행 카테고리: 건강식품
검색 키워드 "{keyword}"에 대해 작성해주세요.
{base_rules}

[파트 A: 공감형 도입]
- "{keyword}"를 검색하는 분들이 공감할 만한 고민·상황을 묘사하세요.
- 블로그 말투로 친근하게 작성하세요.
---도입부---
(도입부 문구)

[파트 B: 상품별 요약 - 건강식품 형식]
각 상품마다: 성분/특징, 추천대상, 가격 언급. length_mode에 맞게 분량 조절.
---상품1---
(요약)
---상품2---
(요약)
...

[상품 목록]
{items_text}
""",
        "생활용품": f"""당신은 네이버 카페 블로그 전문 리뷰어입니다.
발행 카테고리: 생활용품
검색 키워드 "{keyword}"에 대해 작성해주세요.
{base_rules}

[파트 A: 불편했던 상황 제시]
- 사용 전 불편했던 상황을 공감적으로 묘사하세요.
---도입부---
(도입부 문구)

[파트 B: 상품별 요약 - 생활용품 형식]
각 상품마다: 발견계기, 사용감, 장점, 가격. length_mode에 맞게 분량 조절.
---상품1---
(요약)
---상품2---
(요약)
...

[상품 목록]
{items_text}
""",
        "가전제품": f"""당신은 네이버 카페 블로그 전문 리뷰어입니다.
발행 카테고리: 가전제품
검색 키워드 "{keyword}"에 대해 작성해주세요.
{base_rules}

[파트 A: 기존 제품과 비교 도입]
- 기존 제품의 불편함 또는 새 제품을 찾게 된 계기를 묘사하세요.
---도입부---
(도입부 문구)

[파트 B: 상품별 요약 - 가전제품 형식]
각 상품마다: 스펙, 장단점, 추천대상, 가격대. length_mode에 맞게 분량 조절.
---상품1---
(요약)
---상품2---
(요약)
...

[상품 목록]
{items_text}
""",
        "유아/출산": f"""당신은 네이버 카페 블로그 전문 리뷰어입니다.
발행 카테고리: 유아/출산
검색 키워드 "{keyword}"에 대해 작성해주세요.
{base_rules}

[파트 A: 안전성 강조 도입]
- 아이에게 쓰는 제품에 대한 부모님들의 걱정을 공감하세요.
---도입부---
(도입부 문구)

[파트 B: 상품별 요약 - 유아/출산 형식]
각 상품마다: 소재/성분, 부모 후기 느낌. 조심스러운 마무리. length_mode에 맞게 분량 조절.
---상품1---
(요약)
---상품2---
(요약)
...

[상품 목록]
{items_text}
""",
        "기타": f"""당신은 네이버 카페 블로그 전문 리뷰어입니다.
발행 카테고리: 기타
검색 키워드 "{keyword}"에 대해 작성해주세요.
{base_rules}

[파트 A: 제품 소개 도입]
- "{keyword}"에 대해 일반적인 소개를 하세요.
---도입부---
(도입부 문구)

[파트 B: 상품별 요약 - 기타 형식]
각 상품마다: 특징 3가지, 활용 방법. length_mode에 맞게 분량 조절.
---상품1---
(요약)
---상품2---
(요약)
...

[상품 목록]
{items_text}
""",
    }
    return prompts.get(category, prompts["기타"])


# ─────────────────────────────────────────────────────────────
# 제목 템플릿 (포스팅마다 랜덤 선택)
# ─────────────────────────────────────────────────────────────
TITLE_TEMPLATES = [
    "[추천] 요즘 난리 난 {keyword} 직접 써보니 다르네요!",
    "{keyword} 가성비 실화? 솔직 리뷰 공유합니다",
    "품절주의! {keyword} 비교 분석해봤어요",
    "🔥 {keyword} 베스트 추천 TOP{count} 총정리",
    "{keyword} 고민이라면 이 글 하나로 해결!",
    "요즘 핫한 {keyword}, 안 사면 후회할걸요?",
    "✨ {keyword} 어떤 게 좋을까? 꼼꼼 비교 리뷰",
    "{keyword} 추천 리스트 | 진짜 써본 사람의 후기",
    "가성비 갑! {keyword} 이건 꼭 알아야 해요",
    "직접 비교해봤습니다 - {keyword} 최종 추천 🏆",
]


def _pick_random_title(keyword, product_count):
    """제목 템플릿에서 랜덤 선택 후 키워드와 상품 수를 채운다."""
    template = random.choice(TITLE_TEMPLATES)
    return template.format(keyword=keyword, count=product_count)


# ─────────────────────────────────────────────────────────────
# 통합 Gemini 호출: 도입부 + 상품별 요약 (카테고리별 프롬프트)
# ─────────────────────────────────────────────────────────────
def generate_intro_and_summaries(products, keyword, category="건강식품", length_mode="medium", gemini_api_key=None):
    """
    한 번의 Gemini API 호출로:
      1) 카테고리에 맞는 도입부
      2) 각 상품별 요약 (카테고리별 구조)
    를 동시에 받아온다.

    Returns:
        (intro_text, {index: summary_text}) 튜플
    """
    gemini_api_key = gemini_api_key or GEMINI_API_KEY

    # 상품 목록 텍스트 구성
    items_text = ""
    for i, p in enumerate(products, 1):
        name = p.get("productName", "")
        prod_cat = p.get("categoryName", "일반")
        price_str = (
            f"{p['productPrice']:,}원"
            if isinstance(p.get("productPrice"), (int, float))
            else str(p.get("productPrice", ""))
        )
        rocket = " [로켓배송]" if p.get("isRocket") else ""
        free_ship = " [무료배송]" if p.get("isFreeShipping") else ""

        items_text += (
            f"[상품 {i}]\n"
            f"  상품명: {name}\n"
            f"  카테고리: {prod_cat}\n"
            f"  가격: {price_str}{rocket}{free_ship}\n\n"
        )

    prompt = _get_category_prompt(category, keyword, items_text, length_mode)

    url = f"{GEMINI_API_URL}?key={gemini_api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 3000,
        },
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            url, headers=headers, json=payload, timeout=45,
            proxies={"http": None, "https": None},
        )
        response.raise_for_status()

        result = response.json()
        text = (
            result
            .get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if not text:
            print("[경고] Gemini 응답이 비어 있습니다.")
            return _fallback_intro(keyword), _fallback_summaries(products)

        # 파싱
        intro = _parse_intro(text, keyword)
        summaries = _parse_summaries(text, len(products))

        print(f"[완료] Gemini 통합 생성 완료 [{category}/{length_mode}] — 도입부: {len(intro)}자, "
              f"요약: {len(summaries)}개")
        return intro, summaries

    except requests.RequestException as e:
        print(f"[오류] Gemini API 호출 실패: {e}")
        return _fallback_intro(keyword), _fallback_summaries(products)


# ─────────────────────────────────────────────────────────────
# 파싱 함수들
# ─────────────────────────────────────────────────────────────
def _parse_intro(text, keyword):
    """Gemini 응답에서 ---도입부--- 섹션을 추출한다."""
    match = re.search(r'---\s*도입부\s*---\s*\n(.*?)(?=---\s*상품\s*\d|$)', text, re.DOTALL)
    if match:
        intro = match.group(1).strip()
        if intro:
            return intro
    return _fallback_intro(keyword)


def _parse_summaries(text, count):
    """Gemini 응답에서 ---상품N--- 구분자로 분리하여 요약을 추출한다."""
    summaries = {}
    parts = re.split(r'---\s*상품\s*(\d+)\s*---', text)

    for i in range(1, len(parts) - 1, 2):
        try:
            idx = int(parts[i]) - 1
            summary = parts[i + 1].strip()
            # 다음 섹션 시작 전까지만 (혹시 남은 텍스트 제거)
            summary = re.split(r'---\s*(?:상품|도입부)\s*', summary)[0].strip()
            if summary:
                summaries[idx] = summary
        except (ValueError, IndexError):
            continue

    if not summaries and text.strip():
        summaries[0] = text.strip()

    return summaries


# ─────────────────────────────────────────────────────────────
# Fallback 함수들 (Gemini 실패 시)
# ─────────────────────────────────────────────────────────────
def _fallback_intro(keyword):
    intros = [
        f"요즘 {keyword} 때문에 고민이 많으시죠? 😊 종류도 너무 많고, 가격도 천차만별이라 "
        f"뭘 골라야 할지 막막하더라고요. 저도 한참 비교하다가 결국 직접 정리해봤어요! "
        f"오늘 제가 꼼꼼하게 비교해본 결과를 공유해드릴게요 ✨",
        f"{keyword} 추천 제품을 찾고 계신가요? 저도 얼마 전 같은 고민을 했었는데요, "
        f"이것저것 알아보면서 정말 괜찮은 제품들을 발견했어요! "
        f"시간 절약하실 수 있도록 핵심만 정리해봤으니 끝까지 읽어주세요 💕",
    ]
    return random.choice(intros)


def _fallback_summaries(products):
    summaries = {}
    for i, p in enumerate(products):
        name = p.get("productName", "상품")
        category = p.get("categoryName", "")
        tags = []
        if p.get("isRocket"):
            tags.append("로켓배송 지원")
        if p.get("isFreeShipping"):
            tags.append("무료배송")
        tag_str = ", ".join(tags) if tags else "합리적인 가격"

        summaries[i] = (
            f"✨ {name[:20]}... 제품을 분석해봤어요! "
            f"{category} 카테고리에서 인기 있는 이유가 있더라고요. "
            f"{tag_str}까지 지원해서 가성비가 정말 좋아요. "
            f"꼼꼼하게 비교해보시는 분들께 추천드려요! 😊"
        )
    return summaries


def _random_closing(keyword):
    """키워드를 포함한 자연스러운 마무리 문구를 랜덤 생성"""
    templates = [
        f"{keyword} 구매 정보는 댓글에 함께 남겨놓을게요~",
        f"도움이 되셨다면 좋아요 눌러주세요 :) {keyword} 구매처는 댓글 참고해주세요!",
        f"필요하신 분들을 위해 {keyword} 구매 링크는 댓글에 정리해두었어요~",
        f"{keyword} 관련 구매 정보가 궁금하시면 댓글 확인해주세요 😊",
        f"{keyword} 구매처는 댓글에 올려놓았으니 참고하세요~",
        f"혹시 {keyword} 구매가 필요하시면 댓글에 링크 남겨두었어요!",
        f"{keyword} 구매 링크 댓글에 정리해놓았으니 편하게 확인하세요~",
        f"참고가 되셨으면 좋겠어요! {keyword} 구매처는 댓글에 있어요 :)",
        f"궁금하신 분들은 댓글 확인해주세요~ {keyword} 정보 정리해두었습니다!",
        f"{keyword} 직접 보고 싶으신 분들은 댓글에 링크 남겨놓았어요~",
    ]
    return random.choice(templates)


# ─────────────────────────────────────────────────────────────
# 가독성 스타일: 가격·혜택 강조 마커
# ─────────────────────────────────────────────────────────────
def _apply_highlight_markers(body):
    """
    가격 등 핵심 정보에 [C]...[/C] 마커를 적용.
    write_cafe_post에서 파란색(#0000FF)으로 렌더링.
    """
    # 가격 패턴: 12,000원, 1,234,567원
    body = re.sub(r'(\d{1,3}(?:,\d{3})*원)', r'[C]\1[/C]', body)
    return body


# ─────────────────────────────────────────────────────────────
# 키워드 랜덤 반복 삽입
# ─────────────────────────────────────────────────────────────
def _insert_keyword_naturally(body, keyword, repeat_min=3, repeat_max=7):
    """
    본문 중간중간 자연스러운 위치에 키워드를 랜덤 횟수만큼 삽입한다.
    - 빈 줄 직후의 텍스트 줄에 키워드를 앞·뒤에 자연스럽게 붙인다.
    - 이미 키워드가 있는 줄은 건너뛴다.
    """
    if repeat_min <= 0 and repeat_max <= 0:
        return body

    target_count = random.randint(max(1, repeat_min), max(1, repeat_max))

    # 키워드를 삽입할 수 있는 자연스러운 문구들
    keyword_phrases = [
        f"{keyword} 관련해서 말씀드리면,",
        f"특히 {keyword}을(를) 찾는 분들은",
        f"{keyword} 선택 시 참고하세요!",
        f"역시 {keyword}은(는)",
        f"{keyword} 비교 포인트로 보면,",
        f"인기 {keyword} 중에서도",
        f"{keyword} 고민이라면 참고하세요 👉",
    ]

    lines = body.split("\n")
    # 삽입 가능한 위치 찾기: 텍스트가 있는 줄 중 키워드가 없고, 마커/구분선이 아닌 줄
    insertable_indices = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if (
            stripped
            and keyword not in stripped
            and not stripped.startswith(("━", "─", "═", "▶", "📸", "💰", "🛒", "※", "[", "✅"))
            and "go.kdgc.co.kr" not in stripped
            and len(stripped) > 10  # 너무 짧은 줄 제외
        ):
            insertable_indices.append(idx)

    # 삽입할 위치 랜덤 선택
    actual_count = min(target_count, len(insertable_indices))
    if actual_count <= 0:
        return body

    chosen = sorted(random.sample(insertable_indices, actual_count))

    for idx in reversed(chosen):  # 뒤에서부터 삽입 (인덱스 밀림 방지)
        phrase = random.choice(keyword_phrases)
        lines.insert(idx, phrase)

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# 최종 네이버 카페 게시글 조립
# ─────────────────────────────────────────────────────────────
def assemble_final_post(products, keyword, intro, summaries,
                        image_paths=None,
                        keyword_repeat_min=3, keyword_repeat_max=7,
                        use_product_name=False):
    """
    공감 도입부 + Gemini 요약 + 상품 이미지를 조합하여
    네이버 카페용 완성 게시글을 만든다.

    게시글 구조:
      제목: 랜덤 템플릿 선택
      본문:
        - 공감 도입부 (Gemini)
        - 상품별 섹션 (요약 + 이미지)
        - 키워드 자연스러운 반복 삽입
        - 마무리 문구 (키워드 포함, 랜덤)
    """
    # ── 제목 (랜덤 템플릿) ──
    # use_product_name: 검색 키워드 대신 상품명으로 제목 생성
    title_keyword = keyword
    if use_product_name and products:
        names = [p.get("productName", "").strip() for p in products if p.get("productName", "").strip()]
        if names:
            title_keyword = random.choice(names)
    title = _pick_random_title(title_keyword, len(products))

    # ── 본문 구성 ──
    # 구조: 첫 문단(도입) → 대표 이미지 1장 → 줄바꿈 2줄 이상 → 제품정보
    body = ""

    # 1) 공감 도입부 (첫 번째 문단)
    if intro:
        body += f"{intro}\n\n"

    # 2) 대표 이미지 1장 - 첫 문단 바로 아래 고정
    first_name = products[0].get("productName", "") if products else ""
    if image_paths and first_name and first_name in image_paths:
        body += "📸 [상품 이미지]\n\n\n\n"  # 이미지 뒤 줄바꿈 2줄 이상

    # 3) 상품별 섹션 (제품정보만, 이미지 없음)
    for i, p in enumerate(products):
        name = p.get("productName", "")

        if i > 0:
            body += "\n\n"

        body += f"✅ 오늘의 추천 상품: {name}\n\n"

        summary = summaries.get(i, "")
        if summary:
            body += f"{summary}\n\n"

    # 3) 키워드 자연스러운 반복 삽입
    body = _insert_keyword_naturally(
        body, keyword,
        repeat_min=keyword_repeat_min,
        repeat_max=keyword_repeat_max,
    )

    # 4) 마무리
    body += "\n\n"
    body += f"{_random_closing(keyword)}\n"

    # * 문자 제거 (마크다운 서식 잔여물)
    body = body.replace("**", "").replace("*", "")

    # 5) 가독성: 가격·혜택 강조 마커 [C]...[/C] 적용
    body = _apply_highlight_markers(body)

    full_post = f"[제목]\n{title}\n\n[본문]\n{body}"
    return full_post


# ─────────────────────────────────────────────────────────────
# 카테고리별 글 생성 (분기)
# ─────────────────────────────────────────────────────────────
def _generate_post_with_category(products, keyword, category, length_mode, **kwargs):
    """카테고리·length_mode 지정하여 도입부+요약 생성 후 조립"""
    intro, summaries = generate_intro_and_summaries(
        products, keyword, category=category,
        length_mode=length_mode,
        gemini_api_key=kwargs.get("gemini_api_key"),
    )
    return assemble_final_post(
        products, keyword, intro, summaries,
        image_paths=kwargs.get("image_paths"),
        keyword_repeat_min=kwargs.get("keyword_repeat_min", 3),
        keyword_repeat_max=kwargs.get("keyword_repeat_max", 7),
        use_product_name=kwargs.get("use_product_name", False),
    )


def generate_health_post(products, keyword, length_mode, **kwargs):
    """건강식품 카테고리: 공감형 도입, 성분/특징, 추천대상, 가격대"""
    return _generate_post_with_category(products, keyword, "건강식품", length_mode, **kwargs)


def generate_living_post(products, keyword, length_mode, **kwargs):
    """생활용품 카테고리: 불편 상황, 발견계기, 사용감, 장점3가지, 가격"""
    return _generate_post_with_category(products, keyword, "생활용품", length_mode, **kwargs)


def generate_electronics_post(products, keyword, length_mode, **kwargs):
    """가전제품 카테고리: 기존 제품 비교, 스펙, 장단점, 추천대상, 가격대"""
    return _generate_post_with_category(products, keyword, "가전제품", length_mode, **kwargs)


def generate_baby_post(products, keyword, length_mode, **kwargs):
    """유아/출산 카테고리: 안전성 도입, 소재/성분, 부모 후기 느낌"""
    return _generate_post_with_category(products, keyword, "유아/출산", length_mode, **kwargs)


def generate_etc_post(products, keyword, length_mode, **kwargs):
    """기타 카테고리: 제품 소개, 특징 3가지, 활용 방법"""
    return _generate_post_with_category(products, keyword, "기타", length_mode, **kwargs)


def generate_post(products, keyword, category, length_mode, **kwargs):
    """
    카테고리·length_mode 기반으로 해당 전용 생성 함수로 분기.

    Args:
        products: 상품 리스트
        keyword: 검색 키워드
        category: 발행 카테고리
        length_mode: short | medium

    Returns:
        완성된 게시글 문자열
    """
    if category == "건강식품":
        return generate_health_post(products, keyword, length_mode, **kwargs)
    elif category == "생활용품":
        return generate_living_post(products, keyword, length_mode, **kwargs)
    elif category == "가전제품":
        return generate_electronics_post(products, keyword, length_mode, **kwargs)
    elif category == "유아/출산":
        return generate_baby_post(products, keyword, length_mode, **kwargs)
    else:
        return generate_etc_post(products, keyword, length_mode, **kwargs)


# ─────────────────────────────────────────────────────────────
# 메인 진입점: generate_promo_post (기존 인터페이스 유지 + 확장)
# ─────────────────────────────────────────────────────────────
def generate_promo_post(products, keyword, gemini_api_key=None, image_paths=None,
                        keyword_repeat_min=3, keyword_repeat_max=7,
                        use_product_name=False, category="건강식품"):
    """
    전체 게시글 생성 파이프라인.
    category에 따라 카테고리별 템플릿으로 생성합니다.

    Args:
        products: 상품 정보 딕셔너리 리스트
        keyword: 검색 키워드
        gemini_api_key: Gemini API 키
        image_paths: 이미지 경로 딕셔너리 (선택)
        keyword_repeat_min: 키워드 반복 최소 횟수
        keyword_repeat_max: 키워드 반복 최대 횟수
        use_product_name: 제목에 상품명 사용 여부
        category: 발행 카테고리 (건강식품/생활용품/가전제품/유아출산/기타)

    Returns:
        완성된 게시글 문자열
    """
    length_mode = random.choice(LENGTH_MODES)
    print(f"\n[Gemini] 통합 생성 중 (카테고리: {category}, 분량: {length_mode})...")
    post = generate_post(
        products, keyword, category, length_mode,
        gemini_api_key=gemini_api_key,
        image_paths=image_paths,
        keyword_repeat_min=keyword_repeat_min,
        keyword_repeat_max=keyword_repeat_max,
        use_product_name=use_product_name,
    )
    print(f"[완료] 네이버 카페 게시글 생성 완료 [{category}/{length_mode}]")
    return post
