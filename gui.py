# ============================================================
# 쿠팡 파트너스 자동 홍보 봇 - GUI
# ============================================================
# posting_help.py 디자인 시스템 기반 (PySide6 → tkinter 재현)
# ============================================================

import sys
import io

# Windows cp949 콘솔에서 이모지 깨짐 방지 (진입점에서 한 번만 실행)
if sys.stdout and hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '') != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '') != 'utf-8':
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import random
import os
import json
import datetime
import webbrowser

import atexit

# ================================================================
# DESIGN TOKENS  — posting_help.py 완전 일치
# ================================================================
# 배경
BG          = "#eef2f7"
BG_CARD     = "#ffffff"
BG_INPUT    = "#ffffff"
BG_HOVER    = "#f8fafc"
BG_HEADER   = "#f1f5f9"

# 테두리 · 구분선
BD          = "#cbd5e1"
BD_FOCUS    = "#2563eb"
SEP         = "#e2e8f0"

# 텍스트
FG          = "#0f172a"
FG_LABEL    = "#64748b"
FG_DIM      = "#94a3b8"
FG_WHITE    = "#ffffff"

# 포인트 & 버튼
POINT       = "#2563eb"
POINT_H     = "#1d4ed8"
GREEN       = "#22c55e"
GREEN_H     = "#16a34a"
RED         = "#ef4444"
RED_H       = "#dc2626"
ORANGE      = "#f97316"
ORANGE_H    = "#ea580c"
TEAL        = "#14b8a6"
TEAL_H      = "#0d9488"
PURPLE      = "#8b5cf6"
PURPLE_H    = "#7c3aed"

# 로그
LOG_BG      = "#f8fafc"
LOG_FG      = "#111111"

# 폰트 — posting_help.py 10pt 기준 (+1pt 보정)
F           = ("맑은 고딕", 11)
FB          = ("맑은 고딕", 11, "bold")
F_TITLE     = ("맑은 고딕", 14, "bold")
F_SEC       = ("맑은 고딕", 12, "bold")
F_SM        = ("맑은 고딕", 10)
F_SMB       = ("맑은 고딕", 10, "bold")
F_LOG       = ("맑은 고딕", 10)
F_MONO      = ("맑은 고딕", 11)

# 간격
M = 14   # 외곽 margin
S = 12   # spacing
P = 18   # 카드 padding

# 파일 경로 (PyInstaller frozen 시 exe 위치 기준)
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
API_KEYS_FILE = os.path.join(BASE_DIR, ".api_keys.json")
CAFE_SETTINGS_FILE = os.path.join(BASE_DIR, "cafe_settings.json")
GUI_VM_CONFIG = os.path.join(BASE_DIR, "configs", "gui_vm.json")


def _load_gui_vm_config():
    """configs/gui_vm.json 로드 → env 보완. Returns: {VM_NAME, COMM_USER_ID}"""
    out = {"VM_NAME": "", "COMM_USER_ID": ""}
    out["VM_NAME"] = (os.environ.get("VM_NAME") or os.environ.get("WORKER_NAME") or "").strip()
    out["COMM_USER_ID"] = (os.environ.get("COMM_USER_ID") or "").strip()
    try:
        if os.path.isfile(GUI_VM_CONFIG):
            with open(GUI_VM_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
            out["VM_NAME"] = (data.get("VM_NAME") or data.get("vm_name") or out["VM_NAME"] or "").strip()
            out["COMM_USER_ID"] = (data.get("COMM_USER_ID") or data.get("comm_user_id") or out["COMM_USER_ID"] or "").strip()
    except Exception:
        pass
    return out


def _load_gui_vm_name():
    """VM 이름만 반환 (하위 호환)"""
    return _load_gui_vm_config()["VM_NAME"]


# ================================================================
# 공통: 둥근 사각형 좌표 생성
# ================================================================
import tkinter.font as tkfont

def _rr_points(x1, y1, x2, y2, r):
    """smooth polygon용 둥근 사각형 좌표 리스트."""
    return [
        x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1,
        x2, y1, x2, y1+r, x2, y1+r, x2, y2-r,
        x2, y2-r, x2, y2, x2-r, y2, x2-r, y2,
        x1+r, y2, x1+r, y2, x1, y2, x1, y2-r,
        x1, y2-r, x1, y1+r, x1, y1+r, x1, y1,
    ]


# ================================================================
# 둥근 카드 위젯 (Canvas 배경 + 내부 Frame)
# ================================================================
class RoundCard(tk.Canvas):
    """posting_help QFrame#card — border-radius:16 · shadow 재현.

    auto_height=True  → pack(fill='x') 카드: 내부 콘텐츠에 맞춰 높이 자동 조절
    auto_height=False → grid(sticky='nsew') 카드: 그리드가 할당한 크기 사용
    """

    SHADOW = "#d0d6e0"

    def __init__(self, parent, radius=16, pad=P, auto_height=True, **kw):
        super().__init__(parent, highlightthickness=0, bd=0,
                         bg=parent["bg"], **kw)
        self._radius = radius
        self._pad = pad
        self._auto_h = auto_height
        self._fitting = False

        # 내부 프레임 — 자식 위젯은 여기에 배치
        self.inner = tk.Frame(self, bg=BG_CARD)
        self._win_id = self.create_window(pad, pad, window=self.inner,
                                           anchor="nw")

        if auto_height:
            self.inner.bind("<Configure>", self._schedule_fit)
        self.bind("<Configure>", self._redraw)

    # ── auto-height: 콘텐츠에 맞춰 캔버스 높이 조절 ──
    def _schedule_fit(self, e=None):
        if not self._fitting:
            self._fitting = True
            self.after_idle(self._fit_height)

    def _fit_height(self):
        self._fitting = False
        self.inner.update_idletasks()
        ih = self.inner.winfo_reqheight()
        needed = ih + self._pad * 2 + 4
        cur = self.winfo_height()
        if abs(needed - cur) > 2 and needed > 10:
            self.config(height=needed)

    # ── 캔버스 리사이즈 → 배경 다시 그리기 ──
    def _redraw(self, e=None):
        cw = self.winfo_width()
        ch = self.winfo_height()
        if cw < 10 or ch < 10:
            return

        self.delete("bg")
        r = self._radius
        pad = self._pad

        # 그림자 (2px 오른쪽, 3px 아래 오프셋)
        self.create_polygon(
            _rr_points(2, 3, cw, ch, r),
            smooth=True, fill=self.SHADOW, outline="", tags="bg")
        # 카드 본체
        self.create_polygon(
            _rr_points(0, 0, cw - 2, ch - 3, r),
            smooth=True, fill=BG_CARD, outline="", tags="bg")

        # 내부 프레임 너비 맞추기 (항상)
        self.itemconfig(self._win_id,
                        width=max(1, cw - pad * 2 - 2))
        # 높이는 auto가 아닐 때만 캔버스에 맞춤
        if not self._auto_h:
            self.itemconfig(self._win_id,
                            height=max(1, ch - pad * 2 - 4))

        # 프레임을 맨 위로
        self.tag_raise(self._win_id)


# ================================================================
# 모던 스크롤바 (posting_help 스타일)
# ================================================================
class ModernScrollbar(tk.Canvas):
    """포스팅 도우미 스타일 — 얇고 둥근 스크롤바.
    track: #f1f5f9, handle: #cbd5e1, hover: #94a3b8, width: 10px
    """
    TRACK   = "#f1f5f9"
    HANDLE  = "#cbd5e1"
    HOVER   = "#94a3b8"
    WIDTH   = 10
    MIN_H   = 30       # 핸들 최소 높이

    def __init__(self, parent, command=None, **kw):
        super().__init__(parent, width=self.WIDTH, highlightthickness=0,
                         bd=0, bg=self.TRACK, **kw)
        self._command = command
        self._lo = 0.0          # scrollbar low  (0‥1)
        self._hi = 1.0          # scrollbar high (0‥1)
        self._dragging = False
        self._drag_y = 0
        self._hover = False

        self.bind("<Configure>",        self._paint)
        self.bind("<ButtonPress-1>",    self._on_press)
        self.bind("<B1-Motion>",        self._on_drag)
        self.bind("<ButtonRelease-1>",  self._on_release)
        self.bind("<Enter>",            self._on_enter)
        self.bind("<Leave>",            self._on_leave)

    # ── 외부 연결 ────────────────────────────────
    def set(self, lo, hi):
        """스크롤 위치 업데이트 (Canvas.yview → scrollbar.set 콜백)."""
        self._lo = float(lo)
        self._hi = float(hi)
        self._paint()

    # ── 핸들 좌표 계산 ──────────────────────────
    def _handle_coords(self):
        h = self.winfo_height()
        if h < 1:
            return 0, 0
        handle_h = max(self.MIN_H, int((self._hi - self._lo) * h))
        track_free = h - handle_h
        y1 = int(self._lo / max(1.0 - (self._hi - self._lo), 0.001) * track_free)
        y1 = max(0, min(y1, track_free))
        y2 = y1 + handle_h
        return y1, y2

    # ── 그리기 ──────────────────────────────────
    def _paint(self, e=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if h < 2 or self._lo <= 0 and self._hi >= 1:
            return  # 스크롤 불필요 → 핸들 숨김

        y1, y2 = self._handle_coords()
        r = w // 2
        color = self.HOVER if self._hover or self._dragging else self.HANDLE
        # 둥근 사각형 핸들
        pad = 1
        self.create_round_rect(pad, y1 + pad, w - pad, y2 - pad, r, color)

    def create_round_rect(self, x1, y1, x2, y2, r, fill):
        """둥근 사각형을 부드럽게 그린다."""
        r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
        pts = [
            x1 + r, y1,  x2 - r, y1,
            x2, y1,  x2, y1 + r,
            x2, y2 - r,  x2, y2,
            x2 - r, y2,  x1 + r, y2,
            x1, y2,  x1, y2 - r,
            x1, y1 + r,  x1, y1,
        ]
        self.create_polygon(pts, smooth=True, fill=fill, outline="")

    # ── 마우스 이벤트 ───────────────────────────
    def _on_enter(self, e):
        self._hover = True
        self._paint()

    def _on_leave(self, e):
        self._hover = False
        if not self._dragging:
            self._paint()

    def _on_press(self, e):
        y1, y2 = self._handle_coords()
        if y1 <= e.y <= y2:
            self._dragging = True
            self._drag_y = e.y - y1
        else:
            # 트랙 빈 곳 클릭 → 해당 위치로 점프
            h = self.winfo_height()
            handle_h = y2 - y1
            frac = (e.y - handle_h / 2) / max(h - handle_h, 1)
            frac = max(0.0, min(1.0, frac))
            if self._command:
                self._command("moveto", str(frac))

    def _on_drag(self, e):
        if not self._dragging:
            return
        h = self.winfo_height()
        y1, y2 = self._handle_coords()
        handle_h = y2 - y1
        track_free = h - handle_h
        if track_free <= 0:
            return
        new_y1 = e.y - self._drag_y
        frac = new_y1 / track_free
        frac = max(0.0, min(1.0, frac))
        if self._command:
            self._command("moveto", str(frac))

    def _on_release(self, e):
        self._dragging = False
        self._paint()


# ================================================================
# 둥근 버튼 위젯 (Canvas 기반)
# ================================================================
class RoundBtn(tk.Canvas):
    """posting_help QPushButton — 둥근 모서리, 호버, 클릭."""

    def __init__(self, parent, text="", bg_color="#2563eb",
                 hover_color="#1d4ed8", press_color=None,
                 fg_color="#ffffff", font=None, command=None,
                 padx=22, pady=11, radius=10, bd_color=None, **kw):
        self._bg = bg_color
        self._hover = hover_color
        self._press = press_color or hover_color
        self._fg = fg_color
        self._font = font or FB
        self._cmd = command
        self._r = radius
        self._bd_color = bd_color
        self._text = text
        self._padx = padx
        self._pady = pady
        self._enabled = True

        f_obj = tkfont.Font(font=self._font)
        tw = f_obj.measure(text)
        th = f_obj.metrics("linespace")

        w = tw + padx * 2
        h = th + pady * 2

        super().__init__(parent, width=w, height=h,
                         highlightthickness=0, bd=0,
                         bg=parent["bg"], **kw)

        self._cw = w
        self._ch = h
        self._draw(self._bg)

        self.bind("<Enter>",            self._on_enter)
        self.bind("<Leave>",            self._on_leave)
        self.bind("<ButtonPress-1>",    self._on_press)
        self.bind("<ButtonRelease-1>",  self._on_release)
        self.config(cursor="hand2")

    def _draw(self, bg):
        self.delete("all")
        r = self._r
        if self._bd_color:
            self.create_polygon(
                _rr_points(0, 0, self._cw, self._ch, r),
                smooth=True, fill=self._bd_color, outline="")
            self.create_polygon(
                _rr_points(2, 2, self._cw - 2, self._ch - 2, r),
                smooth=True, fill=bg, outline="")
        else:
            self.create_polygon(
                _rr_points(0, 0, self._cw, self._ch, r),
                smooth=True, fill=bg, outline="")
        self.create_text(self._cw // 2, self._ch // 2,
                         text=self._text, fill=self._fg, font=self._font)

    def _on_enter(self, e):
        if self._enabled:
            self._draw(self._hover)
        else:
            self._draw("#9ca3af")
    def _on_leave(self, e):  self._draw(self._bg if self._enabled else "#9ca3af")
    def _on_press(self, e):  self._draw(self._press if self._enabled else "#9ca3af")

    def _on_release(self, e):
        self._draw(self._hover if self._enabled else "#9ca3af")
        if self._enabled and self._cmd:
            self._cmd()

    def set_enabled(self, enabled):
        """버튼 활성/비활성 전환"""
        self._enabled = bool(enabled)
        if self._enabled:
            self._draw(self._bg)
            self.config(cursor="hand2")
        else:
            self._draw("#9ca3af")
            self.config(cursor="arrow")

    def set_text(self, text):
        """버튼 텍스트 변경"""
        self._text = text
        f_obj = tkfont.Font(font=self._font)
        tw = f_obj.measure(text)
        th = f_obj.metrics("linespace")
        w = tw + self._padx * 2
        h = th + self._pady * 2
        self._cw, self._ch = w, h
        self.config(width=w, height=h)
        self._draw(self._bg)

    def set_command(self, cmd):
        """버튼 커맨드 변경"""
        self._cmd = cmd


# ================================================================
# 탭 버튼 (둥근 모서리 + 선택/비선택 상태)
# ================================================================
class TabBtn(RoundBtn):
    """posting_help helperButton / helperButtonSelected."""

    def __init__(self, parent, text, command=None, **kw):
        super().__init__(
            parent, text=text,
            bg_color=BG_CARD, hover_color=BG_HOVER, press_color=BG_HOVER,
            fg_color=FG, font=FB, command=command,
            padx=20, pady=10, radius=10, bd_color=BD, **kw,
        )
        self._selected = False

    def set_selected(self, sel):
        self._selected = sel
        if sel:
            self._bg = POINT
            self._hover = POINT
            self._press = POINT_H
            self._fg = FG_WHITE
            self._bd_color = None
        else:
            self._bg = BG_CARD
            self._hover = BG_HOVER
            self._press = BG_HOVER
            self._fg = FG
            self._bd_color = BD
        self._draw(self._bg)


# ================================================================
# 헬퍼 함수
# ================================================================
def _card(parent, radius=16, pad=P, auto_height=True, **kw):
    """둥근 카드 생성. (RoundCard, inner_frame) 반환."""
    rc = RoundCard(parent, radius=radius, pad=pad,
                   auto_height=auto_height, **kw)
    return rc, rc.inner


def _action_btn(parent, text, bg_color, hover_color, cmd):
    """둥근 액션 버튼 — radius=10, padding 22×11."""
    return RoundBtn(parent, text=text, bg_color=bg_color,
                    hover_color=hover_color, fg_color=FG_WHITE,
                    font=FB, command=cmd, padx=22, pady=11, radius=10)


def _soft_btn(parent, text, cmd):
    """둥근 소프트 버튼 — radius=8, 테두리."""
    return RoundBtn(parent, text=text, bg_color="#fbfcfe",
                    hover_color=BG_HEADER, fg_color=FG,
                    font=F_SMB, command=cmd, padx=14, pady=7,
                    radius=8, bd_color=BD)


class RoundEntry(tk.Canvas):
    """둥근 모서리 Entry — 크기 변경 없이 모서리만 둥글게."""
    BW = 2

    def __init__(self, parent, var, show="", readonly=False, radius=6, fill=None):
        pbg = parent.cget("bg") if isinstance(parent, tk.Widget) else BG_CARD
        st = "readonly" if readonly else "normal"
        rbg = fill if fill is not None else (BG_HOVER if readonly else BG_INPUT)

        # 높이 계산: 폰트 높이 + 내부 패딩(12) + 테두리(4)
        fobj = tkfont.Font(font=F)
        line_h = fobj.metrics("linespace")
        self._h = line_h + 16          # 내부 여유 12 + 테두리 4
        self._radius = radius
        self._fill = rbg

        super().__init__(parent, height=self._h, highlightthickness=0,
                         bd=0, bg=pbg)

        self.entry = tk.Entry(
            self, textvariable=var, font=F, bg=rbg, fg=FG,
            relief="flat", bd=0, insertbackground=BD_FOCUS,
            highlightthickness=0, readonlybackground=rbg, state=st,
            selectbackground="#cfe8ff", selectforeground=FG,
        )
        if show:
            self.entry.config(show=show)

        self._focused = False
        self.entry.bind("<FocusIn>",  lambda e: self._set_focus(True))
        self.entry.bind("<FocusOut>", lambda e: self._set_focus(False))
        self.bind("<Configure>", self._redraw)
        # 캔버스 빈 곳 클릭 → 엔트리에 포커스
        self.bind("<Button-1>", lambda e: self.entry.focus_set())

    def _set_focus(self, on):
        self._focused = on
        self._redraw()

    def _redraw(self, e=None):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("all")
        r = self._radius
        bw = self.BW
        color = BD_FOCUS if self._focused else BD
        # 테두리
        self.create_polygon(
            _rr_points(0, 0, w, h, r),
            smooth=True, fill=color, outline="")
        # 내부 채우기
        self.create_polygon(
            _rr_points(bw, bw, w - bw, h - bw, max(r - bw, 1)),
            smooth=True, fill=self._fill, outline="")
        # Entry 배치
        px = bw + 6
        self.create_window(px, bw, window=self.entry, anchor="nw",
                           width=max(w - 2 * px, 10), height=h - 2 * bw)

    # ── 프록시: toggle_key / toggle_naver_pw 호환 ──
    def cget(self, key):
        return self.entry.cget(key)

    def config(self, **kw):
        self.entry.config(**kw)

    configure = config


def _entry(parent, var, show="", readonly=False, fill=None):
    """posting_help QLineEdit — 둥근 모서리 Entry. fill: 배경색 (예: #e0f2fe)"""
    return RoundEntry(parent, var, show=show, readonly=readonly, fill=fill)


def _sep(parent):
    """posting_help 구분선 — #cbd5e1 · 2px."""
    f = tk.Frame(parent, bg=BD, height=2)
    f.pack(fill="x", pady=10)
    return f


def _grid_sep(parent, row, cols=2, title=None):
    """grid 레이아웃용 구분선 + 섹션 제목.
    posting_help 패턴: 구분선 → 볼드 섹션 타이틀."""
    wrap = tk.Frame(parent, bg=BG_CARD)
    wrap.grid(row=row, column=0, columnspan=cols, sticky="ew", pady=(6, 2))
    tk.Frame(wrap, bg=BD, height=2).pack(fill="x")
    if title:
        tk.Label(wrap, text=title, font=F_SEC, bg=BG_CARD,
                 fg=FG, anchor="w").pack(fill="x", pady=(8, 0))


# ================================================================
# APP
# ================================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("쿠팡 파트너스 도우미 v2.0")
        self.root.geometry("1200x950")
        self.root.minsize(1000, 800)
        self.root.configure(bg=BG)
        self.root.option_add("*Font", F)

        # ttk 스타일 — clam 테마 (가장 커스터마이즈 가능)
        style = ttk.Style()
        style.theme_use("clam")
        # 발행 카테고리 Combobox — 밝은 하늘색 배경
        style.configure("TCombobox", fieldbackground="#e0f2fe", background="#e0f2fe")
        style.map("TCombobox", fieldbackground=[("readonly", "#e0f2fe")], background=[("readonly", "#e0f2fe")])
        self.root.option_add("*TCombobox*Listbox*Background", "#e0f2fe")
        # Treeview (카페 ID/메뉴 추출) — 연한 하늘색
        style.configure("Treeview", background="#e0f2fe", fieldbackground="#e0f2fe", foreground=FG)
        style.configure("Treeview.Heading", background="#e0f2fe", foreground=FG)

        self.keywords = []
        self.results = {}
        self.is_running = False  # 상품 검색 실행 중
        self._stop_flag = False
        self.cafe_list = []
        self.is_posting = False
        self.is_blog_posting = False

        # 자동 재시작 설정
        self._auto_restart_enabled = False
        self._auto_restart_hour = 9      # 기본 09시
        self._auto_restart_minute = 0    # 기본 00분
        self._auto_restart_blog = False  # 블로그 자동재시작
        self._auto_restart_cafe = True   # 카페 자동재시작 (기본)
        self._auto_restart_timer_id = None
        self._auto_restart_daily = True  # 매일 반복
        self._auto_restart_pending_cafe = False  # 블로그→카페 순차 실행용

        self.worker_thread = None

        self.app_links = {}
        self.banners = []
        self.helper_cafes = []
        self.helper_new_cafe_since = None
        self.helper_new_cafes = []

        self._build()
        self._load_api_key_silent()
        self._load_cafe_settings_silent()
        kw_path = os.path.join(BASE_DIR, "keywords.txt")
        if os.path.exists(kw_path):
            self._load_keywords_file(kw_path)

        # 창 아이콘 + Supabase 데이터 — 창 표시 후 백그라운드에서 로드
        self.root.after(50, self._deferred_startup)

    def _deferred_startup(self):
        """창 표시 후 아이콘 생성 + Supabase 데이터 백그라운드 로드"""
        # 1) 아이콘 생성 (메인 스레드, 빠름)
        try:
            ico_path = os.path.join(BASE_DIR, "app_icon.ico")
            if not os.path.exists(ico_path):
                from PIL import Image, ImageDraw
                sz = 64
                img = Image.new("RGB", (sz, sz), (255, 255, 255))
                d = ImageDraw.Draw(img)
                r = sz // 2 - 2
                cx, cy = sz // 2, sz // 2
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 87, 34), outline=(230, 74, 25))
                img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
            if os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
        except Exception:
            pass
        # 2) Supabase 데이터 — 백그라운드 스레드에서 로드
        def _fetch():
            try:
                from shared.gui_data import fetch_app_links, fetch_banners, get_admin_settings, get_cafe_targets
                links = fetch_app_links()
                banners = fetch_banners()
                admin_ok, cafe_ok = False, False
                admin_settings = {}
                cafe_targets = []
                helper_cafes = []
                helper_since = None
                try:
                    admin_settings = get_admin_settings()
                    admin_ok = bool(admin_settings)
                    cafe_targets = get_cafe_targets()
                    cafe_ok = bool(cafe_targets)
                except Exception:
                    pass
                try:
                    from shared.gui_data import fetch_helper_cafes, fetch_helper_new_cafe_since
                    helper_cafes = fetch_helper_cafes()
                    helper_since = fetch_helper_new_cafe_since()
                    if not cafe_targets and helper_cafes:
                        cafe_targets = [{"cafe_id": c.get("cafe_id"), "menu_id": c.get("menu_id"), "name": c.get("cafe_id")} for c in helper_cafes]
                        cafe_ok = bool(cafe_targets)
                except Exception:
                    pass
                print(f"[GUI] get_admin_settings={'OK' if admin_ok else 'FAIL'}, get_cafe_targets={'OK' if cafe_ok else 'FAIL'}", flush=True)
                self.root.after(0, lambda: self._apply_fetched_data(links, banners, helper_cafes, helper_since, admin_settings, cafe_targets))
            except Exception as ex:
                print(f"[GUI] Supabase fetch 실패: {ex}", flush=True)
        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_fetched_data(self, links, banners, helper_cafes=None, helper_since=None, admin_settings=None, cafe_targets=None):
        """Supabase에서 가져온 데이터 적용 (메인 스레드)"""
        self.app_links = links or {}
        self.banners = banners or []
        self.helper_cafes = helper_cafes if helper_cafes is not None else getattr(self, "helper_cafes", [])
        self.helper_new_cafe_since = helper_since if helper_since is not None else getattr(self, "helper_new_cafe_since", None)
        self._admin_settings = admin_settings or {}
        self._cafe_targets_readonly = cafe_targets or []
        self._compute_helper_new_cafes()
        # [C] 관리자 설정: gemini_key, captcha_key — Supabase에서 있으면 적용, 읽기 전용
        gk = self._admin_settings.get("gemini_key") or self._admin_settings.get("gemini_api_key", "")
        if gk and hasattr(self, "gemini_key_var"):
            self.gemini_key_var.set(gk)
            if hasattr(self, "gemini_entry"):
                self.gemini_entry.config(state="readonly")
        ck = self._admin_settings.get("captcha_key") or self._admin_settings.get("captcha_api_key", "")
        if ck:
            self._cafe_autojoin_captcha_key = ck
        if self.banners and hasattr(self, "_banner_rotate_start"):
            self._banner_rotate_start()
        if hasattr(self, "helper_cafe_count_label") and self.helper_cafe_count_label.winfo_exists():
            self._refresh_helper_cafe_count()
        if hasattr(self, "helper_new_cafe_label") and self.helper_new_cafe_label.winfo_exists():
            self._refresh_helper_new_cafe_alert()

    # ──────────────────────────────────────────────
    # BUILD
    # ──────────────────────────────────────────────
    def _build(self):
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="both", expand=True, padx=M, pady=M)

        self._build_tab_bar(wrap)

        self.main_container = tk.Frame(wrap, bg=BG)
        self.main_container.pack(fill="both", expand=True, pady=(S, 0))

        self._build_search_page()
        self._build_blog_page()
        self._build_cafe_page()
        self._build_global_log(wrap)
        self._build_footer(wrap)
        self._build_banner(wrap)
        self._switch_tab_main("search")

    # ── 탭 바 (도우미 메뉴 카드) ──
    def _build_tab_bar(self, parent):
        sh, card = _card(parent, pad=8)
        sh.pack(fill="x")

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x", padx=6, pady=4)

        # 통신시작 체크박스 (post_tasks 폴링 → 새 키워드 등록 시 글 작성)
        self._comm_enabled_var = tk.BooleanVar(value=False)
        self._comm_cb = tk.Checkbutton(
            row, text=" 통신시작 ", variable=self._comm_enabled_var,
            font=F_SM, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD, command=self._on_comm_toggle,
        )
        self._comm_cb.pack(side="left", padx=(0, S))

        # VM 이름 (다중 VM 시 각 PC별 식별자 — configs/gui_vm.json 또는 env VM_NAME)
        tk.Label(row, text="VM:", font=F_SM, bg=BG_CARD, fg=FG_LABEL).pack(side="left", padx=(S, 2))
        self._comm_vm_name_var = tk.StringVar(value=_load_gui_vm_name())
        _vm_entry = tk.Entry(row, textvariable=self._comm_vm_name_var, font=F_SM, width=10, bg=BG_INPUT)
        _vm_entry.pack(side="left", padx=(0, 2))
        _vm_entry.bind("<FocusOut>", lambda e: self._save_gui_vm_config())

        # 실행 시작 (post_tasks enqueue)
        _action_btn(row, " 실행 시작 ", GREEN, GREEN_H, self._on_enqueue_start).pack(side="left", padx=(0, S))

        self._tab_btns = {}
        self._cur_tab = "search"

        for tid, txt in [("search", "🔍 상품 검색"), ("blog", "블로그 포스팅"), ("cafe", "카페 포스팅")]:
            btn = TabBtn(row, text=f"  {txt}  ",
                         command=lambda t=tid: self._switch_tab_main(t))
            btn.pack(side="left", padx=(0, S))
            self._tab_btns[tid] = btn

        # 자동재시작설정 버튼 (카페 포스팅 바로 옆)
        _action_btn(row, " 자동재시작설정 ", "#7C5CFC", "#6B4AEB",
                    self._open_auto_restart_settings).pack(side="left", padx=(0, S))

        # 회원가입 / 로그인 / 로그아웃 버튼
        self._auth_available = False
        self._auth_session_id = None
        self.current_user_id = None  # Supabase Auth user_id (enqueue_post_tasks 등에서 사용)
        self._comm_stop_flag = False
        self._comm_poll_thread = None
        try:
            from auth import is_logged_in, get_session, get_free_use_until, logout
            self._auth_available = True
            self._auth_btn_register = _action_btn(row, " 회원가입 ", TEAL, TEAL_H, self._open_register_dialog)
            self._auth_btn_register.pack(side="left", padx=(0, S))
            self._auth_btn_login = _action_btn(row, " 로그인 ", TEAL, TEAL_H, self._open_login_dialog)
            self._auth_btn_login.pack(side="left", padx=(0, S))
            self._auth_status_label = tk.Label(row, text="", font=F_SM, bg=BG_CARD, fg=FG_LABEL, anchor="e")
            self._auth_status_label.pack(side="right", padx=(0, 4))
            self._update_auth_ui()
        except Exception:
            pass

    def _switch_tab_main(self, tid):
        self._cur_tab = tid
        for k, b in self._tab_btns.items():
            b.set_selected(k == tid)
        for w in self.main_container.winfo_children():
            w.pack_forget()
        if tid == "search":
            self.pg_search.pack(fill="both", expand=True)
        elif tid == "blog":
            self.pg_blog.pack(fill="both", expand=True)
        else:
            self.pg_cafe.pack(fill="both", expand=True)

    # ── 공용 실행 로그 (항상 표시, 탭 무관) ──
    def _build_global_log(self, parent):
        sh, card = _card(parent, pad=8)
        sh.pack(fill="x", pady=(S, 0))

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(row, text="실행 로그", font=F_SEC, bg=BG_CARD,
                 fg=FG, anchor="w").pack(side="left")
        _action_btn(row, " 로그 지우기 ", ORANGE, ORANGE_H, self._clear_global_log).pack(side="right")
        _sep(card)

        log_wrap = tk.Frame(card, bg=LOG_BG, highlightthickness=2, highlightbackground=BD)
        log_wrap.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.global_log_text = tk.Text(
            log_wrap, font=F_LOG, bg=LOG_BG, fg=LOG_FG,
            relief="flat", wrap="word", state="disabled",
            highlightthickness=0, padx=10, pady=10, height=8,
        )
        gsb = ModernScrollbar(log_wrap, command=self.global_log_text.yview)
        gsb.pack(side="right", fill="y")
        self.global_log_text.config(yscrollcommand=gsb.set)
        self.global_log_text.pack(fill="both", expand=True)

    def append_log_global(self, msg):
        """실행 로그 — 탭과 무관하게 항상 공용 로그에 출력"""
        print(msg)
        def _do():
            if getattr(self, "global_log_text", None) and self.global_log_text.winfo_exists():
                self.global_log_text.config(state="normal")
                self.global_log_text.insert("end", msg + "\n")
                self.global_log_text.see("end")
                self.global_log_text.config(state="disabled")
        if self.root.winfo_exists():
            self.root.after(0, _do)

    def _clear_global_log(self):
        if getattr(self, "global_log_text", None):
            self.global_log_text.config(state="normal")
            self.global_log_text.delete("1.0", "end")
            self.global_log_text.config(state="disabled")

    # ── 푸터 ──
    def _build_footer(self, parent):
        sh, card = _card(parent, pad=8)
        sh.pack(fill="x", pady=(S, 0))

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x", padx=8, pady=4)

        # 상태 위젯 (내부 참조용, 비표시)
        self.status_dot = tk.Label(row, bg=BG_CARD)
        self.status_text = tk.Label(row, bg=BG_CARD)
        self.bottom_status = self.status_text

        def _on_inquiry():
            url = self.app_links.get("inquiry", "").strip()
            if url:
                webbrowser.open(url)
            else:
                messagebox.showinfo("안내", "문의접수 링크가 등록되어 있지 않습니다.")

        _soft_btn(row, " 문의접수 ", _on_inquiry).pack(side="left", padx=(0, 8))
        tk.Label(row,
                 text="무료 혜택 유지를 위해 유료 회원 글과 본인 홍보글이 1:1 비율로 발행되는 점 양해 부탁드립니다.",
                 font=("맑은 고딕", 9), bg=BG_CARD, fg="#888888",
                 anchor="w").pack(side="left")

        tk.Label(row, text="ⓘ 모든 작업은 사용자의 책임 하에 실행됩니다.",
                 font=F_SM, bg=BG_CARD, fg=FG_DIM, anchor="e").pack(side="right")

    # ── 하단 배너 (자영업자 타겟 AI 비서) ──
    BANNER_URL_DEFAULT = "https://posting-webna.vercel.app/"

    def _build_banner(self, parent):
        banner = tk.Frame(parent, bg=BG, height=100)
        banner.pack(side="bottom", fill="x", pady=(4, 0))
        banner.pack_propagate(False)

        from PIL import Image, ImageTk, ImageDraw

        # #051937 → #004d7a 짙은 네이비 사선 그라데이션
        NAVY_1 = (0x05, 0x19, 0x37)
        NAVY_2 = (0x00, 0x4d, 0x7a)

        def _make_banner_bg(w, h, radius=16):
            """짙은 네이비 사선 그라데이션 + Tech Line 패턴(~10%) + 둥근 모서리"""
            grad = Image.new("RGB", (w, h))
            px = grad.load()
            tot = w + h
            for x in range(w):
                for y in range(h):
                    t = (x + y) / max(tot - 1, 1)
                    r = int(NAVY_1[0] + (NAVY_2[0] - NAVY_1[0]) * t)
                    g = int(NAVY_1[1] + (NAVY_2[1] - NAVY_1[1]) * t)
                    b = int(NAVY_1[2] + (NAVY_2[2] - NAVY_1[2]) * t)
                    px[x, y] = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

            draw = ImageDraw.Draw(grad)
            # Tech Line 패턴 (Grid, 10% 느낌·은은하게)
            line_c = (40, 70, 110)
            for iv in range(0, w + 1, 55):
                draw.line([(iv, 0), (iv, h)], fill=line_c, width=1)
            for ih in range(0, h + 1, 50):
                draw.line([(0, ih), (w, ih)], fill=line_c, width=1)

            # 상단 부드러운 그림자 (0 -5px 15px rgba(0,0,0,0.1) 느낌)
            for y in range(min(8, h)):
                alpha = int(25 * (1 - y / 8))
                for x in range(w):
                    c = px[x, y]
                    px[x, y] = tuple(max(0, c[k] - alpha) for k in range(3))

            # 4곳 둥근 마스크
            mask = Image.new("L", (w, h), 0)
            draw_m = ImageDraw.Draw(mask)
            r = min(radius, w // 2, h // 2)
            draw_m.rectangle((r, r, w - r, h - r), fill=255)
            draw_m.rectangle((r, 0, w - r, r), fill=255)
            draw_m.rectangle((r, h - r, w - r, h), fill=255)
            draw_m.rectangle((0, r, r, h - r), fill=255)
            draw_m.rectangle((w - r, r, w, h - r), fill=255)
            draw_m.pieslice((0, 0, r * 2, r * 2), 180, 270, fill=255)
            draw_m.pieslice((w - r * 2, 0, w, r * 2), 270, 360, fill=255)
            draw_m.pieslice((0, h - r * 2, r * 2, h), 90, 180, fill=255)
            draw_m.pieslice((w - r * 2, h - r * 2, w, h), 0, 90, fill=255)

            bg_color = (0xee, 0xf2, 0xf7)
            bg_img = Image.new("RGB", (w, h), bg_color)
            return Image.composite(grad, bg_img, mask)

        canvas = tk.Canvas(banner, highlightthickness=0, cursor="hand2", bg=BG)
        canvas.pack(fill="both", expand=True)
        canvas._btn_hover = False
        canvas._banner_rotate_timer_id = None

        DEFAULT_MAIN = "월 30만원으로 채용하는 AI 광고직원을 아시나요?"
        DEFAULT_SUB = "24시간 쉬지 않고 사장님 대신 포스팅하는 스마트 비서 서비스"

        def _get_current_banner():
            if self.banners:
                return random.choice(self.banners)
            return {
                "main_text": DEFAULT_MAIN,
                "sub_text": DEFAULT_SUB,
                "url": self.app_links.get("banner", "").strip() or self.BANNER_URL_DEFAULT,
            }

        canvas._current_banner = _get_current_banner()

        def _redraw(e=None, btn_hover=None):
            canvas.update_idletasks()
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 2 or h < 2:
                w, h = 1100, 100
            use_btn_hover = btn_hover if btn_hover is not None else getattr(canvas, "_btn_hover", False)
            canvas.delete("all")
            img = _make_banner_bg(w, h, radius=16)
            photo = ImageTk.PhotoImage(img)
            canvas._img_ref = photo
            canvas.create_image(0, 0, anchor="nw", image=photo, tags="banner_content")

            pad = 20
            cy = h // 2
            cur = canvas._current_banner
            main_txt = cur.get("main_text", DEFAULT_MAIN)
            sub_txt = cur.get("sub_text", DEFAULT_SUB)
            btn_txt = "자세히 보기 >"
            icon_txt = "☁"

            f_icon = tkfont.Font(family="맑은 고딕", size=14)
            f_main = tkfont.Font(family="맑은 고딕", size=18, weight="bold")
            f_sub = tkfont.Font(family="맑은 고딕", size=11)
            f_btn = tkfont.Font(family="맑은 고딕", size=12, weight="bold")

            w_icon = f_icon.measure(icon_txt)
            w_main = f_main.measure(main_txt)
            w_btn = f_btn.measure(btn_txt)
            line_gap = 10

            x_icon = pad + w_icon // 2
            y_main = cy - 16
            y_sub = cy + 16 + line_gap

            canvas.create_text(x_icon, cy, text=icon_txt, font=("맑은 고딕", 14), fill="#ffffff", anchor="center", tags="banner_content")
            canvas.create_line(pad + w_icon + 12, pad + 10, pad + w_icon + 12, h - pad - 10, fill="#6b7a8a", width=1, tags="banner_content")

            x_start = pad + w_icon + 28
            x_btn = w - pad - w_btn // 2 - 14
            btn_l = x_btn - w_btn // 2 - 12
            center_x = (x_start + btn_l) // 2
            canvas.create_text(center_x, y_main, text=main_txt, font=("맑은 고딕", 18, "bold"), fill="#ffffff", anchor="center", tags="banner_content")
            canvas.create_text(center_x, y_sub, text=sub_txt, font=("맑은 고딕", 11), fill="#BDC3C7", anchor="center", tags="banner_content")

            btn_r = x_btn + w_btn // 2 + 12
            btn_t = cy - 18
            btn_b = cy + 18
            if use_btn_hover:
                canvas.create_rectangle(btn_l, btn_t, btn_r, btn_b, fill="#d0dce8", outline="#ffffff", width=1, tags="banner_content")
            else:
                canvas.create_rectangle(btn_l, btn_t, btn_r, btn_b, outline="#ffffff", width=1, tags="banner_content")
            canvas.create_text(x_btn, cy, text=btn_txt, font=("맑은 고딕", 12, "bold"), fill="#ffffff", anchor="center", tags="banner_content")

        def _on_enter(e):
            canvas._btn_hover = True
            _redraw(btn_hover=True)

        def _on_leave(e):
            canvas._btn_hover = False
            _redraw(btn_hover=False)

        def _open_banner_url(e):
            url = canvas._current_banner.get("url", "").strip()
            if not url:
                url = self.app_links.get("banner", "").strip() or self.BANNER_URL_DEFAULT
            if url:
                webbrowser.open(url)

        def _rotate_banner():
            if self.banners:
                canvas._current_banner = random.choice(self.banners)
            else:
                canvas._current_banner = _get_current_banner()
            if canvas.winfo_exists():
                _redraw()
            if canvas.winfo_exists() and self.banners:
                t = threading.Timer(60.0, lambda: self.root.after(0, _rotate_banner))
                t.daemon = True
                t.start()
                canvas._banner_rotate_timer = t

        canvas.bind("<Configure>", _redraw)
        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)
        canvas.bind("<Button-1>", _open_banner_url)
        canvas.after(100, lambda: _redraw(None))

        def _start_banner_rotate():
            if self.banners and canvas.winfo_exists():
                canvas._current_banner = random.choice(self.banners)
                _redraw()
                t = threading.Timer(60.0, lambda: self.root.after(0, _rotate_banner))
                t.daemon = True
                t.start()
                canvas._banner_rotate_timer = t
        self._banner_canvas = canvas
        self._banner_rotate_start = _start_banner_rotate
        if self.banners:
            _start_banner_rotate()

    # ═══════════════════════════════════════════════
    # PAGE 1 — 상품 검색
    # ═══════════════════════════════════════════════
    def _build_search_page(self):
        self.pg_search = tk.Frame(self.main_container, bg=BG)
        # 키워드 반복 기본값 (카페탭에서 관리, worker 호환용)
        self.kw_repeat_min_var = tk.IntVar(value=3)
        self.kw_repeat_max_var = tk.IntVar(value=7)

        # 액션바 카드 (상단)
        sh, card = _card(self.pg_search, pad=8)
        sh.pack(fill="x")
        bar = tk.Frame(card, bg=BG_CARD)
        bar.pack(fill="x", padx=4, pady=3)

        def _on_tutorial_video():
            url = self.app_links.get("tutorial_video", "").strip()
            if url:
                webbrowser.open(url)
            else:
                messagebox.showinfo("안내", "광고교육 및 사용법 영상 링크가 등록되어 있지 않습니다.")

        for txt, c, h, cmd in [
            ("키워드 불러오기", POINT,  POINT_H,  self._on_load_keywords),
            ("추천인 포스팅발행 키워드등록", TEAL, TEAL_H,  self._open_distribute_keywords_dialog),
            ("▶️ 광고교육 및 사용법영상", RED, RED_H, _on_tutorial_video),
        ]:
            _action_btn(bar, f" {txt} ", c, h, cmd).pack(
                side="left", padx=(0, 4))

        # 3열 레이아웃 (메인 콘텐츠)
        body = tk.Frame(self.pg_search, bg=BG)
        body.pack(fill="both", expand=True, pady=(S, 0))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_sidebar(body)
        self._build_center(body)
        self._build_right_log(body)

    # ── 사이드바 (200px) ──
    def _build_sidebar(self, parent):
        sh, card = _card(parent, width=200, auto_height=False)
        sh.grid(row=0, column=0, sticky="ns", padx=(0, S))

        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="both", expand=True, padx=12, pady=12)
        card.pack_propagate(False)
        card.config(width=200)

        self._sec(inner, "키워드 목록")

        self.kw_listbox = tk.Listbox(
            inner, selectmode="extended", font=F,
            bg=BG_INPUT, fg=FG, relief="flat", bd=0,
            highlightthickness=2, highlightbackground=BD, highlightcolor=BD_FOCUS,
            selectbackground=POINT, selectforeground=FG_WHITE,
            activestyle="none",
        )
        self.kw_listbox.pack(fill="both", expand=True, pady=(0, 6))

        self.kw_count = tk.Label(inner, text="0개 키워드", font=F_SM,
                                  bg=BG_CARD, fg=FG_LABEL, anchor="w")
        self.kw_count.pack(fill="x", pady=(0, 8))

    # ── 중앙 (설정) ──
    def _build_center(self, parent):
        center = tk.Frame(parent, bg=BG)
        center.grid(row=0, column=1, sticky="nsew")
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)

        # 설정 카드 (스크롤 가능)
        sh, card = _card(center, auto_height=False)
        sh.grid(row=0, column=0, sticky="nsew", pady=(0, S))

        scroll_canvas = tk.Canvas(card, bg=BG_CARD, highlightthickness=0, bd=0)
        settings_sb = ModernScrollbar(card, command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=settings_sb.set)

        settings_sb.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(scroll_canvas, bg=BG_CARD, padx=22, pady=16)
        inner_id = scroll_canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_cfg(e):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        def _on_canvas_cfg(e):
            scroll_canvas.itemconfig(inner_id, width=e.width)
        inner.bind("<Configure>", _on_inner_cfg)
        scroll_canvas.bind("<Configure>", _on_canvas_cfg)

        def _on_wheel(e):
            scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        def _bind_w(e):
            scroll_canvas.bind_all("<MouseWheel>", _on_wheel)
        def _unbind_w(e):
            scroll_canvas.unbind_all("<MouseWheel>")
        scroll_canvas.bind("<Enter>", _bind_w)
        scroll_canvas.bind("<Leave>", _unbind_w)

        tk.Label(inner, text="기본 설정", font=F_TITLE, bg=BG_CARD,
                 fg=FG, anchor="w").pack(fill="x")
        _sep(inner)

        tk.Label(inner,
                 text="API 키와 검색 옵션을 설정하세요.",
                 font=F_SM, bg=BG_CARD, fg=FG_LABEL, anchor="w"
                 ).pack(fill="x", pady=(0, 10))

        form = tk.Frame(inner, bg=BG_CARD)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        # ── 쿠팡 파트너스 API ──
        r = 0
        cak = tk.Frame(form, bg=BG_CARD)
        cak.grid(row=r, column=0, columnspan=2, sticky="ew", pady=8)
        cak.columnconfigure(0, weight=1)
        tk.Label(cak, text="Access Key 등록", font=F_SM, bg=BG_CARD,
                 fg=FG_LABEL, anchor="w").pack(fill="x")
        cak_row = tk.Frame(cak, bg=BG_CARD)
        cak_row.pack(fill="x")
        self.coupang_ak_var = tk.StringVar()
        self.coupang_ak_var.trace_add("write", lambda *_: self._auto_save_api_keys())
        self.coupang_ak_entry = _entry(cak_row, self.coupang_ak_var, show="●")
        self.coupang_ak_entry.pack(side="left", fill="x", expand=True)
        _soft_btn(cak_row, "표시", self._toggle_coupang_ak).pack(
            side="left", padx=(4, 0))

        r += 1
        csk = tk.Frame(form, bg=BG_CARD)
        csk.grid(row=r, column=0, columnspan=2, sticky="ew", pady=8)
        csk.columnconfigure(0, weight=1)
        tk.Label(csk, text="Secret Key 등록", font=F_SM, bg=BG_CARD,
                 fg=FG_LABEL, anchor="w").pack(fill="x")
        csk_row = tk.Frame(csk, bg=BG_CARD)
        csk_row.pack(fill="x")
        self.coupang_sk_var = tk.StringVar()
        self.coupang_sk_var.trace_add("write", lambda *_: self._auto_save_api_keys())
        self.coupang_sk_entry = _entry(csk_row, self.coupang_sk_var, show="●")
        self.coupang_sk_entry.pack(side="left", fill="x", expand=True)
        _soft_btn(csk_row, "표시", self._toggle_coupang_sk).pack(
            side="left", padx=(4, 0))

        r += 1; _grid_sep(form, r)

        # ── Gemini API ──
        r += 1
        self._lbl(form, "Gemini API Key:", r)
        kf = tk.Frame(form, bg=BG_CARD)
        kf.grid(row=r, column=1, sticky="ew", pady=8)

        self.gemini_key_var = tk.StringVar()
        self.gemini_key_var.trace_add("write", lambda *_: self._auto_save_api_keys())
        self.gemini_entry = _entry(kf, self.gemini_key_var, show="●")
        self.gemini_entry.pack(side="left", fill="x", expand=True)

        for t, c in [("표시", self._toggle_key), ("저장", self._save_api_key),
                      ("불러오기", lambda: self._load_api_key())]:
            _soft_btn(kf, t, c).pack(side="left", padx=(4, 0))

        r += 1; _grid_sep(form, r, title="파일 설정")

        r += 1
        self._lbl(form, "키워드 파일:", r)
        ff = tk.Frame(form, bg=BG_CARD)
        ff.grid(row=r, column=1, sticky="ew", pady=8)

        self.file_var = tk.StringVar(value="keywords.txt")
        _entry(ff, self.file_var, readonly=True).pack(
            side="left", fill="x", expand=True)
        _soft_btn(ff, "찾아보기...", self._on_load_keywords).pack(
            side="left", padx=(4, 0))

        r += 1
        self._lbl(form, "", r)
        self.use_paid_keywords_frame = tk.Frame(form, bg=BG_CARD)
        self.use_paid_keywords_frame.grid(row=r, column=1, sticky="w", pady=8)
        self.use_paid_member_keywords_var = tk.BooleanVar(value=False)
        self.use_paid_keywords_cb = tk.Checkbutton(
            self.use_paid_keywords_frame,
            text="유료회원 키워드 사용 (관리자 전용, 키워드 설정 없이 랜덤 사용)",
            variable=self.use_paid_member_keywords_var,
            font=F_SM, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD,
        )
        self.use_paid_keywords_cb.pack(side="left")

        r += 1
        self._lbl(form, "이미지 저장 경로:", r)
        imgf = tk.Frame(form, bg=BG_CARD)
        imgf.grid(row=r, column=1, sticky="ew", pady=8)

        self.img_dir_var = tk.StringVar(
            value=os.path.join(BASE_DIR, "images"))
        _entry(imgf, self.img_dir_var).pack(
            side="left", fill="x", expand=True)
        _soft_btn(imgf, "찾아보기...", self._browse_img_dir).pack(
            side="left", padx=(4, 0))

        r += 1; _grid_sep(form, r, title="진행 상태")

        r += 1
        self._lbl(form, "진행 상태:", r)
        pf = tk.Frame(form, bg=BG_CARD)
        pf.grid(row=r, column=1, sticky="ew", pady=8)

        self.progress_canvas = tk.Canvas(pf, height=22, bg=SEP,
                                          highlightthickness=0, bd=0)
        self.progress_canvas.pack(fill="x")
        self.progress_bar_id = self.progress_canvas.create_rectangle(
            0, 0, 0, 22, fill=POINT, outline="")
        self.progress_text_id = self.progress_canvas.create_text(
            8, 11, text="대기 중", anchor="w", font=F_SM, fill=FG_LABEL)
        self._progress_pct = 0

    # ── 우측 로그 패널 (posting_help 활동 내역, 300px) ──
    def _build_right_log(self, parent):
        """상품 검색 페이지에서는 결과/로그 탭이 center에 포함되므로
        별도 우측 패널 없음. 향후 확장 시 이 자리에 배치."""
        pass

    # ═══════════════════════════════════════════════
    # PAGE 2 — 블로그 포스팅
    # ═══════════════════════════════════════════════
    def _build_blog_page(self):
        self.pg_blog = tk.Frame(self.main_container, bg=BG)

        sh, card = _card(self.pg_blog, pad=8)
        sh.pack(fill="x")
        bar = tk.Frame(card, bg=BG_CARD)
        bar.pack(fill="x", padx=4, pady=3)

        for txt, c, h, cmd in [
            ("설정 저장",   TEAL,   TEAL_H,   self._save_blog_settings),
            ("설정 불러오기", POINT,  POINT_H,  self._load_blog_settings),
            ("발행 시작 ▶", GREEN,  GREEN_H,  self._on_start_blog_posting),
            ("발행 중지",   RED,    RED_H,    self._on_stop_blog_posting),
            ("로그 지우기", ORANGE, ORANGE_H, self._clear_blog_log),
        ]:
            _action_btn(bar, f" {txt} ", c, h, cmd).pack(
                side="left", padx=(0, 4))
        self.blog_auto_start_cafe_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bar, text=" 카페자동시작 ", variable=self.blog_auto_start_cafe_var,
            font=F_SM, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD,
        ).pack(side="left", padx=(8, 0))

        body = tk.Frame(self.pg_blog, bg=BG)
        body.pack(fill="both", expand=True, pady=(S, 0))
        body.columnconfigure(0, weight=2, minsize=380)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_blog_settings(body)
        self._build_blog_log(body)

    def _build_blog_settings(self, parent):
        sh, card = _card(parent, auto_height=False)
        sh.grid(row=0, column=0, sticky="nsew", padx=(0, S // 2))

        scroll_canvas = tk.Canvas(card, bg=BG_CARD, highlightthickness=0, bd=0)
        scrollbar = ModernScrollbar(card, command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(scroll_canvas, bg=BG_CARD, padx=22, pady=16)
        inner_id = scroll_canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(e):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def _on_canvas_configure(e):
            scroll_canvas.itemconfig(inner_id, width=e.width)

        inner.bind("<Configure>", _on_inner_configure)
        scroll_canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(e):
            scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        def _bind_wheel(e):
            scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(e):
            scroll_canvas.unbind_all("<MouseWheel>")

        scroll_canvas.bind("<Enter>", _bind_wheel)
        scroll_canvas.bind("<Leave>", _unbind_wheel)

        tk.Label(inner, text="블로그 설정", font=F_TITLE, bg=BG_CARD,
                 fg=FG, anchor="w").pack(fill="x")
        _sep(inner)

        tk.Label(inner,
                 text="네이버 로그인 정보를 설정하세요. "
                      "발행 시작 시 상품 검색 → Gemini 요약 → 네이버 블로그 포스팅이 진행됩니다.",
                 font=F_SM, bg=BG_CARD, fg=FG_LABEL, anchor="w",
                 wraplength=380, justify="left").pack(fill="x", pady=(0, 10))

        form = tk.Frame(inner, bg=BG_CARD)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        r = 0
        self._lbl(form, "네이버 아이디:", r)
        idf = tk.Frame(form, bg=BG_CARD)
        idf.grid(row=r, column=1, sticky="ew", pady=8)
        self.blog_naver_id_var = tk.StringVar()
        _entry(idf, self.blog_naver_id_var).pack(fill="x")

        r += 1
        self._lbl(form, "네이버 비밀번호:", r)
        pwf = tk.Frame(form, bg=BG_CARD)
        pwf.grid(row=r, column=1, sticky="ew", pady=8)
        self.blog_naver_pw_var = tk.StringVar()
        _entry(pwf, self.blog_naver_pw_var, show="●").pack(fill="x")

        r += 1; _grid_sep(form, r, title="다중아이디 설정")
        r += 1
        self._lbl(form, "다중아이디 사용:", r)
        maf = tk.Frame(form, bg=BG_CARD)
        maf.grid(row=r, column=1, sticky="w", pady=8)
        self.blog_multi_account_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            maf, text="활성화",
            variable=self.blog_multi_account_var,
            font=F_SM, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD,
        ).pack(side="left")
        tk.Label(maf, text=" (아이디 탭 비밀번호 형식 txt 파일)", font=F_SM,
                 bg=BG_CARD, fg=FG_DIM).pack(side="left")
        r += 1
        self._lbl(form, "아이디 파일:", r)
        maf2 = tk.Frame(form, bg=BG_CARD)
        maf2.grid(row=r, column=1, sticky="ew", pady=8)
        maf2.columnconfigure(0, weight=1)
        self.blog_multi_account_file_var = tk.StringVar()
        _entry(maf2, self.blog_multi_account_file_var, readonly=True).pack(
            fill="x", pady=(0, 4))
        _soft_btn(maf2, "파일 불러오기", self._browse_blog_multi_account_file).pack(anchor="w")
        r += 1
        self._lbl(form, "아이디 교체 대기시간:", r)
        maf3 = tk.Frame(form, bg=BG_CARD)
        maf3.grid(row=r, column=1, sticky="w", pady=8)
        self.blog_account_switch_wait_var = tk.IntVar(value=5)
        tk.Spinbox(maf3, from_=1, to=1440, width=8,
                   textvariable=self.blog_account_switch_wait_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", ipady=4)
        tk.Label(maf3, text=" 분  (다음 아이디 로그인 전 대기)", font=F_SM,
                 bg=BG_CARD, fg=FG_DIM).pack(side="left")
        r += 1
        self._lbl(form, "무한반복실행:", r)
        maf4 = tk.Frame(form, bg=BG_CARD)
        maf4.grid(row=r, column=1, sticky="w", pady=8)
        self.blog_infinite_loop_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            maf4, text="모든 아이디 사용 후 첫 아이디부터 반복",
            variable=self.blog_infinite_loop_var,
            font=F_SM, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD,
        ).pack(side="left")

        r += 1; _grid_sep(form, r, title="포스팅 설정")

        r += 1
        self._lbl(form, "발행 개수:", r)
        pcf = tk.Frame(form, bg=BG_CARD)
        pcf.grid(row=r, column=1, sticky="w", pady=8)
        self.blog_post_count_var = tk.IntVar(value=10)
        tk.Spinbox(pcf, from_=2, to=999, width=8,
                   textvariable=self.blog_post_count_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", ipady=4)
        tk.Label(pcf, text="  건", font=F_SM, bg=BG_CARD,
                 fg=FG_DIM).pack(side="left")

        r += 1
        self._lbl(form, "포스팅 주기:", r)
        ivf = tk.Frame(form, bg=BG_CARD)
        ivf.grid(row=r, column=1, sticky="w", pady=8)
        self.blog_interval_min_var = tk.IntVar(value=5)
        self.blog_interval_max_var = tk.IntVar(value=30)
        tk.Spinbox(ivf, from_=1, to=1440, width=6,
                   textvariable=self.blog_interval_min_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", ipady=4)
        tk.Label(ivf, text=" ~ ", font=F_SM, bg=BG_CARD, fg=FG_DIM).pack(side="left")
        tk.Spinbox(ivf, from_=1, to=1440, width=6,
                   textvariable=self.blog_interval_max_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", ipady=4)
        tk.Label(ivf, text="  분  (랜덤)", font=F_SM, bg=BG_CARD,
                 fg=FG_DIM).pack(side="left")

        r += 1
        self._lbl(form, "제목 키워드:", r)
        pnf = tk.Frame(form, bg=BG_CARD)
        pnf.grid(row=r, column=1, sticky="w", pady=8)
        self.blog_use_product_name_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            pnf, text="업체제품명 사용",
            variable=self.blog_use_product_name_var,
            font=F_SM, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD,
        ).grid(row=0, column=0, sticky="w")
        tk.Label(pnf, text="(제목에 검색된 상품명 사용)",
                 font=F_SM, bg=BG_CARD, fg=FG_DIM).grid(row=1, column=0, sticky="w")

        r += 1
        self._lbl(form, "키워드 반복 횟수:", r)
        ckf = tk.Frame(form, bg=BG_CARD)
        ckf.grid(row=r, column=1, sticky="w", pady=8)
        self.blog_kw_repeat_min_var = tk.IntVar(value=3)
        self.blog_kw_repeat_max_var = tk.IntVar(value=7)
        tk.Label(ckf, text="최소", font=F_SM, bg=BG_CARD,
                 fg=FG_LABEL).pack(side="left")
        tk.Spinbox(ckf, from_=0, to=20, width=8,
                   textvariable=self.blog_kw_repeat_min_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", padx=(6, 12), ipady=4)
        tk.Label(ckf, text="~ 최대", font=F_SM, bg=BG_CARD,
                 fg=FG_LABEL).pack(side="left")
        tk.Spinbox(ckf, from_=0, to=20, width=8,
                   textvariable=self.blog_kw_repeat_max_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", padx=(6, 12), ipady=4)
        tk.Label(ckf, text="회", font=F_SM, bg=BG_CARD,
                 fg=FG_DIM).pack(side="left")

        r += 1; _grid_sep(form, r, title="본문 설정")

        r += 1
        self._lbl(form, "줄바꿈 (모바일):", r)
        lbf = tk.Frame(form, bg=BG_CARD)
        lbf.grid(row=r, column=1, sticky="w", pady=8)
        self.blog_linebreak_var = tk.BooleanVar(value=False)
        self.blog_linebreak_cb = tk.Checkbutton(
            lbf, text="사용", variable=self.blog_linebreak_var,
            font=F, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD, command=self._toggle_blog_linebreak,
        )
        self.blog_linebreak_cb.pack(side="left")
        self.blog_maxchars_frame = tk.Frame(lbf, bg=BG_CARD)
        tk.Label(self.blog_maxchars_frame, text="  한줄 최대:", font=F_SM,
                 bg=BG_CARD, fg=FG_LABEL).pack(side="left")
        self.blog_maxchars_var = tk.IntVar(value=45)
        tk.Spinbox(self.blog_maxchars_frame, from_=20, to=100, width=6,
                   textvariable=self.blog_maxchars_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   ).pack(side="left", padx=(4, 0), ipady=3)
        tk.Label(self.blog_maxchars_frame, text=" 자", font=F_SM,
                 bg=BG_CARD, fg=FG_DIM).pack(side="left")

        r += 1
        self._lbl(form, "글자 배경색 적용 줄수:", r)
        bgf = tk.Frame(form, bg=BG_CARD)
        bgf.grid(row=r, column=1, sticky="w", pady=8)
        self.blog_bg_highlight_var = tk.IntVar(value=0)
        tk.Spinbox(bgf, from_=0, to=20, width=8,
                   textvariable=self.blog_bg_highlight_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", ipady=4)
        tk.Label(bgf, text="  줄  (0=미적용)", font=F_SM, bg=BG_CARD,
                 fg=FG_DIM).pack(side="left")

        r += 1
        self._lbl(form, "쿠팡 파트너스 수수료 이미지:", r)
        cif = tk.Frame(form, bg=BG_CARD)
        cif.grid(row=r, column=1, sticky="ew", pady=8)
        self.blog_commission_image_folder_var = tk.StringVar()
        _entry(cif, self.blog_commission_image_folder_var, readonly=True).pack(
            fill="x", pady=(0, 4))
        _soft_btn(cif, "찾아보기...", self._browse_blog_commission_image_folder).pack(
            anchor="w")
        r += 1
        tk.Label(form, text="(본문 하단에 삽입. 폴더 내 사진 중 랜덤 1장)",
                 font=F_SM, bg=BG_CARD, fg=FG_DIM, wraplength=280).grid(
            row=r, column=1, sticky="w", padx=(0, 8))

        tk.Label(inner, text="(상품 검색 탭의 키워드·API Key 사용)", font=F_SM,
                 bg=BG_CARD, fg=FG_DIM, anchor="w").pack(fill="x", ipady=6)

        self._load_blog_settings()
        self._toggle_blog_linebreak()

    def _toggle_blog_linebreak(self):
        """블로그 줄바꿈 설정 토글 — 체크 시 최대 글자수 입력 표시."""
        if getattr(self, "blog_linebreak_var", None) and self.blog_linebreak_var.get():
            if hasattr(self, "blog_maxchars_frame"):
                self.blog_maxchars_frame.pack(side="left")
        else:
            if hasattr(self, "blog_maxchars_frame"):
                self.blog_maxchars_frame.pack_forget()

    def _load_accounts_from_file(self, path):
        """txt 파일에서 아이디/비밀번호 로드. 형식: 아이디[TAB]비밀번호 (한 줄에 하나)"""
        accounts = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t", 1)
                    if len(parts) >= 2:
                        aid, apw = parts[0].strip(), parts[1].strip()
                        if aid and apw:
                            accounts.append({"id": aid, "pw": apw})
        except Exception:
            pass
        return accounts

    def _browse_blog_multi_account_file(self):
        p = filedialog.askopenfilename(
            title="다중아이디 파일 선택 (아이디 탭 비밀번호 형식)",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
        )
        if p:
            self.blog_multi_account_file_var.set(p)
            cnt = len(self._load_accounts_from_file(p))
            if cnt > 0:
                self._blog_log(f"[다중아이디] {cnt}개 계정 로드: {p}")
            else:
                self._blog_log(f"[다중아이디] 유효한 계정 없음 (형식: 아이디[TAB]비밀번호): {p}")

    def _browse_cafe_multi_account_file(self):
        p = filedialog.askopenfilename(
            title="다중아이디 파일 선택 (아이디 탭 비밀번호 형식)",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
        )
        if p:
            self.cafe_multi_account_file_var.set(p)
            cnt = len(self._load_accounts_from_file(p))
            if cnt > 0:
                self._cafe_log(f"[다중아이디] {cnt}개 계정 로드: {p}")
            else:
                self._cafe_log(f"[다중아이디] 유효한 계정 없음 (형식: 아이디[TAB]비밀번호): {p}")

    def _browse_blog_commission_image_folder(self):
        p = filedialog.askdirectory(title="쿠팡 파트너스 수수료 이미지 폴더 선택")
        if p:
            self.blog_commission_image_folder_var.set(p)
            self._blog_log(f"[설정] 수수료 이미지 폴더: {p}")

    def _build_blog_log(self, parent):
        sh, card = _card(parent, auto_height=False)
        sh.grid(row=0, column=1, sticky="nsew")

        tk.Label(card, text="활동 내역", font=F_SEC, bg=BG_CARD,
                 fg=FG, anchor="w").pack(fill="x", padx=12, pady=(12, 4))
        _sep(card)

        self.blog_log_text = tk.Text(
            card, font=F_LOG, bg=LOG_BG, fg=LOG_FG,
            relief="flat", wrap="word", state="disabled",
            highlightthickness=0, padx=10, pady=10,
        )
        self.blog_log_text.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self.blog_progress_var = tk.StringVar(value="대기 중")
        tk.Label(card, textvariable=self.blog_progress_var, font=F_SM,
                 bg=BG_CARD, fg=FG_LABEL, anchor="w").pack(fill="x", padx=12, pady=(0, 8))

    def _blog_log(self, msg):
        if "[BLOG]" in msg or "[CAFE]" in msg or "[실행시작]" in msg:
            self.append_log_global(msg)
        def _do():
            t = self.blog_log_text
            t.config(state="normal")
            t.insert("end", msg + "\n")
            t.see("end")
            t.config(state="disabled")
        if self.root.winfo_exists():
            self.root.after(0, _do)

    def _clear_blog_log(self):
        self.blog_log_text.config(state="normal")
        self.blog_log_text.delete("1.0", "end")
        self.blog_log_text.config(state="disabled")
        self.blog_progress_var.set("대기 중")

    def _save_blog_settings(self, silent=False):
        """silent=True: 자동재시작 시 확인 메시지 없이 저장"""
        try:
            data = {
                "blog_naver_id": self.blog_naver_id_var.get(),
                "blog_naver_pw": self.blog_naver_pw_var.get(),
                "blog_interval_min": self.blog_interval_min_var.get(),
                "blog_interval_max": self.blog_interval_max_var.get(),
                "blog_auto_start_cafe": self.blog_auto_start_cafe_var.get(),
                "blog_post_count": self.blog_post_count_var.get(),
                "blog_use_product_name": self.blog_use_product_name_var.get(),
                "blog_kw_repeat_min": self.blog_kw_repeat_min_var.get(),
                "blog_kw_repeat_max": self.blog_kw_repeat_max_var.get(),
                "blog_linebreak": self.blog_linebreak_var.get(),
                "blog_maxchars": self.blog_maxchars_var.get(),
                "blog_bg_highlight": self.blog_bg_highlight_var.get(),
                "blog_commission_image_folder": self.blog_commission_image_folder_var.get(),
                "blog_multi_account": self.blog_multi_account_var.get() if hasattr(self, "blog_multi_account_var") else False,
                "blog_multi_account_file": self.blog_multi_account_file_var.get() if hasattr(self, "blog_multi_account_file_var") else "",
                "blog_account_switch_wait": self.blog_account_switch_wait_var.get() if hasattr(self, "blog_account_switch_wait_var") else 5,
                "blog_infinite_loop": self.blog_infinite_loop_var.get() if hasattr(self, "blog_infinite_loop_var") else False,
            }
            path = os.path.join(BASE_DIR, "blog_settings.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if not silent:
                messagebox.showinfo("완료", "블로그 설정이 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패:\n{e}")

    def _load_blog_settings(self):
        try:
            path = os.path.join(BASE_DIR, "blog_settings.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.blog_naver_id_var.set(data.get("blog_naver_id", ""))
                self.blog_naver_pw_var.set(data.get("blog_naver_pw", ""))
                if "blog_interval_min" in data or "blog_interval_max" in data:
                    self.blog_interval_min_var.set(int(data.get("blog_interval_min", 5)))
                    self.blog_interval_max_var.set(int(data.get("blog_interval_max", 30)))
                else:
                    old = int(data.get("blog_interval", 5))
                    self.blog_interval_min_var.set(max(1, old // 2))
                    self.blog_interval_max_var.set(old)
                self.blog_auto_start_cafe_var.set(bool(data.get("blog_auto_start_cafe", False)))
                self.blog_post_count_var.set(max(2, int(data.get("blog_post_count", 10))))
                self.blog_use_product_name_var.set(bool(data.get("blog_use_product_name", False)))
                self.blog_kw_repeat_min_var.set(int(data.get("blog_kw_repeat_min", 3)))
                self.blog_kw_repeat_max_var.set(int(data.get("blog_kw_repeat_max", 7)))
                self.blog_linebreak_var.set(bool(data.get("blog_linebreak", False)))
                self.blog_maxchars_var.set(int(data.get("blog_maxchars", 45)))
                self.blog_bg_highlight_var.set(int(data.get("blog_bg_highlight", 0)))
                self.blog_commission_image_folder_var.set(data.get("blog_commission_image_folder", ""))
                if "blog_multi_account" in data:
                    self.blog_multi_account_var.set(bool(data.get("blog_multi_account", False)))
                if "blog_multi_account_file" in data:
                    self.blog_multi_account_file_var.set(data.get("blog_multi_account_file", ""))
                if "blog_account_switch_wait" in data:
                    self.blog_account_switch_wait_var.set(int(data.get("blog_account_switch_wait", 5)))
                if "blog_infinite_loop" in data:
                    self.blog_infinite_loop_var.set(bool(data.get("blog_infinite_loop", False)))
        except Exception:
            pass

    def run_blog_job(self, keywords, gemini_key, accounts):
        """블로그 포스팅 실제 작업 (백그라운드 스레드에서 호출)"""
        self.append_log_global("[BLOG] run_blog_job ENTER")
        self._blog_posting_worker(keywords, gemini_key, accounts)

    def _on_start_blog_posting(self, skip_confirm=False, cmd_id=None, program_username=None, task_keywords_override=None):
        """skip_confirm=True: 자동재시작 시 저장 확인 메시지 없이 진행. cmd_id/program_username: (레거시, 미사용).
        task_keywords_override: post_tasks에서 온 키워드 리스트 (통신시작 모드)."""
        self.worker_thread = None
        self._last_start_error = None
        if not self._require_login_and_session("blog"):
            self._last_start_error = "로그인/세션 필요"
            return
        is_task_run = bool(task_keywords_override and getattr(self, "_comm_current_task_id", None))
        if not is_task_run:
            try:
                from auth import get_session
                from shared.gui_data import fetch_user_coupang_keys
                s = get_session()
                uid = (s or {}).get("id")
                keys = fetch_user_coupang_keys(username=(s or {}).get("username"), user_id=uid, log=self._blog_log)
                if not keys and not (getattr(self, "coupang_ak_var", None) and self.coupang_ak_var.get().strip() and getattr(self, "coupang_sk_var", None) and self.coupang_sk_var.get().strip()):
                    messagebox.showwarning("안내", "쿠팡파트너스 키를 등록후 진행하세요.")
                    return
            except Exception:
                if not (getattr(self, "coupang_ak_var", None) and self.coupang_ak_var.get().strip() and getattr(self, "coupang_sk_var", None) and self.coupang_sk_var.get().strip()):
                    messagebox.showwarning("안내", "쿠팡파트너스 키를 등록후 진행하세요.")
                    return
        if task_keywords_override is not None:
            keywords = list(task_keywords_override) if task_keywords_override else []
            if not keywords:
                self._last_start_error = "task 키워드 없음"
                return
        else:
            use_paid = getattr(self, "use_paid_member_keywords_var", None) and self.use_paid_member_keywords_var.get()
            if use_paid and self._is_admin():
                try:
                    from shared.gui_data import fetch_paid_member_keywords_pool
                    post_count = max(2, self.blog_post_count_var.get())
                    keywords = fetch_paid_member_keywords_pool(count=post_count * 2, log=self._blog_log)
                    if not keywords:
                        self._last_start_error = "유료회원 키워드 없음"
                        messagebox.showwarning("안내", "유료회원 키워드가 없습니다. Supabase paid_members 테이블을 확인하세요.")
                        return
                except Exception as e:
                    self._last_start_error = f"유료회원 키워드 조회 실패: {e}"
                    messagebox.showerror("오류", f"유료회원 키워드 조회 실패:\n{e}")
                    return
            else:
                keywords = [k for k in (self.keywords or []) if k and str(k).strip()]
                if not keywords:
                    self._last_start_error = "키워드 없음"
                    messagebox.showwarning("안내", "키워드를 먼저 '상품 검색' 탭에서 불러오세요.")
                    return
        multi = getattr(self, "blog_multi_account_var", None) and self.blog_multi_account_var.get()
        if multi:
            path = getattr(self, "blog_multi_account_file_var", None) and self.blog_multi_account_file_var.get().strip()
            if not path or not os.path.isfile(path):
                self._last_start_error = "다중아이디 파일 없음"
                messagebox.showwarning("안내", "다중아이디 사용 시 아이디 파일을 불러오세요.")
                return
            accounts = self._load_accounts_from_file(path)
            if not accounts:
                self._last_start_error = "유효한 계정 없음"
                messagebox.showwarning("안내", "유효한 계정이 없습니다. 형식: 아이디[TAB]비밀번호 (한 줄에 하나)")
                return
        else:
            nid = self.blog_naver_id_var.get().strip()
            npw = self.blog_naver_pw_var.get().strip()
            if not nid or not npw:
                self._last_start_error = "네이버 아이디/비밀번호 없음"
                messagebox.showwarning("안내", "네이버 아이디와 비밀번호를 입력해주세요.")
                return
            accounts = [{"id": nid, "pw": npw}]
        gk = self.gemini_key_var.get().strip()
        if not gk:
            self._last_start_error = "Gemini API 키 없음"
            messagebox.showwarning("안내", "Gemini API 키를 입력해주세요.")
            return
        try:
            from blog_poster import run_auto_blogging
        except ImportError as e:
            self._last_start_error = f"블로그 모듈 로드 실패: {e}"
            messagebox.showerror("오류", f"블로그 포스팅 모듈을 불러올 수 없습니다.\n{e}")
            return
        self.is_blog_posting = True
        self._blog_stop_flag = False
        self._set_status("running", "블로그 포스팅 중...")
        self._clear_blog_log()
        self._blog_log("블로그 포스팅 시작...")
        self._save_blog_settings(silent=skip_confirm)
        if not use_paid:
            keywords = [k for k in (self.keywords or []) if k and str(k).strip()]
        random.shuffle(keywords)
        blog_task_user_id = getattr(self, "_comm_current_user_id", None) if task_keywords_override else None
        self.worker_thread = threading.Thread(
            target=self.run_blog_job,
            args=(keywords, gk, accounts),
            kwargs={"task_user_id": blog_task_user_id},
            daemon=True
        )
        self.worker_thread.start()

    def run_blog_job(self, keywords, gemini_key, accounts, task_user_id=None):
        """블로그 포스팅 실제 작업 (백그라운드 스레드에서 호출). task_user_id: post_tasks 태스크 소유자."""
        self.append_log_global("[BLOG] run_blog_job ENTER")
        self._blog_posting_worker(keywords, gemini_key, accounts, task_user_id=task_user_id)

    def _blog_posting_worker(self, keywords, gemini_key, accounts, task_user_id=None):
        """accounts: [{"id", "pw"}, ...] — 다중아이디 시 여러 계정, 단일 시 1개"""
        self._blog_log("[BLOG] worker started")
        import time
        try:
            from blog_poster import run_auto_blogging
            post_count = max(2, self.blog_post_count_var.get())
            iv_min = max(1, self.blog_interval_min_var.get())
            iv_max = max(iv_min, self.blog_interval_max_var.get())
            multi = getattr(self, "blog_multi_account_var", None) and self.blog_multi_account_var.get()
            infinite = getattr(self, "blog_infinite_loop_var", None) and self.blog_infinite_loop_var.get()
            wait_min = max(1, getattr(self, "blog_account_switch_wait_var", None) and self.blog_account_switch_wait_var.get() or 5)

            paid_members = []
            try:
                from shared.gui_data import fetch_paid_members
                self._blog_log("[Supabase] 유료회원 목록 조회 중...")
                paid_members = fetch_paid_members(log=self._blog_log)
            except ImportError:
                self._blog_log("[Supabase] supabase 패키지 미설치 — 본인 글만 발행합니다.")
            except Exception as e:
                self._blog_log(f"[Supabase] 조회 실패: {e} — 본인 글만 발행합니다.")

            referrer = None
            program_username = ""
            coupang_ak, coupang_sk = None, None
            try:
                from auth import get_session
                from shared.gui_data import fetch_referrer, fetch_user_coupang_keys
                s = get_session()
                program_username = (s or {}).get("username", "") or ""
                rid = (s or {}).get("referrer_id") if s else None
                if rid:
                    self._blog_log(f"[Supabase] 추천인 '{rid}' 조회 중...")
                    referrer = fetch_referrer(rid, log=self._blog_log)
                # 쿠팡 API 키: task_user_id 있으면 태스크 소유자(profiles)만 사용(fallback 없음). 없으면 세션+GUI.
                if (task_user_id or "").strip():
                    keys = fetch_user_coupang_keys(user_id=(task_user_id or "").strip(), log=self._blog_log)
                    if not keys:
                        self._blog_log("[통신] 태스크 소유자 쿠팡키 미등록 — 작업 스킵")
                        return
                    coupang_ak, coupang_sk = keys[0], keys[1]
                else:
                    coupang_uid = (s or {}).get("id")
                    keys = fetch_user_coupang_keys(username=program_username, user_id=coupang_uid, log=self._blog_log)
                    if keys:
                        coupang_ak, coupang_sk = keys[0], keys[1]
                    else:
                        coupang_ak = self.coupang_ak_var.get().strip() or None
                        coupang_sk = self.coupang_sk_var.get().strip() or None
            except Exception as e:
                self._blog_log(f"[Supabase] 조회 실패: {e}")
            if not coupang_ak or not coupang_sk:
                coupang_ak = self.coupang_ak_var.get().strip() or None
                coupang_sk = self.coupang_sk_var.get().strip() or None

            account_idx = 0
            total_success, total_fail, total_done = 0, 0, 0
            self.append_log_global("[BLOG] entering work loop")
            while True:
                if getattr(self, "_blog_stop_flag", False):
                    self._blog_log("[중지] 사용자가 작업을 중지했습니다.")
                    break
                acc = accounts[account_idx]
                nid, npw = acc["id"], acc["pw"]
                kw_list = keywords
                if multi and len(accounts) > 1:
                    self._blog_log(f"\n[다중아이디] {account_idx + 1}/{len(accounts)}번째 계정: {nid}")
                result = run_auto_blogging(
                    login_id=nid,
                    password=npw,
                    keywords=kw_list,
                    program_username=program_username,
                    gemini_api_key=gemini_key,
                    log=self._blog_log,
                    posting_interval_min=iv_min,
                    posting_interval_max=iv_max,
                    image_save_dir=self.img_dir_var.get().strip(),
                    keyword_repeat_min=self.blog_kw_repeat_min_var.get(),
                    keyword_repeat_max=self.blog_kw_repeat_max_var.get(),
                    coupang_access_key=coupang_ak,
                    coupang_secret_key=coupang_sk,
                    stop_flag=lambda: getattr(self, "_blog_stop_flag", False),
                    post_count=post_count,
                    use_product_name=self.blog_use_product_name_var.get(),
                    linebreak_enabled=self.blog_linebreak_var.get(),
                    linebreak_max_chars=self.blog_maxchars_var.get(),
                    commission_image_folder=self.blog_commission_image_folder_var.get().strip() or None,
                    bg_highlight_lines=self.blog_bg_highlight_var.get(),
                    paid_members=paid_members,
                    referrer=referrer,
                    category=self.selected_category.get() if hasattr(self, "selected_category") else "건강식품",
                )
                success = result.get("success", 0)
                fail = result.get("fail", 0)
                total = result.get("total", 0)
                total_success += success
                total_fail += fail
                total_done += total
                self.root.after(0, lambda s=success, f=fail, t=total: self._blog_log(f"\n완료: 성공 {s} / 실패 {f} / 총 {t}"))

                if getattr(self, "_blog_stop_flag", False):
                    break
                account_idx += 1
                if account_idx >= len(accounts):
                    if infinite:
                        account_idx = 0
                        self._blog_log(f"\n[무한반복] 첫 아이디부터 재시작. {wait_min}분 대기...")
                    else:
                        break
                if account_idx < len(accounts) or (infinite and account_idx == 0):
                    self._blog_log(f"\n[다중아이디] 다음 계정으로 전환. {wait_min}분 대기...")
                    wait_sec = min(wait_min * 60, 3600)
                    for _ in range(wait_sec):
                        if getattr(self, "_blog_stop_flag", False):
                            break
                        time.sleep(1)

            self.append_log_global("[BLOG] work loop exited")
            self.root.after(0, lambda: self._set_status("done", f"블로그 포스팅 완료: {total_success}/{total_done}"))
            if getattr(self, "blog_auto_start_cafe_var", None) and self.blog_auto_start_cafe_var.get():
                self.root.after(500, lambda: self._on_start_posting(skip_confirm=True))
            elif getattr(self, "_auto_restart_pending_cafe", False):
                self._auto_restart_pending_cafe = False
                self.root.after(500, lambda: self._on_start_posting(skip_confirm=True))
            elif getattr(self, "_auto_restart_enabled", False):
                self.root.after(0, self._schedule_auto_restart)
        except Exception as e:
            self.root.after(0, lambda: self._blog_log(f"오류: {e}"))
            self.root.after(0, lambda: self._set_status("error", str(e)))
            if getattr(self, "_auto_restart_enabled", False):
                self.root.after(0, self._schedule_auto_restart)
        finally:
            self.root.after(0, lambda: setattr(self, "is_blog_posting", False))
            self.root.after(0, lambda: setattr(self, "is_running", False))

    def _on_stop_blog_posting(self):
        self._blog_stop_flag = True
        self._blog_log("[중지] 블로그 포스팅 중지 요청됨...")

    # ═══════════════════════════════════════════════
    # PAGE 3 — 카페 포스팅
    # ═══════════════════════════════════════════════
    def _build_cafe_page(self):
        self.pg_cafe = tk.Frame(self.main_container, bg=BG)

        # 액션바 (상단)
        sh, card = _card(self.pg_cafe, pad=8)
        sh.pack(fill="x")
        bar = tk.Frame(card, bg=BG_CARD)
        bar.pack(fill="x", padx=4, pady=3)

        for txt, c, h, cmd in [
            ("카페주소 가져오기", POINT,  POINT_H,  self._on_load_cafe_list),
            ("카페 ID/메뉴 추출", POINT,  POINT_H,  self._open_cafe_extractor),
            ("설정 저장",         TEAL,   TEAL_H,   self._save_cafe_settings),
            ("설정 불러오기",     POINT,  POINT_H,  self._load_cafe_settings),
            ("발행 시작 ▶",      GREEN,  GREEN_H,  self._on_start_posting),
            ("발행 중지",         RED,    RED_H,    self._on_stop_posting),
            ("카페가입도우미",    PURPLE, PURPLE_H, self._open_cafe_autojoin),
        ]:
            _action_btn(bar, f" {txt} ", c, h, cmd).pack(
                side="left", padx=(0, 4))

        # 메인 콘텐츠 (설정 카드에 더 넓은 비율 배정 — 우측 짤림 방지)
        body = tk.Frame(self.pg_cafe, bg=BG)
        body.pack(fill="both", expand=True, pady=(S, 0))
        body.columnconfigure(0, weight=2, minsize=380)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_cafe_settings(body)
        self._build_cafe_log(body)

    # ── 카페 설정 카드 ──
    def _build_cafe_settings(self, parent):
        sh, card = _card(parent, auto_height=False)
        sh.grid(row=0, column=0, sticky="nsew", padx=(0, S // 2))

        # ── 스크롤 가능 영역 (포스팅 도우미 스타일) ──
        scroll_canvas = tk.Canvas(card, bg=BG_CARD, highlightthickness=0, bd=0)
        scrollbar = ModernScrollbar(card, command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        scroll_canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(scroll_canvas, bg=BG_CARD, padx=22, pady=16)
        inner_id = scroll_canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(e):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def _on_canvas_configure(e):
            scroll_canvas.itemconfig(inner_id, width=e.width)

        inner.bind("<Configure>", _on_inner_configure)
        scroll_canvas.bind("<Configure>", _on_canvas_configure)

        # 마우스 휠 스크롤
        def _on_mousewheel(e):
            scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        def _bind_wheel(e):
            scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(e):
            scroll_canvas.unbind_all("<MouseWheel>")

        scroll_canvas.bind("<Enter>", _bind_wheel)
        scroll_canvas.bind("<Leave>", _unbind_wheel)

        tk.Label(inner, text="카페 설정", font=F_TITLE, bg=BG_CARD,
                 fg=FG, anchor="w").pack(fill="x")
        _sep(inner)

        tk.Label(inner,
                 text="네이버 로그인 정보와 카페 리스트를 설정하세요. "
                      "발행 시작 시 자동으로 상품 검색 → Gemini 요약 → 포스팅이 진행됩니다.",
                 font=F_SM, bg=BG_CARD, fg=FG_LABEL, anchor="w",
                 wraplength=380, justify="left").pack(fill="x", pady=(0, 10))

        form = tk.Frame(inner, bg=BG_CARD)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        # ── 로그인 정보 ──
        r = 0
        self._lbl(form, "네이버 아이디:", r)
        idf = tk.Frame(form, bg=BG_CARD)
        idf.grid(row=r, column=1, sticky="ew", pady=8)
        self.naver_id_var = tk.StringVar()
        _entry(idf, self.naver_id_var).pack(fill="x")

        r += 1
        self._lbl(form, "네이버 비밀번호:", r)
        pwf = tk.Frame(form, bg=BG_CARD)
        pwf.grid(row=r, column=1, sticky="ew", pady=8)
        self.naver_pw_var = tk.StringVar()
        self.naver_pw_entry = _entry(pwf, self.naver_pw_var, show="●")
        self.naver_pw_entry.pack(side="left", fill="x", expand=True)
        _soft_btn(pwf, "표시", self._toggle_naver_pw).pack(
            side="left", padx=(4, 0))

        r += 1; _grid_sep(form, r, title="다중아이디 설정")
        r += 1
        self._lbl(form, "다중아이디 사용:", r)
        maf = tk.Frame(form, bg=BG_CARD)
        maf.grid(row=r, column=1, sticky="w", pady=8)
        self.cafe_multi_account_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            maf, text="활성화",
            variable=self.cafe_multi_account_var,
            font=F_SM, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD,
        ).pack(side="left")
        tk.Label(maf, text=" (아이디 탭 비밀번호 형식 txt 파일)", font=F_SM,
                 bg=BG_CARD, fg=FG_DIM).pack(side="left")
        r += 1
        self._lbl(form, "아이디 파일:", r)
        maf2 = tk.Frame(form, bg=BG_CARD)
        maf2.grid(row=r, column=1, sticky="ew", pady=8)
        maf2.columnconfigure(0, weight=1)
        self.cafe_multi_account_file_var = tk.StringVar()
        _entry(maf2, self.cafe_multi_account_file_var, readonly=True).pack(
            fill="x", pady=(0, 4))
        _soft_btn(maf2, "파일 불러오기", self._browse_cafe_multi_account_file).pack(anchor="w")
        r += 1
        self._lbl(form, "아이디 교체 대기시간:", r)
        maf3 = tk.Frame(form, bg=BG_CARD)
        maf3.grid(row=r, column=1, sticky="w", pady=8)
        self.cafe_account_switch_wait_var = tk.IntVar(value=5)
        tk.Spinbox(maf3, from_=1, to=1440, width=8,
                   textvariable=self.cafe_account_switch_wait_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", ipady=4)
        tk.Label(maf3, text=" 분  (다음 아이디 로그인 전 대기)", font=F_SM,
                 bg=BG_CARD, fg=FG_DIM).pack(side="left")
        r += 1
        self._lbl(form, "무한반복실행:", r)
        maf4 = tk.Frame(form, bg=BG_CARD)
        maf4.grid(row=r, column=1, sticky="w", pady=8)
        self.cafe_infinite_loop_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            maf4, text="모든 아이디 사용 후 첫 아이디부터 반복",
            variable=self.cafe_infinite_loop_var,
            font=F_SM, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD,
        ).pack(side="left")

        r += 1; _grid_sep(form, r, title="API / 파일 설정")

        r += 1
        self._lbl(form, "Gemini API Key:", r)
        gf = tk.Frame(form, bg=BG_CARD)
        gf.grid(row=r, column=1, sticky="ew", pady=8)
        tk.Label(gf, text="(상품 검색 탭의 API Key 사용)", font=F_SM,
                 bg=BG_CARD, fg=FG_DIM, anchor="w").pack(fill="x", ipady=6)

        r += 1
        cf = tk.Frame(form, bg=BG_CARD)
        cf.grid(row=r, column=0, columnspan=2, sticky="ew", pady=8)
        cf.columnconfigure(1, weight=1)
        # 상단: 라벨 + 입력창 한 줄
        tk.Label(cf, text="카페리스트 파일:", font=F_SM, bg=BG_CARD,
                 fg=FG_LABEL, anchor="e", padx=8).grid(row=0, column=0, sticky="e")
        self.cafe_file_var = tk.StringVar(value="cafe_list.txt")
        _entry(cf, self.cafe_file_var, readonly=True).grid(
            row=0, column=1, sticky="ew", padx=(0, 8))
        # 하단: 찾아보기 버튼 (입력창과 같은 열, 왼쪽 정렬)
        _soft_btn(cf, "찾아보기...", self._on_load_cafe_list).grid(
            row=1, column=1, sticky="w", pady=(4, 0))

        r += 1; _grid_sep(form, r, title="검색 설정")

        r += 1
        self._lbl(form, "키워드 반복 횟수:", r)
        ckf = tk.Frame(form, bg=BG_CARD)
        ckf.grid(row=r, column=1, sticky="w", pady=8)

        self.cafe_kw_repeat_min_var = tk.IntVar(value=3)
        self.cafe_kw_repeat_max_var = tk.IntVar(value=7)

        tk.Label(ckf, text="최소", font=F_SM, bg=BG_CARD,
                 fg=FG_LABEL).pack(side="left")
        tk.Spinbox(ckf, from_=0, to=20, width=8,
                   textvariable=self.cafe_kw_repeat_min_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", padx=(6, 12), ipady=4)
        tk.Label(ckf, text="~ 최대", font=F_SM, bg=BG_CARD,
                 fg=FG_LABEL).pack(side="left")
        tk.Spinbox(ckf, from_=0, to=20, width=8,
                   textvariable=self.cafe_kw_repeat_max_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", padx=(6, 12), ipady=4)
        tk.Label(ckf, text="회", font=F_SM, bg=BG_CARD,
                 fg=FG_DIM).pack(side="left")

        r += 1; _grid_sep(form, r, title="포스팅 설정")

        r += 1
        self._lbl(form, "발행 카테고리:", r)
        catf = tk.Frame(form, bg=BG_CARD)
        catf.grid(row=r, column=1, sticky="w", pady=8)
        self.selected_category = tk.StringVar(value="건강식품")
        ttk.Combobox(
            catf, textvariable=self.selected_category,
            values=["건강식품", "생활용품", "가전제품", "유아/출산", "기타"],
            state="readonly", width=14, font=F_SM,
        ).pack(side="left")

        r += 1
        self._lbl(form, "발행 개수:", r)
        pcf = tk.Frame(form, bg=BG_CARD)
        pcf.grid(row=r, column=1, sticky="w", pady=8)

        self.cafe_post_count_var = tk.IntVar(value=10)
        tk.Spinbox(pcf, from_=2, to=999, width=8,
                   textvariable=self.cafe_post_count_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", ipady=4)
        tk.Label(pcf, text="  건  (카페당 발행할 글 수)", font=F_SM, bg=BG_CARD,
                 fg=FG_DIM, wraplength=200).pack(side="left")

        r += 1
        self._lbl(form, "포스팅 주기:", r)
        ivf = tk.Frame(form, bg=BG_CARD)
        ivf.grid(row=r, column=1, sticky="w", pady=8)

        self.cafe_interval_min_var = tk.IntVar(value=5)
        self.cafe_interval_max_var = tk.IntVar(value=30)
        tk.Spinbox(ivf, from_=1, to=1440, width=6,
                   textvariable=self.cafe_interval_min_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", ipady=4)
        tk.Label(ivf, text=" ~ ", font=F_SM, bg=BG_CARD, fg=FG_DIM).pack(side="left")
        tk.Spinbox(ivf, from_=1, to=1440, width=6,
                   textvariable=self.cafe_interval_max_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   selectbackground="#cfe8ff", selectforeground=FG,
                   ).pack(side="left", ipady=4)
        tk.Label(ivf, text="  분  (랜덤)", font=F_SM, bg=BG_CARD,
                 fg=FG_DIM).pack(side="left")

        r += 1
        self._lbl(form, "제목 키워드:", r)
        pnf = tk.Frame(form, bg=BG_CARD)
        pnf.grid(row=r, column=1, sticky="w", pady=8)
        # 상단: 체크박스 같은 줄
        self.cafe_use_product_name_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            pnf, text="업체제품명 사용",
            variable=self.cafe_use_product_name_var,
            font=F_SM, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD,
        ).grid(row=0, column=0, sticky="w")
        # 아랫줄: (제목에 검색된 상품명 사용)
        tk.Label(pnf, text="(제목에 검색된 상품명 사용)",
                 font=F_SM, bg=BG_CARD, fg=FG_DIM).grid(row=1, column=0, sticky="w")

        r += 1; _grid_sep(form, r, title="본문 설정")

        r += 1
        self._lbl(form, "줄바꿈 (모바일):", r)
        lbf = tk.Frame(form, bg=BG_CARD)
        lbf.grid(row=r, column=1, sticky="w", pady=8)

        self.cafe_linebreak_var = tk.BooleanVar(value=False)
        self.cafe_linebreak_cb = tk.Checkbutton(
            lbf, text="사용", variable=self.cafe_linebreak_var,
            font=F, bg=BG_CARD, fg=FG, activebackground=BG_CARD,
            selectcolor=BG_CARD, command=self._toggle_linebreak,
        )
        self.cafe_linebreak_cb.pack(side="left")

        r += 1
        self._lbl(form, "쿠팡 파트너스 수수료 이미지:", r)
        cif = tk.Frame(form, bg=BG_CARD)
        cif.grid(row=r, column=1, sticky="ew", pady=8)
        self.commission_image_folder_var = tk.StringVar()
        _entry(cif, self.commission_image_folder_var, readonly=True).pack(
            fill="x", pady=(0, 4))
        _soft_btn(cif, "찾아보기...", self._browse_commission_image_folder).pack(
            anchor="w")
        r += 1
        tk.Label(form, text="(본문 하단에 삽입. 폴더 내 사진 중 랜덤 1장)",
                 font=F_SM, bg=BG_CARD, fg=FG_DIM, wraplength=280).grid(
            row=r, column=1, sticky="w", padx=(0, 8))

        self.cafe_maxchars_frame = tk.Frame(lbf, bg=BG_CARD)
        tk.Label(self.cafe_maxchars_frame, text="  한줄 최대:", font=F_SM,
                 bg=BG_CARD, fg=FG_LABEL).pack(side="left")
        self.cafe_maxchars_var = tk.IntVar(value=45)
        tk.Spinbox(self.cafe_maxchars_frame, from_=20, to=100, width=6,
                   textvariable=self.cafe_maxchars_var,
                   font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                   buttonbackground=BG_HEADER,
                   highlightthickness=2, highlightbackground=BD,
                   highlightcolor=BD_FOCUS,
                   ).pack(side="left", padx=(4, 0), ipady=3)
        tk.Label(self.cafe_maxchars_frame, text=" 자", font=F_SM,
                 bg=BG_CARD, fg=FG_DIM).pack(side="left")
        # 초기 숨김

        # (링크 버튼 이미지 설정 제거 — 댓글 방식으로 전환)
        self.link_btn_img_var = tk.StringVar(value="")  # 하위호환 유지

        _sep(inner)

        # 카페 리스트
        self._sec(inner, "등록된 카페 리스트")

        hdr = tk.Frame(inner, bg=BG_HEADER)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  #", font=F_SMB, bg=BG_HEADER, fg=FG_LABEL,
                 width=4, anchor="w").pack(side="left")
        tk.Label(hdr, text="카페 번호", font=F_SMB, bg=BG_HEADER, fg=FG_LABEL,
                 width=20, anchor="w").pack(side="left", padx=4)
        tk.Label(hdr, text="메뉴 번호", font=F_SMB, bg=BG_HEADER, fg=FG_LABEL,
                 width=15, anchor="w").pack(side="left")

        lf = tk.Frame(inner, bg=BG_CARD)
        lf.pack(fill="both", expand=True)

        self.cafe_listbox = tk.Listbox(
            lf, font=F_MONO, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
            highlightthickness=2, highlightbackground=BD, highlightcolor=BD_FOCUS,
            selectbackground=POINT, selectforeground=FG_WHITE,
            activestyle="none", height=6,
        )
        csb = tk.Scrollbar(lf, command=self.cafe_listbox.yview)
        csb.pack(side="right", fill="y")
        self.cafe_listbox.config(yscrollcommand=csb.set)
        self.cafe_listbox.pack(fill="both", expand=True)

        self.cafe_count_label = tk.Label(inner, text="0개 카페 등록됨",
                                          font=F_SM, bg=BG_CARD,
                                          fg=FG_LABEL, anchor="w")
        self.cafe_count_label.pack(fill="x", pady=(4, 0))

        cafe_btn_row = tk.Frame(inner, bg=BG_CARD)
        cafe_btn_row.pack(fill="x", pady=(6, 0))
        _action_btn(cafe_btn_row, " 선택삭제 ", RED, RED_H, self._on_cafe_delete_selected).pack(side="left", padx=(0, 8))
        _action_btn(cafe_btn_row, " 리셋 ", ORANGE, ORANGE_H, self._on_cafe_reset).pack(side="left", padx=(0, 8))
        _action_btn(cafe_btn_row, " 저장 ", TEAL, TEAL_H, self._on_cafe_save).pack(side="left")

        _sep(inner)

        # 도우미 기본 카페리스트 (서버에서 불러옴)
        self._sec(inner, "도우미 기본 카페리스트")
        helper_row = tk.Frame(inner, bg=BG_CARD)
        helper_row.pack(fill="x", pady=(0, 4))
        self.helper_cafe_mode_var = tk.StringVar(value="")  # "all" | ""
        tk.Radiobutton(helper_row, text="모두사용", variable=self.helper_cafe_mode_var, value="all",
                       font=F_SM, bg=BG_CARD, fg=FG, anchor="w",
                       activebackground=BG_CARD, activeforeground=FG, selectcolor=BG_CARD,
                       command=self._on_helper_mode_change).pack(side="left", padx=(0, 12))
        tk.Radiobutton(helper_row, text="사용 안 함", variable=self.helper_cafe_mode_var, value="",
                       font=F_SM, bg=BG_CARD, fg=FG_DIM, anchor="w",
                       activebackground=BG_CARD, activeforeground=FG, selectcolor=BG_CARD,
                       command=self._on_helper_mode_change).pack(side="left", padx=(0, 12))
        helper_row2 = tk.Frame(inner, bg=BG_CARD)
        helper_row2.pack(fill="x", pady=(4, 0))
        _action_btn(helper_row2, " 적용 ", TEAL, TEAL_H, self._on_helper_apply).pack(side="left")
        self.helper_cafe_count_label = tk.Label(helper_row2, text="(서버에서 불러옴)",
                                                font=F_SM, bg=BG_CARD, fg=FG_DIM, anchor="w")
        self.helper_cafe_count_label.pack(side="left", padx=(12, 0))
        helper_row3 = tk.Frame(inner, bg=BG_CARD)
        helper_row3.pack(fill="x", pady=(8, 4))
        _action_btn(helper_row3, " 신규카페 리스트 다운로드 ", POINT, POINT_H, self._on_helper_download_new).pack(side="left", padx=(0, 8))
        _action_btn(helper_row3, " 전체카페리스트 다운로드 ", POINT, POINT_H, self._on_helper_download_all).pack(side="left")
        self.helper_new_cafe_label = tk.Label(inner, text="", font=F_SM, bg=BG_CARD, fg=RED, anchor="w")
        self.helper_new_cafe_label.pack(fill="x", pady=(12, 8))

        _sep(inner)

        # 포스팅 진행
        pf = tk.Frame(inner, bg=BG_CARD)
        pf.pack(fill="x")
        tk.Label(pf, text="포스팅 진행:", font=FB, bg=BG_CARD,
                 fg=FG_LABEL).pack(side="left")

        self.cafe_progress_canvas = tk.Canvas(pf, height=22, bg=SEP,
                                               highlightthickness=0, bd=0)
        self.cafe_progress_canvas.pack(side="left", fill="x", expand=True,
                                        padx=(8, 0))
        self.cafe_progress_bar = self.cafe_progress_canvas.create_rectangle(
            0, 0, 0, 22, fill=GREEN, outline="")
        self.cafe_progress_text = self.cafe_progress_canvas.create_text(
            8, 11, text="대기 중", anchor="w", font=F_SM, fill=FG_LABEL)

    # ── 카페 로그 카드 (posting_help 활동 내역) ──
    def _build_cafe_log(self, parent):
        sh, card = _card(parent, auto_height=False)
        sh.grid(row=0, column=1, sticky="nsew", padx=(S // 2, 0))

        inner = tk.Frame(card, bg=BG_CARD, padx=16, pady=16)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text="포스팅 활동 로그", font=F_SEC,
                 bg=BG_CARD, fg=FG, anchor="w").pack(fill="x", pady=(0, S))

        log_wrap = tk.Frame(inner, bg=LOG_BG, highlightthickness=2,
                             highlightbackground=BD)
        log_wrap.pack(fill="both", expand=True)

        self.cafe_log_text = tk.Text(
            log_wrap, wrap="word", font=F_LOG,
            bg=LOG_BG, fg=LOG_FG, relief="flat", padx=12, pady=10,
            insertbackground=FG, selectbackground="#cfe8ff",
            selectforeground=FG, borderwidth=0, spacing1=2,
        )
        clsb = ModernScrollbar(log_wrap, command=self.cafe_log_text.yview)
        clsb.pack(side="right", fill="y")
        self.cafe_log_text.config(yscrollcommand=clsb.set)
        self.cafe_log_text.pack(fill="both", expand=True)
        self.cafe_log_text.config(state="disabled")

    # ──────────────────────────────────────────────
    # KEYWORDS
    # ──────────────────────────────────────────────
    def _on_load_keywords(self):
        p = filedialog.askopenfilename(
            title="키워드 파일 선택",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")])
        if p:
            self._load_keywords_file(p)

    def _load_keywords_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            # 콤마(,)로 구분된 키워드 파싱 (줄바꿈도 구분자로 처리)
            self.keywords = [kw.strip() for kw in content.replace("\n", ",").split(",") if kw.strip()]
            self.file_var.set(os.path.basename(path))
            self.kw_listbox.delete(0, "end")
            for kw in self.keywords:
                self.kw_listbox.insert("end", kw)
            self.kw_listbox.select_set(0, "end")
            self.kw_count.config(text=f"{len(self.keywords)}개 키워드")
            self._log(f"[키워드] {len(self.keywords)}개 로드 ← {path}")
        except Exception as e:
            messagebox.showerror("오류", f"파일 읽기 실패:\n{e}")

    def _open_distribute_keywords_dialog(self):
        """추천인 포스팅발행 키워드·카테고리 등록 다이얼로그"""
        try:
            from auth import get_session, update_distribute_keywords, get_distribute_keywords, get_distribute_category
        except ImportError:
            messagebox.showwarning("안내", "로그인이 필요합니다.")
            return
        s = get_session()
        if not s or not s.get("id"):
            messagebox.showwarning("안내", "로그인이 필요합니다.")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("추천인 포스팅발행 키워드·카테고리 등록")
        dlg.configure(bg=BG_CARD)
        dlg.resizable(True, True)
        dlg.grab_set()
        w, h = 520, 360
        x = self.root.winfo_x() + max(0, (self.root.winfo_width() - w) // 2)
        y = self.root.winfo_y() + max(0, (self.root.winfo_height() - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        pad = 20

        tk.Label(dlg, text="추천인 포스팅발행 키워드 (콤마로 구분, 한 줄)",
                 font=F_TITLE, bg=BG_CARD, fg=FG).pack(pady=(pad, 8))
        tk.Label(dlg, text="나를 추천인으로 등록한 사용자가 있을경우 포스팅시 교차발행으로 등록될 키워드를 설정합니다.",
                 font=F_SM, bg=BG_CARD, fg=FG_LABEL, wraplength=w - 40).pack(pady=(0, 4))
        tk.Label(dlg, text="3000자 이하(약 1000개 키워드)",
                 font=F_SM, bg=BG_CARD, fg=FG_DIM).pack(pady=(0, 10))

        btn_row = tk.Frame(dlg, bg=BG_CARD)
        btn_row.pack(fill="x", padx=pad, pady=(0, 6))
        _action_btn(btn_row, " 파일 불러오기 ", TEAL, TEAL_H, lambda: _load_file()).pack(side="left", padx=(0, 8))

        txt_frame = tk.Frame(dlg, bg=BG_CARD)
        txt_frame.pack(fill="both", expand=True, padx=pad, pady=(0, 10))

        text_var = tk.StringVar(value=get_distribute_keywords(s.get("id"), log=self._log))
        text_entry = tk.Entry(txt_frame, textvariable=text_var, font=F, bg=BG_INPUT, fg=FG,
                             relief="flat", highlightthickness=1, highlightbackground=BD, highlightcolor=BD_FOCUS)
        text_entry.pack(fill="x", ipady=8, ipadx=10)

        # 카테고리 선택
        cat_row = tk.Frame(dlg, bg=BG_CARD)
        cat_row.pack(fill="x", padx=pad, pady=(10, 0))
        tk.Label(cat_row, text="발행 카테고리:", font=F_SM, bg=BG_CARD, fg=FG_LABEL, width=12, anchor="e").pack(side="left", padx=(0, 8))
        _DISTRIBUTE_CATEGORIES = ["건강식품", "생활용품", "가전제품", "유아/출산", "기타"]
        category_var = tk.StringVar(value=get_distribute_category(s.get("id"), log=self._log))
        ttk.Combobox(cat_row, textvariable=category_var, values=_DISTRIBUTE_CATEGORIES,
                     state="readonly", width=14, font=F_SM).pack(side="left")

        msg_lbl = tk.Label(dlg, text="", font=F_SM, bg=BG_CARD, fg=GREEN)
        msg_lbl.pack(pady=(4, 0))

        DISTRIBUTE_MAX_LEN = 3000

        def _load_file():
            p = filedialog.askopenfilename(
                title="키워드 파일 선택",
                filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")])
            if p:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        content = f.read()
                    content = ",".join(c.strip() for c in content.replace("\n", ",").split(",") if c.strip())
                    if len(content) > DISTRIBUTE_MAX_LEN:
                        content = content[:DISTRIBUTE_MAX_LEN]
                        msg_lbl.config(text=f"3000자 초과하여 앞 3000자만 적용됨 ({len(content)}자)", fg=ORANGE)
                    else:
                        msg_lbl.config(text="파일 로드 완료", fg=GREEN)
                    text_var.set(content)
                except Exception as e:
                    msg_lbl.config(text=f"파일 읽기 실패: {e}", fg=RED)

        def _send():
            val = text_var.get().strip()
            if len(val) > DISTRIBUTE_MAX_LEN:
                msg_lbl.config(text=f"3000자 이하로 입력해주세요. (현재 {len(val)}자)", fg=RED)
                return
            ok, msg = update_distribute_keywords(s.get("id"), val, category_var.get(), log=self._log)
            msg_lbl.config(text=msg, fg=GREEN if ok else RED)
            if ok:
                dlg.after(800, dlg.destroy)

        btn_f = tk.Frame(dlg, bg=BG_CARD)
        btn_f.pack(fill="x", padx=pad, pady=(0, pad))
        _action_btn(btn_f, " 전송 ", TEAL, TEAL_H, _send).pack(side="left", padx=(0, 8))
        _action_btn(btn_f, " 취소 ", "#6b7280", "#545c66", dlg.destroy).pack(side="left")

    def _select_all_kw(self):
        self.kw_listbox.select_set(0, "end")

    def _deselect_all_kw(self):
        self.kw_listbox.selection_clear(0, "end")

    # ──────────────────────────────────────────────
    # API KEY
    # ──────────────────────────────────────────────
    def _toggle_key(self):
        cur = self.gemini_entry.cget("show")
        self.gemini_entry.config(show="" if cur == "●" else "●")

    def _toggle_coupang_ak(self):
        cur = self.coupang_ak_entry.cget("show")
        self.coupang_ak_entry.config(show="" if cur == "●" else "●")

    def _toggle_coupang_sk(self):
        cur = self.coupang_sk_entry.cget("show")
        self.coupang_sk_entry.config(show="" if cur == "●" else "●")

    def _auto_save_api_keys(self):
        """API 키 변경 시 자동 저장 (디바운스 500ms)"""
        if hasattr(self, '_api_save_timer') and self._api_save_timer is not None:
            self.root.after_cancel(self._api_save_timer)
        self._api_save_timer = self.root.after(500, self._do_auto_save_api_keys)

    def _do_auto_save_api_keys(self):
        """실제 API 키 자동 저장 수행"""
        self._api_save_timer = None
        gk = self.gemini_key_var.get().strip()
        ak = self.coupang_ak_var.get().strip()
        sk = self.coupang_sk_var.get().strip()
        if not gk and not ak and not sk:
            return
        data = {}
        if os.path.exists(API_KEYS_FILE):
            try:
                with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        if gk:
            data["gemini_api_key"] = gk
        if ak:
            data["coupang_access_key"] = ak
        if sk:
            data["coupang_secret_key"] = sk
        try:
            with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _save_api_key(self):
        gk = self.gemini_key_var.get().strip()
        ak = self.coupang_ak_var.get().strip()
        sk = self.coupang_sk_var.get().strip()
        if not gk and not ak and not sk:
            messagebox.showwarning("안내", "저장할 API 키를 입력하세요.")
            return
        data = {}
        if os.path.exists(API_KEYS_FILE):
            try:
                with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        if gk:
            data["gemini_api_key"] = gk
        if ak:
            data["coupang_access_key"] = ak
        if sk:
            data["coupang_secret_key"] = sk
        with open(API_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._log("[설정] 모든 API 키 저장 완료")

    def _load_api_key(self):
        self._load_api_key_silent()
        loaded = []
        if self.gemini_key_var.get():
            loaded.append("Gemini")
        if self.coupang_ak_var.get():
            loaded.append("쿠팡")
        if loaded:
            self._log(f"[설정] API 키 불러오기 완료: {', '.join(loaded)}")
        else:
            messagebox.showinfo("안내", "저장된 키가 없습니다.")

    def _load_api_key_silent(self):
        if os.path.exists(API_KEYS_FILE):
            try:
                with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                k = data.get("gemini_api_key", "")
                if k:
                    self.gemini_key_var.set(k)
                ak = data.get("coupang_access_key", "")
                if ak:
                    self.coupang_ak_var.set(ak)
                sk = data.get("coupang_secret_key", "")
                if sk:
                    self.coupang_sk_var.set(sk)
            except Exception:
                pass

    # ──────────────────────────────────────────────
    def _toggle_naver_pw(self):
        cur = self.naver_pw_entry.cget("show")
        self.naver_pw_entry.config(show="" if cur == "●" else "●")

    def _toggle_linebreak(self):
        """줄바꿈 설정 토글 — 체크 시 최대 글자수 입력 표시."""
        if self.cafe_linebreak_var.get():
            self.cafe_maxchars_frame.pack(side="left")
        else:
            self.cafe_maxchars_frame.pack_forget()

    def _browse_img_dir(self):
        p = filedialog.askdirectory(title="이미지 저장 폴더 선택")
        if p:
            self.img_dir_var.set(p)
            self._log(f"[설정] 이미지 저장 경로: {p}")

    def _browse_commission_image_folder(self):
        p = filedialog.askdirectory(title="쿠팡 파트너스 수수료 이미지 폴더 선택")
        if p:
            self.commission_image_folder_var.set(p)
            self._cafe_log(f"[설정] 수수료 이미지 폴더: {p}")

    # ──────────────────────────────────────────────
    # CAFE LIST
    # ──────────────────────────────────────────────
    def _on_cafe_delete_selected(self):
        """선택된 카페를 리스트에서 삭제"""
        sel = list(self.cafe_listbox.curselection())
        if not sel:
            messagebox.showinfo("안내", "삭제할 카페를 선택해주세요.")
            return
        for i in reversed(sel):
            del self.cafe_list[i]
        self.cafe_listbox.delete(0, "end")
        for i, c in enumerate(self.cafe_list, 1):
            self.cafe_listbox.insert("end", f"  {i:>3}    {c['cafe_id']:<20}  {c['menu_id']}")
        self.cafe_count_label.config(text=f"{len(self.cafe_list)}개 카페 등록됨")
        self._cafe_log(f"[카페] 선택 항목 {len(sel)}개 삭제됨")

    def _on_cafe_reset(self):
        """등록된 카페 리스트 전체 초기화"""
        if not self.cafe_list:
            messagebox.showinfo("안내", "등록된 카페가 없습니다.")
            return
        if not messagebox.askyesno("확인", "등록된 카페 리스트를 모두 초기화할까요?"):
            return
        self.cafe_list = []
        self.cafe_listbox.delete(0, "end")
        self.cafe_count_label.config(text="0개 카페 등록됨")
        self._cafe_log("[카페] 리스트 초기화됨")

    def _on_cafe_save(self):
        """등록된 카페 리스트를 파일로 저장"""
        if not self.cafe_list:
            messagebox.showinfo("안내", "저장할 카페가 없습니다.")
            return
        path = os.path.join(BASE_DIR, self.cafe_file_var.get())
        try:
            with open(path, "w", encoding="utf-8") as f:
                for c in self.cafe_list:
                    f.write(f"{c['cafe_id']},{c['menu_id']}\n")
            self._save_cafe_settings()
            self._cafe_log(f"[카페] {len(self.cafe_list)}개 카페 저장됨 ← {path}")
            messagebox.showinfo("완료", f"{path}\n{len(self.cafe_list)}개 카페가 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"파일 저장 실패:\n{e}")

    def _on_load_cafe_list(self):
        p = filedialog.askopenfilename(
            title="카페 리스트 파일 선택",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")])
        if p:
            self._load_cafe_list_file(p)

    def _open_cafe_extractor(self):
        """카페 URL → 카페 ID / 메뉴 ID 추출 팝업"""
        dlg = tk.Toplevel(self.root)
        dlg.title("카페 ID 메뉴ID 추출")
        dlg.configure(bg=BG)
        dlg.resizable(True, True)
        dlg.geometry("500x630")
        pad = 16

        # 둥근 카드로 전체 감싸기
        sh, card = _card(dlg, pad=pad)
        sh.pack(fill="both", expand=True, padx=pad, pady=pad)

        # 1. 카페 URL
        tk.Label(card, text="1. 카페 URL:", font=F_SM, bg=BG_CARD, fg=FG).pack(anchor="w", pady=(0, 4))
        url_var = tk.StringVar(value="https://cafe.naver.com/")
        url_entry = _entry(card, url_var)
        url_entry.pack(fill="x", pady=(0, 8))

        # 정보 조회 버튼
        def _on_fetch():
            url = url_var.get().strip()
            if not url:
                messagebox.showwarning("안내", "카페 URL을 입력해주세요.", parent=dlg)
                return
            cafe_id_var.set("조회 중...")
            for c in tree.get_children():
                tree.delete(c)
            dlg.update()

            def _do():
                try:
                    from cafe_extractor import extract_cafe_info
                    result = extract_cafe_info(url)
                    self.root.after(0, lambda: _apply_result(result))
                except Exception as e:
                    self.root.after(0, lambda: _apply_result({"cafe_id": None, "menus": [], "error": str(e)}))

            def _apply_result(result):
                err = result.get("error")
                if err:
                    cafe_id_var.set("")
                    messagebox.showerror("오류", err, parent=dlg)
                    return
                cid = result.get("cafe_id") or ""
                cafe_id_var.set(cid)
                for m in result.get("menus", []):
                    tree.insert("", "end", values=(m.get("type", "일반"), m.get("menu_name", ""), m.get("menu_id", "")))

            threading.Thread(target=_do, daemon=True).start()

        btn_frame = tk.Frame(card, bg=BG_CARD)
        btn_frame.pack(fill="x", pady=(0, 8))
        _action_btn(btn_frame, " 정보 조회 하기 ", TEAL, TEAL_H, _on_fetch).pack(side="left")

        # 2. 카페 ID 결과 (둥근 Entry, 연한 하늘색)
        tk.Label(card, text="- 카페 ID:", font=F_SM, bg=BG_CARD, fg=FG).pack(anchor="w", pady=(8, 4))
        cafe_id_var = tk.StringVar()
        cafe_id_entry = _entry(card, cafe_id_var, readonly=True, fill="#e0f2fe")
        cafe_id_entry.pack(fill="x", pady=(0, 8))

        # 3. 메뉴 테이블 (둥근 카드로 감싸기)
        tk.Label(card, text="- 메뉴 목록:", font=F_SM, bg=BG_CARD, fg=FG).pack(anchor="w", pady=(4, 4))
        tree_card_sh, tree_card = _card(card, pad=10, auto_height=False)
        tree_card_sh.pack(fill="x", pady=(0, 16))
        tree_frame = tk.Frame(tree_card, bg=BG_CARD)
        tree_frame.pack(fill="both", expand=True, padx=2, pady=(0, 20))
        cols = ("종류", "메뉴", "메뉴번호")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=7, selectmode="browse")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=80 if c == "종류" else 180 if c == "메뉴" else 80)
        tree.pack(side="left", fill="both", expand=True)
        tvsb = ModernScrollbar(tree_frame, command=tree.yview)
        tvsb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=tvsb.set)

        # 4. 리스트에 추가 버튼
        def _on_add_to_list():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("안내", "메뉴를 선택해주세요.", parent=dlg)
                return
            cid = cafe_id_var.get()
            if not cid:
                messagebox.showinfo("안내", "먼저 정보 조회를 실행해주세요.", parent=dlg)
                return
            item = tree.item(sel[0])
            vals = item.get("values", [])
            if len(vals) >= 3:
                menu_id = str(vals[2])
                self.cafe_list.append({"cafe_id": cid, "menu_id": menu_id})
                self.cafe_listbox.delete(0, "end")
                for i, c in enumerate(self.cafe_list, 1):
                    self.cafe_listbox.insert("end", f"  {i:>3}    {c['cafe_id']:<20}  {c['menu_id']}")
                self.cafe_count_label.config(text=f"{len(self.cafe_list)}개 카페 등록됨")
                self._cafe_log(f"[카페] 추가: {cid} / {menu_id}")
                messagebox.showinfo("완료", "포스팅 리스트에 추가되었습니다.", parent=dlg)

        _action_btn(card, " 리스트에 추가 ", GREEN, GREEN_H, _on_add_to_list).pack(pady=(4, 16))

    def _open_cafe_autojoin(self):
        """카페가입도우미 — 도우미 카페 리스트로 자동 가입 (cafe_autojoin 모듈)"""
        nid = self.naver_id_var.get().strip()
        npw = self.naver_pw_var.get().strip()
        if not nid or not npw:
            messagebox.showwarning("안내", "네이버 아이디와 비밀번호를 먼저 입력해주세요.")
            return
        # helper_cafes 테이블의 cafe_url 필드 사용 (Supabase helper_cafes)
        cafes = getattr(self, "helper_cafes", [])
        if not cafes:
            messagebox.showwarning("안내", "가입할 카페가 없습니다.\n'도우미 적용'으로 서버 카페리스트를 불러오세요.")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("카페가입도우미")
        dlg.configure(bg=BG)
        dlg.resizable(True, True)
        dlg.geometry("420x280")
        pad = 16
        sh, card = _card(dlg, pad=pad)
        sh.pack(fill="both", expand=True, padx=pad, pady=pad)
        tk.Label(card, text="카페가입도우미", font=F_TITLE, bg=BG_CARD, fg=FG).pack(anchor="w", pady=(0, 8))
        _sep(card)
        tk.Label(card, text=f"가입 대상: {len(cafes)}개 카페", font=F_SM, bg=BG_CARD, fg=FG_LABEL).pack(anchor="w", pady=(0, 4))
        tk.Label(card, text="가입 질문 기본 답변 (미입력 시 '넵.알겠습니다.'):", font=F_SM, bg=BG_CARD, fg=FG_LABEL).pack(anchor="w", pady=(8, 4))
        join_answer_var = tk.StringVar(value=getattr(self, "_cafe_autojoin_join_answer", "") or "넵.알겠습니다.")
        _entry(card, join_answer_var).pack(fill="x", pady=(0, 8))
        tk.Label(card, text="2captcha API 키 (캡챠 해독용, 없으면 캡챠 시 스킵):", font=F_SM, bg=BG_CARD, fg=FG_LABEL).pack(anchor="w", pady=(8, 4))
        captcha_var = tk.StringVar(value=getattr(self, "_cafe_autojoin_captcha_key", "") or "")
        _entry(card, captcha_var, show="●").pack(fill="x", pady=(0, 12))
        stop_flag = {"v": False}
        driver_holder = {}

        def _on_start():
            try:
                stop_flag["v"] = False
                self._cafe_log("[카페가입도우미] 시작 — 네이버 로그인 후 카페 순회")
                def _run():
                    try:
                        from cafe_autojoin import run_helper_cafe_join
                        def _log(msg):
                            try:
                                self.root.after(0, lambda m=msg: self._cafe_log(m))
                            except Exception:
                                pass
                        def _progress(p, t):
                            try:
                                self.root.after(0, lambda pp=p, tt=t: self._update_cafe_progress(pp, tt))
                            except Exception:
                                pass
                        run_helper_cafe_join(
                            naver_id=nid,
                            naver_pw=npw,
                            helper_cafes=cafes,
                            captcha_api_key=captcha_var.get().strip() or None,
                            join_answer_text=join_answer_var.get().strip() or None,
                            log=_log,
                            stop_flag=lambda: stop_flag["v"],
                            driver_holder=driver_holder,
                            on_progress=_progress,
                            on_joined=lambda joined: self.root.after(0, lambda: (self._cafe_log(f"[카페가입도우미] {len(joined)}개 가입 완료 → 포스팅 리스트에 반영"), self._merge_joined_to_cafe_list(joined))),
                        )
                        self.root.after(0, lambda: self._cafe_log("[카페가입도우미] 작업 완료"))
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        self.root.after(0, lambda err=str(e): self._cafe_log(f"[카페가입도우미] 오류: {err}"))
                        self.root.after(0, lambda err=str(e): messagebox.showerror("카페가입도우미 오류", str(err), parent=dlg))
                threading.Thread(target=_run, daemon=True).start()
            except Exception as e:
                messagebox.showerror("오류", f"시작 실패: {e}", parent=dlg)

        def _on_stop():
            stop_flag["v"] = True
            self._cafe_log("[카페가입도우미] 중지 요청")
            try:
                from cafe_poster import safe_quit_driver
                d = driver_holder.get("driver")
                if d:
                    safe_quit_driver(d)
                    driver_holder["driver"] = None
            except Exception:
                pass

        def _save_settings():
            self._cafe_autojoin_captcha_key = captcha_var.get().strip()
            self._cafe_autojoin_join_answer = join_answer_var.get().strip()

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.pack(fill="x", pady=(12, 0))
        _action_btn(btn_row, " 시작 ", GREEN, GREEN_H, lambda: (_save_settings(), _on_start())).pack(side="left", padx=(0, 8))
        _action_btn(btn_row, " 중지 ", RED, RED_H, _on_stop).pack(side="left")

    def _merge_joined_to_cafe_list(self, joined):
        """가입 완료된 카페를 포스팅 리스트에 병합 (중복 제외)"""
        for j in joined:
            cid = j.get("cafe_id")
            mid = j.get("menu_id", "")
            if not cid:
                continue
            exists = any(c.get("cafe_id") == cid for c in self.cafe_list)
            if not exists:
                self.cafe_list.append({"cafe_id": cid, "menu_id": mid})
        self.cafe_listbox.delete(0, "end")
        for i, c in enumerate(self.cafe_list, 1):
            self.cafe_listbox.insert("end", f"  {i:>3}    {c['cafe_id']:<20}  {c['menu_id']}")
        self.cafe_count_label.config(text=f"{len(self.cafe_list)}개 카페 등록됨")

    def _load_cafe_list_file(self, path):
        from cafe_poster import load_cafe_list
        try:
            self.cafe_list = load_cafe_list(path)
            self.cafe_file_var.set(os.path.basename(path))
            self.cafe_listbox.delete(0, "end")
            for i, c in enumerate(self.cafe_list, 1):
                self.cafe_listbox.insert(
                    "end",
                    f"  {i:>3}    {c['cafe_id']:<20}  {c['menu_id']}")
            self.cafe_count_label.config(
                text=f"{len(self.cafe_list)}개 카페 등록됨")
            self._cafe_log(
                f"[카페] {len(self.cafe_list)}개 카페 로드 ← {path}")
        except Exception as e:
            messagebox.showerror("오류", f"카페 리스트 읽기 실패:\n{e}")

    def _compute_helper_new_cafes(self):
        """helper_new_cafe_since 기준으로 신규 카페 목록 계산"""
        since = getattr(self, "helper_new_cafe_since", None)
        cafes = getattr(self, "helper_cafes", [])
        self.helper_new_cafes = []
        if not since or not cafes:
            return
        try:
            since_dt = datetime.datetime.strptime(since, "%Y-%m-%d").date()
            for c in cafes:
                ca = c.get("created_at")
                if not ca:
                    continue
                if isinstance(ca, str):
                    ca = ca[:10]
                    try:
                        cd = datetime.datetime.strptime(ca, "%Y-%m-%d").date()
                    except ValueError:
                        continue
                else:
                    continue
                if cd >= since_dt:
                    self.helper_new_cafes.append(c)
        except Exception:
            pass

    def _refresh_helper_new_cafe_alert(self):
        """도우미 하단: 신규 카페 알림 (빨간 글씨)"""
        new_list = getattr(self, "helper_new_cafes", [])
        since = getattr(self, "helper_new_cafe_since", None)
        if not new_list or not since:
            self.helper_new_cafe_label.config(text="")
            return
        try:
            dt = datetime.datetime.strptime(since, "%Y-%m-%d")
            fmt = f"{dt.year}년{dt.month}월{dt.day}일"
        except Exception:
            fmt = since
        self.helper_new_cafe_label.config(text=f"{fmt}자 신규추가 카페가 있습니다. ")

    def _on_helper_mode_change(self):
        """도우미 모드 변경 시 (별도 처리 없음)"""
        pass

    def _refresh_helper_cafe_count(self):
        """도우미 카페 개수 라벨 갱신"""
        n = len(getattr(self, "helper_cafes", []))
        if n > 0:
            self.helper_cafe_count_label.config(text=f"{n}개 카페 (서버)")
        else:
            self.helper_cafe_count_label.config(text="(서버에서 불러옴)")

    def _on_helper_apply(self):
        """서버에서 카페리스트를 가져와 포스팅용 리스트에 적용.
        로그인 시: agent_cafe_lists에서 status=saved/joined 조회 (자기 아이디 것만)
        미로그인 시: helper_cafes (기존)"""
        if self.helper_cafe_mode_var.get() != "all":
            messagebox.showinfo("안내", "'모두사용'을 선택한 후 적용해주세요.")
            return
        def _do():
            try:
                from auth import get_session
                from shared.gui_data import fetch_helper_cafes, fetch_program_cafe_lists
                s = get_session()
                un = (s or {}).get("username", "").strip() if s else ""
                if un:
                    cafes = fetch_program_cafe_lists(un, statuses=["saved", "joined"])
                    if not cafes:
                        cafes = fetch_helper_cafes()
                else:
                    cafes = fetch_helper_cafes()
                self.root.after(0, lambda: self._apply_helper_cafes(cafes))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("오류", f"서버에서 카페리스트를 가져오지 못했습니다:\n{e}"))
        threading.Thread(target=_do, daemon=True).start()

    def _apply_helper_cafes(self, cafes):
        """서버 카페리스트를 포스팅용 리스트에 적용"""
        self.helper_cafes = cafes
        self._compute_helper_new_cafes()
        if hasattr(self, "helper_cafe_count_label") and self.helper_cafe_count_label.winfo_exists():
            self._refresh_helper_cafe_count()
        if hasattr(self, "helper_new_cafe_label") and self.helper_new_cafe_label.winfo_exists():
            self._refresh_helper_new_cafe_alert()
        if not cafes:
            messagebox.showwarning("안내", "서버에 등록된 카페가 없습니다.")
            return
        valid = [c for c in cafes if (c.get("cafe_id") or "").strip() and (c.get("menu_id") or "").strip()]
        self.cafe_list = [{"cafe_id": c["cafe_id"], "menu_id": c["menu_id"]} for c in valid]
        self.cafe_listbox.delete(0, "end")
        for i, c in enumerate(self.cafe_list, 1):
            self.cafe_listbox.insert("end", f"  {i:>3}    {c['cafe_id']:<20}  {c['menu_id']}")
        self.cafe_count_label.config(text=f"{len(self.cafe_list)}개 카페 등록됨")
        self._cafe_log(f"[도우미] 서버 카페리스트 {len(self.cafe_list)}개 적용 완료")

    def _on_helper_download_new(self):
        """신규카페 리스트를 텍스트 파일로 다운로드 (카페주소만)"""
        cafes = getattr(self, "helper_new_cafes", [])
        if not cafes:
            messagebox.showinfo("안내", "신규 추가된 카페가 없습니다.")
            return
        path = filedialog.asksaveasfilename(
            title="신규카페 리스트 저장",
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
            initialfile="신규카페리스트.txt",
        )
        if path:
            self._save_cafe_urls_to_file(cafes, path, "신규")

    def _on_helper_download_all(self):
        """전체카페리스트를 텍스트 파일로 다운로드 (카페주소만)"""
        cafes = getattr(self, "helper_cafes", [])
        if not cafes:
            messagebox.showinfo("안내", "서버에 등록된 카페가 없습니다.")
            return
        path = filedialog.asksaveasfilename(
            title="전체카페리스트 저장",
            defaultextension=".txt",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
            initialfile="전체카페리스트.txt",
        )
        if path:
            self._save_cafe_urls_to_file(cafes, path, "전체")

    def _save_cafe_urls_to_file(self, cafes, path, label):
        """서버 cafe_url만 텍스트 파일로 저장 (카페 주소만, 글쓰기 경로 제외)"""
        try:
            urls = []
            for c in cafes:
                u = (c.get("cafe_url") or "").strip()
                if u:
                    urls.append(u)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(urls))
            self._cafe_log(f"[도우미] {label} 카페리스트 {len(urls)}개 저장됨 ← {path}")
            messagebox.showinfo("완료", f"{path}\n{len(urls)}개 카페 주소 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"파일 저장 실패:\n{e}")

    # ──────────────────────────────────────────────
    # CAFE SETTINGS SAVE/LOAD
    # ──────────────────────────────────────────────
    def _save_cafe_settings(self):
        data = {
            "naver_id": self.naver_id_var.get().strip(),
            "naver_pw": self.naver_pw_var.get().strip(),
            "cafe_file": self.cafe_file_var.get(),
            "cafe_list": self.cafe_list,
            "posting_interval_min": self.cafe_interval_min_var.get(),
            "posting_interval_max": self.cafe_interval_max_var.get(),
            "post_count": self.cafe_post_count_var.get(),
            "linebreak_enabled": self.cafe_linebreak_var.get(),
            "linebreak_max_chars": self.cafe_maxchars_var.get(),
            "kw_repeat_min": self.cafe_kw_repeat_min_var.get(),
            "kw_repeat_max": self.cafe_kw_repeat_max_var.get(),
            "use_product_name": self.cafe_use_product_name_var.get(),
            "selected_category": self.selected_category.get(),
            "commission_image_folder": self.commission_image_folder_var.get().strip(),
            # "link_btn_image": 더 이상 사용하지 않음 (댓글 방식)
            "auto_restart_enabled": self._auto_restart_enabled,
            "auto_restart_hour": self._auto_restart_hour,
            "auto_restart_minute": self._auto_restart_minute,
            "auto_restart_blog": self._auto_restart_blog,
            "auto_restart_cafe": self._auto_restart_cafe,
            "helper_cafe_mode": self.helper_cafe_mode_var.get(),
            "cafe_multi_account": self.cafe_multi_account_var.get() if hasattr(self, "cafe_multi_account_var") else False,
            "cafe_multi_account_file": self.cafe_multi_account_file_var.get() if hasattr(self, "cafe_multi_account_file_var") else "",
            "cafe_account_switch_wait": self.cafe_account_switch_wait_var.get() if hasattr(self, "cafe_account_switch_wait_var") else 5,
            "cafe_infinite_loop": self.cafe_infinite_loop_var.get() if hasattr(self, "cafe_infinite_loop_var") else False,
            "last_cafe_idx": getattr(self, "_last_cafe_idx", 0),
        }
        with open(CAFE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._cafe_log("[설정] 카페 설정 저장 완료")

    def _load_cafe_settings(self):
        self._load_cafe_settings_silent()
        self._cafe_log("[설정] 카페 설정 불러오기 완료")

    def _load_cafe_settings_silent(self):
        self._last_cafe_idx = 0
        if not os.path.exists(CAFE_SETTINGS_FILE):
            dp = os.path.join(BASE_DIR, "cafe_list.txt")
            if os.path.exists(dp):
                self._load_cafe_list_file(dp)
            return
        try:
            with open(CAFE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            nid = data.get("naver_id", "")
            npw = data.get("naver_pw", "")
            if nid:
                self.naver_id_var.set(nid)
            if npw:
                self.naver_pw_var.set(npw)
            # 포스팅 주기 / 줄바꿈 설정 복원
            if "posting_interval_min" in data or "posting_interval_max" in data:
                self.cafe_interval_min_var.set(data.get("posting_interval_min", 5))
                self.cafe_interval_max_var.set(data.get("posting_interval_max", 30))
            else:
                old = data.get("posting_interval", 60)
                self.cafe_interval_min_var.set(max(1, old // 2))
                self.cafe_interval_max_var.set(old)
            self.cafe_post_count_var.set(max(2, data.get("post_count", 10)))
            lb = data.get("linebreak_enabled", False)
            self.cafe_linebreak_var.set(lb)
            self.cafe_maxchars_var.set(data.get("linebreak_max_chars", 45))
            if lb:
                self.cafe_maxchars_frame.pack(side="left")
            self.cafe_kw_repeat_min_var.set(data.get("kw_repeat_min", 3))
            self.cafe_kw_repeat_max_var.set(data.get("kw_repeat_max", 7))
            self.cafe_use_product_name_var.set(data.get("use_product_name", False))
            self.selected_category.set(data.get("selected_category", "건강식품"))
            self.commission_image_folder_var.set(data.get("commission_image_folder", ""))
            # (link_btn_image 설정은 더 이상 사용하지 않음 — 댓글 방식으로 전환)
            # 자동재시작 설정 복원
            self._auto_restart_enabled = data.get("auto_restart_enabled", False)
            self._auto_restart_hour = data.get("auto_restart_hour", 9)
            self._auto_restart_minute = data.get("auto_restart_minute", 0)
            self._auto_restart_blog = data.get("auto_restart_blog", False)
            self._auto_restart_cafe = data.get("auto_restart_cafe", True)
            if self._auto_restart_enabled:
                self._schedule_auto_restart()
            # 도우미 카페 모드 복원 (구 helper_cafe_use 호환)
            if hasattr(self, "helper_cafe_mode_var"):
                hm = data.get("helper_cafe_mode")
                if hm is None and data.get("helper_cafe_use"):
                    hm = "all"
                if hm in ("all", "") or hm is None:
                    self.helper_cafe_mode_var.set(hm or "")
            # 다중아이디 설정 복원
            if hasattr(self, "cafe_multi_account_var"):
                self.cafe_multi_account_var.set(bool(data.get("cafe_multi_account", False)))
                self.cafe_multi_account_file_var.set(data.get("cafe_multi_account_file", ""))
                self.cafe_account_switch_wait_var.set(int(data.get("cafe_account_switch_wait", 5)))
                self.cafe_infinite_loop_var.set(bool(data.get("cafe_infinite_loop", False)))
            self._last_cafe_idx = max(0, int(data.get("last_cafe_idx", 0)))
            saved = data.get("cafe_list", [])
            if saved:
                self.cafe_list = saved
                self.cafe_file_var.set(data.get("cafe_file", "cafe_list.txt"))
                self.cafe_listbox.delete(0, "end")
                for i, c in enumerate(self.cafe_list, 1):
                    self.cafe_listbox.insert(
                        "end",
                        f"  {i:>3}    {c['cafe_id']:<20}  {c['menu_id']}")
                self.cafe_count_label.config(
                    text=f"{len(self.cafe_list)}개 카페 등록됨")
            else:
                cf = data.get("cafe_file", "")
                if cf:
                    fp = os.path.join(BASE_DIR, cf)
                    if os.path.exists(fp):
                        self._load_cafe_list_file(fp)
        except Exception:
            pass

    # ──────────────────────────────────────────────
    # SEARCH RUN / STOP
    # ──────────────────────────────────────────────
    def _require_login_and_session(self, run_type="search"):
        """로그인 체크 + 기기 제한 체크 + 세션 등록. 성공 시 True"""
        if not getattr(self, "_auth_available", False):
            messagebox.showwarning("안내", "로그인이 필요합니다.\n(인증 모듈을 불러올 수 없습니다. Supabase 설정을 확인하세요.)")
            return False
        try:
            from auth import is_logged_in, get_session, check_device_limit, add_active_session, save_coupang_keys
            if not is_logged_in():
                messagebox.showwarning("안내", "로그인이 필요합니다.")
                return False
            ak = self.coupang_ak_var.get().strip()
            sk = self.coupang_sk_var.get().strip()
            if not ak or not sk:
                messagebox.showwarning("안내", "쿠팡 파트너스 Access Key와 Secret Key를 입력하세요.")
                return False
            s = get_session()
            user_id = s.get("id") if s else None
            if not user_id:
                try:
                    from auth import logout
                    logout()
                except Exception:
                    pass
                messagebox.showwarning("안내", "세션 정보를 읽을 수 없습니다. 다시 로그인해주세요.")
                self._update_auth_ui()
                return False
            max_dev = s.get("max_devices", 5)
            ok, msg = check_device_limit(ak, user_id, max_dev, log=self._log)
            if not ok:
                messagebox.showwarning("안내", msg)
                return False
            if not getattr(self, "_auth_session_id", None):
                ok, sid = add_active_session(user_id, ak, sk, log=self._log)
                if not ok:
                    err_msg = sid if isinstance(sid, str) and sid else "세션 등록 실패. 다시 시도해주세요."
                    messagebox.showwarning("안내", f"세션 등록 실패.\n{err_msg}")
                    return False
                if sid:
                    self._auth_session_id = sid
                save_coupang_keys(user_id, ak, sk, log=self._log)
            return True
        except Exception as e:
            self._log(f"[인증] 오류: {e}")
            messagebox.showwarning("안내", "로그인 확인 중 오류가 발생했습니다. 다시 시도해주세요.")
            return False

    def _save_gui_vm_config(self):
        """VM 이름을 configs/gui_vm.json에 저장"""
        try:
            vm = (getattr(self, "_comm_vm_name_var", None) and self._comm_vm_name_var.get() or "").strip()
            d = os.path.dirname(GUI_VM_CONFIG)
            if d and not os.path.isdir(d):
                os.makedirs(d, exist_ok=True)
            with open(GUI_VM_CONFIG, "w", encoding="utf-8") as f:
                json.dump({"VM_NAME": vm}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_comm_toggle(self):
        """통신시작 체크박스 토글: 체크 시 post_tasks 폴링 시작, 해제 시 중지"""
        if not getattr(self, "_comm_enabled_var", None):
            return
        if self._comm_enabled_var.get():
            if not self._require_login_and_session():
                self._comm_enabled_var.set(False)
                return
            self._comm_stop_flag = False
            if not getattr(self, "_comm_poll_thread", None) or not self._comm_poll_thread.is_alive():
                self._comm_poll_thread = threading.Thread(target=self._comm_poll_loop, daemon=True)
                self._comm_poll_thread.start()
            self._log("[통신] Supabase post_tasks 폴링 시작")
            self.append_log_global("[통신] Supabase와 통신 시작 — 새 키워드 등록 시 자동 글 작성")
        else:
            self._comm_stop_flag = True
            self._log("[통신] 폴링 중지")
            self.append_log_global("[통신] 통신 중지")

    def _comm_poll_loop(self):
        """post_tasks 폴링 루프: pending 작업 발견 시 claim → 카페 포스팅 → finish"""
        import time
        POLL_INTERVAL = 15
        while getattr(self, "_comm_enabled_var", None) and self._comm_enabled_var.get() and not getattr(self, "_comm_stop_flag", True):
            try:
                from shared.gui_data import fetch_pending_post_tasks, claim_post_task_for_gui, finish_post_task_for_gui
                # 로그인과 무관하게 post_tasks의 모든 pending 작업 처리
                tasks = fetch_pending_post_tasks(user_id=None, limit=1, log=self._log)
                if not tasks:
                    time.sleep(POLL_INTERVAL)
                    continue
                task = tasks[0]
                task_id = task.get("id")
                task_user_id = task.get("user_id")
                kw = (task.get("keyword") or "").strip()
                channel = (task.get("channel") or "cafe").strip().lower()
                if not task_id:
                    time.sleep(POLL_INTERVAL)
                    continue
                vm_name = (getattr(self, "_comm_vm_name_var", None) and self._comm_vm_name_var.get() or "").strip() or _load_gui_vm_config().get("VM_NAME", "")
                if not claim_post_task_for_gui(task_id, task_user_id, vm_name=vm_name or None, log=self._log):
                    time.sleep(POLL_INTERVAL)
                    continue
                self._log(f"[통신] task {task_id} 선점 — 키워드: {kw!r}" + (f" (VM: {vm_name})" if vm_name else ""))
                self.append_log_global(f"[통신] 새 작업 발견 — 키워드 '{kw}'로 글 작성 시작")
                self.root.after(0, lambda: self._run_task_posting(task_id, task_user_id, kw, channel))
                time.sleep(3)
                if not getattr(self, "is_posting", False):
                    finish_post_task_for_gui(task_id, task_user_id, success=False, log=self._log)
                    self._log(f"[통신] task {task_id} — 포스팅 시작 실패 (카페/계정 설정 확인)")
                    time.sleep(POLL_INTERVAL)
                    continue
                while getattr(self, "is_posting", False) and not getattr(self, "_comm_stop_flag", True):
                    time.sleep(2)
                # 글작성 직후 이미 완료 등록했으면 성공 유지 (크롬 중간 종료 시 실패로 덮어쓰지 않음)
                already_success = getattr(self, "_comm_task_finished_success", False)
                success = already_success or (not getattr(self, "_posting_stop_flag", True))
                published_url = getattr(self, "_comm_last_published_url", None)
                if published_url:
                    self._log(f"[통신] task {task_id} published_url 저장: {published_url[:50]}...")
                else:
                    self._log(f"[통신] task {task_id} published_url 없음 (success={success})")
                if not already_success:
                    finish_post_task_for_gui(task_id, task_user_id, success=success, published_url=published_url, log=self._log)
                self._log(f"[통신] task {task_id} 완료 처리 (success={success})")
                # 대기시간 설정만큼 대기 후 다음 폴링
                imin = max(1, getattr(self, "cafe_interval_min_var", None) and self.cafe_interval_min_var.get() or 5)
                imax = max(imin, getattr(self, "cafe_interval_max_var", None) and self.cafe_interval_max_var.get() or 30)
                wait_min = random.randint(imin, imax)
                self._log(f"[통신] 다음 작업까지 {wait_min}분 대기...")
                self._cafe_log(f"[통신] {wait_min}분간 통신대기중")
                for _ in range(wait_min * 60):
                    if getattr(self, "_comm_stop_flag", True):
                        break
                    time.sleep(1)
            except Exception as e:
                self._log(f"[통신] 폴링 오류: {e}")
            time.sleep(POLL_INTERVAL)

    def _run_task_posting(self, task_id, user_id, kw, channel):
        """task 키워드로 포스팅 시작 (메인 스레드에서 호출)"""
        if not kw:
            self._log("[통신] 키워드 없음 — task 스킵")
            return
        self._comm_current_task_id = task_id
        self._comm_current_user_id = user_id
        self._comm_last_published_url = None  # 이전 작업 URL 초기화
        self._comm_task_finished_success = False  # 글작성 성공 시 즉시 완료 처리 여부
        if channel == "blog":
            self._switch_tab_main("blog")
            self._on_start_blog_posting(skip_confirm=True, task_keywords_override=[kw])
        else:
            self._switch_tab_main("cafe")
            self._on_start_posting(skip_confirm=True, task_keywords_override=[kw])

    def _on_enqueue_start(self):
        """실행 시작: enqueue_post_tasks_paid RPC 호출 → post_tasks에 pending 작업 생성"""
        if not self._require_login_and_session():
            return
        try:
            from shared.gui_data import enqueue_post_tasks_paid, fetch_user_coupang_keys
            user_id = getattr(self, "current_user_id", None)
            if not user_id:
                from auth import get_session
                s = get_session()
                user_id = s.get("id") if s else None
            if not user_id:
                messagebox.showwarning("안내", "세션 정보가 없습니다. 다시 로그인해주세요.")
                return
            keys = fetch_user_coupang_keys(user_id=user_id, log=self._log)
            if not keys:
                messagebox.showwarning("안내", "쿠팡파트너스 키를 등록후 진행하세요.")
                return
            count = max(1, getattr(self, "blog_post_count_var", None) and self.blog_post_count_var.get() or 10)
            channel = "cafe"  # 기본값
            cur_tab = getattr(self, "_cur_tab", None) or "search"
            if cur_tab == "blog":
                channel = "blog"
                count = max(1, getattr(self, "blog_post_count_var", None) and self.blog_post_count_var.get() or 10)
            elif cur_tab == "cafe":
                channel = "cafe"
                count = max(2, getattr(self, "cafe_post_count_var", None) and self.cafe_post_count_var.get() or 10)
            payload = {"meta": {}}
            ok, data, err = enqueue_post_tasks_paid(user_id=user_id, channel=channel, count=count, cost=None, payload=payload, log=self._log)
            if ok:
                self._log(f"[실행시작] post_tasks enqueue 성공: channel={channel}, count={count}")
                self.append_log_global(f"[실행시작] post_tasks enqueue 성공 — worker가 claim하여 실행합니다.")
            else:
                self._log(f"[실행시작] enqueue 실패: {err}")
                self.append_log_global(f"[실행시작] enqueue 실패: {err}")
                messagebox.showerror("오류", f"enqueue_post_tasks_paid 실패:\n{err}")
        except Exception as e:
            self._log(f"[실행시작] 오류: {e}")
            self.append_log_global(f"[실행시작] 오류: {e}")
            messagebox.showerror("오류", str(e))

    def _on_run_selected(self):
        if not self._require_login_and_session():
            return
        sel = self.kw_listbox.curselection()
        if not sel:
            messagebox.showwarning("안내", "키워드를 선택하세요.")
            return
        self._start([self.kw_listbox.get(i) for i in sel])

    def _on_run_all(self):
        if not self._require_login_and_session():
            return
        if not self.keywords:
            messagebox.showwarning("안내", "키워드를 먼저 불러오세요.")
            return
        self.kw_listbox.select_set(0, "end")
        self._start(list(self.keywords))

    def _on_stop(self):
        if self.is_running:
            self._stop_flag = True
            self._log("[중지] 사용자가 중지 요청")

    def _start(self, keywords):
        key = self.gemini_key_var.get().strip()
        if not key:
            messagebox.showwarning("안내", "Gemini API Key를 입력하세요.")
            return
        if not self.coupang_ak_var.get().strip() or not self.coupang_sk_var.get().strip():
            messagebox.showwarning("안내", "쿠팡 파트너스 Access Key와 Secret Key를 입력하세요.")
            return
        if self.is_running:
            return
        self.is_running = True
        self._stop_flag = False
        self._set_status("running", "실행 중...")
        self._clear_log()
        self._update_progress(0, "준비 중...")
        threading.Thread(target=self._worker, args=(keywords, key),
                         daemon=True).start()

    def _worker(self, keywords, gemini_key):
        keywords = list(keywords)
        random.shuffle(keywords)
        total = len(keywords)
        limit = 1
        img_dir = self.img_dir_var.get().strip()

        banned_brands = []
        is_keyword_banned_fn = None
        try:
            from shared.gui_data import fetch_banned_brands, is_keyword_banned
            banned_brands = fetch_banned_brands(log=self._log)
            is_keyword_banned_fn = is_keyword_banned
        except Exception as e:
            self._log(f"[Supabase] 활동금지 브랜드 조회 실패: {e}")

        for idx, kw in enumerate(keywords):
            if getattr(self, '_stop_flag', False):
                self._log(f"\n[중지] 작업이 중지되었습니다. ({idx}/{total})")
                break
            if banned_brands and is_keyword_banned_fn and is_keyword_banned_fn(kw, banned_brands):
                self._log(f"\n⚠ 해당 키워드는 쿠팡 활동금지 업체 브랜드 키워드 입니다: {kw}")
                self._log(f"  → 다음 키워드로 이동합니다.")
                continue
            pct = int((idx / total) * 100)
            self._safe(self._update_progress, pct,
                       f"{kw} 처리 중... ({idx+1}/{total})")
            self._safe(self._set_status, "running",
                       f"실행 중: {kw} ({idx+1}/{total})")
            self._log(f"\n{'━'*45}")
            self._log(f"  [{idx+1}/{total}] {kw}")
            self._log(f"{'━'*45}")
            try:
                from main import run_pipeline
                result = run_pipeline(
                    kw, limit=limit, gemini_api_key=gemini_key,
                    log_callback=self._log, image_save_dir=img_dir,
                    keyword_repeat_min=self.kw_repeat_min_var.get(),
                    keyword_repeat_max=self.kw_repeat_max_var.get(),
                    coupang_access_key=self.coupang_ak_var.get().strip() or None,
                    coupang_secret_key=self.coupang_sk_var.get().strip() or None)
                if result:
                    self.results[kw] = result
                    self._log(f"  ✔ '{kw}' 완료")
                else:
                    self._log(f"  ✘ '{kw}' 결과 없음")
            except Exception as e:
                self._log(f"  ✘ 오류: {e}")

        done = len(self.results)
        self._safe(self._update_progress, 100,
                   f"완료 — {done}/{total}개 처리됨")
        self._safe(self._set_status, "done", f"완료: {done}/{total}")
        self._log(f"\n전체 완료: {done}/{total}개 성공")
        self.root.after(0, self._on_done)

    def _on_done(self):
        self.is_running = False
        if self.results and getattr(self, "result_menu", None):
            menu = self.result_menu["menu"]
            menu.delete(0, "end")
            for kw in self.results:
                menu.add_command(label=kw,
                    command=lambda k=kw: self.result_kw_var.set(k))
            self.result_kw_var.set(list(self.results.keys())[-1])

    # ──────────────────────────────────────────────
    # CAFE POSTING
    # ──────────────────────────────────────────────
    def _on_start_posting(self, skip_confirm=False, cafes_override=None, use_agent_cafe_loop=False, task_keywords_override=None):
        """skip_confirm: 자동재시작 등에서 확인 팝업 없이 바로 시작.
        cafes_override: 서버에서 가져온 카페 리스트 (도우미 모두사용 + 서버뉴카페 시).
        use_agent_cafe_loop: True면 모두 완료 후 처음 카페부터 반복.
        task_keywords_override: post_tasks에서 온 키워드 리스트 (통신시작 모드)."""
        if not self._require_login_and_session("cafe"):
            return
        if task_keywords_override is not None:
            keywords_for_posting = [k for k in (task_keywords_override or []) if k and str(k).strip()]
            if not keywords_for_posting:
                return
        else:
            use_paid_kw = getattr(self, "use_paid_member_keywords_var", None) and self.use_paid_member_keywords_var.get()
            if use_paid_kw and self._is_admin():
                try:
                    from shared.gui_data import fetch_paid_member_keywords_pool
                    pc = max(2, self.cafe_post_count_var.get())
                    keywords_for_posting = fetch_paid_member_keywords_pool(count=pc * 2, log=self._cafe_log)
                    if not keywords_for_posting:
                        messagebox.showwarning("안내", "유료회원 키워드가 없습니다. Supabase paid_members 테이블을 확인하세요.")
                        return
                except Exception as e:
                    messagebox.showerror("오류", f"유료회원 키워드 조회 실패:\n{e}")
                    return
            else:
                if not self.keywords:
                    messagebox.showwarning("안내",
                        "키워드를 먼저 '상품 검색' 탭에서 불러오세요.")
                    return
                keywords_for_posting = None
        multi = getattr(self, "cafe_multi_account_var", None) and self.cafe_multi_account_var.get()
        if multi:
            path = getattr(self, "cafe_multi_account_file_var", None) and self.cafe_multi_account_file_var.get().strip()
            if not path or not os.path.isfile(path):
                messagebox.showwarning("안내", "다중아이디 사용 시 아이디 파일을 불러오세요.")
                return
            accounts = self._load_accounts_from_file(path)
            if not accounts:
                messagebox.showwarning("안내", "유효한 계정이 없습니다. 형식: 아이디[TAB]비밀번호 (한 줄에 하나)")
                return
        else:
            nid = self.naver_id_var.get().strip()
            npw = self.naver_pw_var.get().strip()
            if not nid or not npw:
                messagebox.showwarning("안내", "네이버 아이디와 비밀번호를 입력하세요.")
                return
            accounts = [{"id": nid, "pw": npw}]
        gk = self.gemini_key_var.get().strip()
        if not gk:
            messagebox.showwarning("안내",
                "Gemini API Key를 먼저 '상품 검색' 탭에서 입력하세요.")
            return
        comm_mode_agent_cafe = bool(task_keywords_override and getattr(self, "_comm_current_task_id", None))
        if comm_mode_agent_cafe:
            cafes_for_posting = []
        elif cafes_override is not None:
            cafes_for_posting = cafes_override
        else:
            mode = self.helper_cafe_mode_var.get()
            if mode == "all":
                cafes_for_posting = [{"cafe_id": c["cafe_id"], "menu_id": c["menu_id"]} for c in getattr(self, "helper_cafes", [])]
            else:
                cafes_for_posting = self.cafe_list
        if not comm_mode_agent_cafe and not cafes_for_posting:
            if cafes_override is not None:
                msg = "서버에 가입된 카페(agent_cafe_lists)가 없습니다. 카페가입을 먼저 진행해주세요."
            else:
                mode = self.helper_cafe_mode_var.get()
                msg = "카페리스트를 먼저 불러오세요." if mode != "all" else "서버 도우미 카페리스트가 비어있습니다. '적용' 버튼을 눌러주세요."
            messagebox.showwarning("안내", msg)
            return
        is_task_run = bool(task_keywords_override and getattr(self, "_comm_current_task_id", None))
        if not is_task_run:
            try:
                from auth import get_session
                from shared.gui_data import fetch_user_coupang_keys
                s = get_session()
                uid = (s or {}).get("id")
                keys = fetch_user_coupang_keys(username=(s or {}).get("username"), user_id=uid, log=self._cafe_log)
                if not keys and not (self.coupang_ak_var.get().strip() and self.coupang_sk_var.get().strip()):
                    messagebox.showwarning("안내", "쿠팡파트너스 키를 등록후 진행하세요.")
                    return
            except Exception:
                if not (self.coupang_ak_var.get().strip() and self.coupang_sk_var.get().strip()):
                    messagebox.showwarning("안내", "쿠팡파트너스 키를 등록후 진행하세요.")
                    return
        if self.is_posting:
            messagebox.showinfo("안내", "이미 포스팅이 진행 중입니다.")
            return
        kw_count = len(keywords_for_posting) if keywords_for_posting else len(self.keywords or [])
        if not skip_confirm:
            msg = (f"아래 설정으로 자동 포스팅을 시작합니다.\n\n"
                   f"  발행 카테고리: {self.selected_category.get()}\n"
                   f"  키워드: {kw_count}개\n"
                   f"  카페: {len(cafes_for_posting)}개\n"
                   f"  총 포스팅: 카페당 키워드 1씩 배분 (작업 수 건)\n\n"
                   f"계속 진행할까요?")
            if not messagebox.askyesno("발행 확인", msg):
                return
        self.is_posting = True
        self._posting_stop_flag = False
        self._set_status("running", "포스팅 중...")
        self._clear_cafe_log()
        self._update_cafe_progress(0, "준비 중...")
        self._save_cafe_settings()
        comm_task_id = getattr(self, "_comm_current_task_id", None) if keywords_for_posting else None
        comm_task_user_id = getattr(self, "_comm_current_user_id", None) if comm_task_id else None
        t = threading.Thread(
            target=self._posting_worker,
            args=(cafes_for_posting, accounts),
            kwargs={
                "keywords_override": keywords_for_posting,
                "use_agent_cafe_loop": use_agent_cafe_loop,
                "task_id": comm_task_id,
                "task_user_id": comm_task_user_id,
                "comm_mode_agent_cafe": comm_mode_agent_cafe,
            },
            daemon=True,
        )
        t.start()

    def _on_stop_posting(self):
        # 포스팅 중이면 worker 중지 플래그
        if self.is_posting:
            self._posting_stop_flag = True
        # 통신대기중이면 폴링 루프의 대기 즉시 중단
        if getattr(self, "_comm_enabled_var", None) and self._comm_enabled_var.get():
            self._comm_stop_flag = True
        self._cafe_log("[중지] 포스팅 중지 요청됨 — 크롬 브라우저를 종료합니다...")
        from cafe_poster import safe_quit_driver
        d = None
        if hasattr(self, "_driver_holder") and isinstance(getattr(self, "_driver_holder"), dict):
            d = self._driver_holder.get("driver")
        if d:
            safe_quit_driver(d)
            self._driver_holder["driver"] = None
            self._cafe_log("[중지] ✔ 크롬 브라우저 강제 종료 완료")

    def _posting_worker(self, cafes_for_posting=None, accounts=None, task_id=None, task_user_id=None, keywords_override=None, use_agent_cafe_loop=False, comm_mode_agent_cafe=False):
        """accounts: [{"id", "pw"}, ...] — 다중아이디 시 여러 계정. keywords_override: 유료회원 키워드 사용 시.
        task_user_id: post_tasks 태스크 소유자 user_id — 이 값이 있으면 해당 사용자의 쿠팡키 사용 (프로그램 로그인 무관).
        use_agent_cafe_loop: True면 서버뉴카페 모드 — 모두 완료 후 처음 카페부터 반복.
        comm_mode_agent_cafe: True면 통신모드 — agent_cafe_lists만 naver_id 기준, 카페<50이면 가입 1개 후 글작성 1건."""
        self.append_log_global("[CAFE] worker started")
        self._cafe_log("[CAFE] worker started")
        import time
        from cafe_poster import run_auto_posting, setup_driver, login_to_naver
        accounts = accounts or [{"id": self.naver_id_var.get().strip(), "pw": self.naver_pw_var.get().strip()}]
        keywords_to_use = (keywords_override if keywords_override is not None else self.keywords) or []
        gk = self.gemini_key_var.get().strip()
        sl = 1
        imd = self.img_dir_var.get().strip()
        posted = [0]
        # 통신모드: 기존 크롬창 재사용. 일반모드: 매번 새로 시작
        if task_id is None:
            self._driver_holder = {"driver": None}
        elif not hasattr(self, "_driver_holder") or self._driver_holder is None:
            self._driver_holder = {"driver": None}

        comm_naver_id = ""
        comm_naver_pw = ""
        driver_holder = self._driver_holder
        if comm_mode_agent_cafe and task_id and accounts:
            comm_naver_id = (accounts[0].get("id") or "").strip()
            comm_naver_pw = (accounts[0].get("pw") or "").strip()
            if not comm_naver_id or not comm_naver_pw:
                self._cafe_log("[통신] 네이버 아이디/비밀번호 없음")
                self.is_posting = False
                return
            driver = driver_holder.get("driver")
            if not driver:
                try:
                    driver = setup_driver(headless=False)
                    driver_holder["driver"] = driver
                    if not login_to_naver(driver, comm_naver_id, comm_naver_pw, log=self._cafe_log):
                        self._cafe_log("[통신] 네이버 로그인 실패")
                        self.is_posting = False
                        return
                except Exception as e:
                    self._cafe_log(f"[통신] 드라이버/로그인 오류: {e}")
                    self.is_posting = False
                    return

        def _fetch_comm_cafes():
            """comm_mode_agent_cafe용: agent_cafe_lists에서 카페 1개 선택 (가입 필요 시 1개 가입 후)."""
            from supabase_client import delete_expired_agent_cafes, fetch_agent_cafe_lists_full
            from config import OWNER_USER_ID
            from shared.gui_data import get_admin_settings, fetch_cafe_join_policy
            policy = fetch_cafe_join_policy(log=self._cafe_log) or {}
            expire_days = int(policy.get("expire_days") or 10)
            target_count = int(policy.get("target_count") or 50)
            delete_expired_agent_cafes(comm_naver_id, days=expire_days, log=self._cafe_log)
            cafes_full = fetch_agent_cafe_lists_full(comm_naver_id, statuses=["saved", "joined"], log=self._cafe_log)
            if len(cafes_full) < target_count:
                self._cafe_log(f"[통신] 카페 {len(cafes_full)}개 (목표 {target_count}) → 1개 가입 후 글작성")
                try:
                    from cafe_autojoin import run_cafe_join_job
                    admin = get_admin_settings(log=self._cafe_log)
                    captcha_key = (admin.get("captcha_api_key") or admin.get("captcha_key") or "").strip() or None
                    if not captcha_key:
                        self._cafe_log("[통신] app_links(captcha_api_key) 없음 — 캡챠 시 스킵됨")
                    comm_vm_name = (getattr(self, "_comm_vm_name_var", None) and self._comm_vm_name_var.get() or "").strip() or _load_gui_vm_config().get("VM_NAME", "")
                    # post_tasks의 assigned_vm_name처럼 agent_cafe_lists에도 vm_name 등록 (없으면 GUI로 식별)
                    vm_for_cafe = (comm_vm_name or "GUI").strip()
                    run_cafe_join_job(
                        owner_user_id=OWNER_USER_ID,
                        program_username=comm_naver_id,
                        naver_id=comm_naver_id,
                        naver_pw=comm_naver_pw,
                        stop_flag=lambda: getattr(self, "_posting_stop_flag", False),
                        log=self._cafe_log,
                        immediate=True,
                        target_count_override=1,
                        driver_holder=driver_holder,
                        captcha_api_key=captcha_key,
                        vm_name=vm_for_cafe or None,
                    )
                except Exception as e:
                    self._cafe_log(f"[통신] 카페가입 실패: {e}")
                cafes_full = fetch_agent_cafe_lists_full(comm_naver_id, statuses=["saved", "joined"], log=self._cafe_log)
            if not cafes_full:
                return None
            cafes_sorted = sorted(cafes_full, key=lambda c: (c.get("last_posted_at") or "1970-01-01"))
            first_cafe = cafes_sorted[0]
            return [{"cafe_id": first_cafe["cafe_id"], "menu_id": first_cafe["menu_id"], "_cafe_url": first_cafe.get("cafe_url", "")}]

        cafes = cafes_for_posting if cafes_for_posting is not None else self.cafe_list
        multi = getattr(self, "cafe_multi_account_var", None) and self.cafe_multi_account_var.get()
        infinite = getattr(self, "cafe_infinite_loop_var", None) and self.cafe_infinite_loop_var.get()
        wait_min = max(1, getattr(self, "cafe_account_switch_wait_var", None) and self.cafe_account_switch_wait_var.get() or 5)

        # ── Supabase에서 유료회원 목록 가져오기 (통신모드 agent_cafe: 스킵) ──
        paid_members = []
        if not comm_mode_agent_cafe:
            try:
                from shared.gui_data import fetch_paid_members
                self._cafe_log("[Supabase] 유료회원 목록 조회 중...")
                paid_members = fetch_paid_members(log=self._cafe_log)
            except ImportError:
                self._cafe_log("[Supabase] supabase 패키지 미설치 — 본인 글만 발행합니다.")
            except Exception as e:
                self._cafe_log(f"[Supabase] 조회 실패: {e} — 본인 글만 발행합니다.")

        # ── 추천인(referrer_id) 및 쿠팡 API 키 조회 ──
        # post_tasks 태스크: task_user_id(태스크 소유자)의 쿠팡키 사용. 일반모드: 프로그램 로그인 사용자.
        referrer = None
        program_username = ""
        coupang_ak, coupang_sk = None, None
        try:
            from auth import get_session
            from shared.gui_data import fetch_referrer, fetch_user_coupang_keys
            s = get_session()
            program_username = (s or {}).get("username", "") or ""
            if not comm_mode_agent_cafe:
                rid = (s or {}).get("referrer_id") if s else None
                if rid:
                    self._cafe_log(f"[Supabase] 추천인 '{rid}' 조회 중...")
                    referrer = fetch_referrer(rid, log=self._cafe_log)
            # 쿠팡 API 키: task_user_id 있으면 태스크 소유자(profiles)만 사용(fallback 없음). 없으면 세션+GUI.
            if (task_user_id or "").strip():
                keys = fetch_user_coupang_keys(user_id=(task_user_id or "").strip(), log=self._cafe_log)
                if not keys:
                    self._cafe_log("[통신] 태스크 소유자 쿠팡키 미등록 — 작업 스킵")
                    self.is_posting = False
                    try:
                        from shared.gui_data import finish_post_task_for_gui
                        self.root.after(0, lambda: finish_post_task_for_gui(task_id or "", task_user_id or "", success=False, log=self._cafe_log))
                    except Exception:
                        pass
                    return
                coupang_ak, coupang_sk = keys[0], keys[1]
            else:
                coupang_uid = (s or {}).get("id")
                keys = fetch_user_coupang_keys(username=program_username, user_id=coupang_uid, log=self._cafe_log)
                if keys:
                    coupang_ak, coupang_sk = keys[0], keys[1]
                else:
                    coupang_ak = self.coupang_ak_var.get().strip() or None
                    coupang_sk = self.coupang_sk_var.get().strip() or None
        except Exception as e:
            self._cafe_log(f"[Supabase] 추천인 조회 실패: {e}")
        if not coupang_ak or not coupang_sk:
            coupang_ak = self.coupang_ak_var.get().strip() or None
            coupang_sk = self.coupang_sk_var.get().strip() or None

        # 교차 발행 시 total 재계산 (통신모드 agent_cafe: 서버 키워드만, 유료/추천인 미사용)
        if comm_mode_agent_cafe:
            total = 1
        elif paid_members:
            kw = max(len(keywords_to_use), 1)
            if referrer:
                cycles = (kw + 2) // 3
                task_count = cycles * 6
            else:
                task_count = kw * 2
            pc = max(2, self.cafe_post_count_var.get())
            if pc and pc > 0 and task_count > pc:
                task_count = pc
            total = task_count
        else:
            task_count = len(keywords_to_use)
            pc = max(2, self.cafe_post_count_var.get())
            if pc and pc > 0 and task_count > pc:
                task_count = pc
            total = task_count

        def log_prog(msg):
            self._cafe_log(msg)
            if "포스팅 완료" in msg or "✔ 포스팅 완료" in msg:
                posted[0] += 1
                pct = int((posted[0] / max(total, 1)) * 100)
                self._safe(self._update_cafe_progress, pct,
                           f"{posted[0]}/{total}건 완료")

        account_idx = 0
        result = {"success": 0, "fail": 0}
        current_task_id = task_id
        current_task_user_id = task_user_id
        _comm_cycle_count = 0
        try:
            while True:
                if getattr(self, "_posting_stop_flag", False):
                    self._cafe_log("[중지] 사용자가 작업을 중지했습니다.")
                    break
                # 통신모드 agent_cafe: 2회차부터 새 태스크 claim → 다른 키워드 사용
                if comm_mode_agent_cafe:
                    if _comm_cycle_count > 0:
                        from shared.gui_data import fetch_pending_post_tasks, claim_post_task_for_gui, fetch_user_coupang_keys
                        tasks = fetch_pending_post_tasks(user_id=None, limit=1, log=self._cafe_log)
                        if not tasks:
                            self._cafe_log("[통신] 추가 pending 태스크 없음 — 종료")
                            break
                        t = tasks[0]
                        new_task_id = t.get("id")
                        new_task_user_id = t.get("user_id")
                        new_kw = (t.get("keyword") or "").strip()
                        if not new_task_id or not new_kw:
                            self._cafe_log("[통신] 태스크 키워드 없음 — 종료")
                            break
                        vm_name = (getattr(self, "_comm_vm_name_var", None) and self._comm_vm_name_var.get() or "").strip() or _load_gui_vm_config().get("VM_NAME", "")
                        if not claim_post_task_for_gui(new_task_id, new_task_user_id, vm_name=vm_name or None, log=self._cafe_log):
                            self._cafe_log("[통신] 태스크 선점 실패 — 종료")
                            break
                        current_task_id = new_task_id
                        current_task_user_id = new_task_user_id
                        keywords_to_use = [new_kw]
                        keys = fetch_user_coupang_keys(user_id=new_task_user_id, log=self._cafe_log)
                        if not keys:
                            self._cafe_log("[통신] 새 태스크 소유자 쿠팡키 미등록 — 스킵")
                            break
                        coupang_ak, coupang_sk = keys[0], keys[1]
                        self._cafe_log(f"[통신] 다음 태스크 선점 — 키워드: {new_kw!r}")
                    _comm_cycle_count += 1
                if comm_mode_agent_cafe:
                    try:
                        cafes = _fetch_comm_cafes()
                        if not cafes:
                            self._cafe_log("[통신] agent_cafe_lists에 카페 없음 — 스킵")
                            break
                    except Exception as e:
                        self._cafe_log(f"[통신] agent_cafe_lists 조회 실패: {e}")
                        break
                    nid, npw = comm_naver_id, comm_naver_pw
                else:
                    acc = accounts[account_idx]
                    nid, npw = acc["id"], acc["pw"]
                if multi and len(accounts) > 1:
                    self._cafe_log(f"\n[다중아이디] {account_idx + 1}/{len(accounts)}번째 계정: {nid}")
                comm_mode = task_id is not None
                start_idx = getattr(self, "_last_cafe_idx", 0)
                post_count_val = 1 if comm_mode_agent_cafe else max(2, self.cafe_post_count_var.get())
                _paid = None if comm_mode_agent_cafe else (paid_members or None)
                _referrer = None if comm_mode_agent_cafe else referrer
                result = run_auto_posting(
                    login_id=nid, password=npw, cafes=cafes,
                    keywords=keywords_to_use, gemini_api_key=gk,
                    start_cafe_idx=start_idx,
                    search_limit=sl, image_save_dir=imd, log=log_prog,
                    stop_flag=lambda: getattr(self, '_posting_stop_flag', False),
                    driver_holder=self._driver_holder,
                    keyword_repeat_min=self.cafe_kw_repeat_min_var.get(),
                    keyword_repeat_max=self.cafe_kw_repeat_max_var.get(),
                    posting_interval_min=max(1, self.cafe_interval_min_var.get()),
                    posting_interval_max=max(1, self.cafe_interval_max_var.get()),
                    linebreak_enabled=self.cafe_linebreak_var.get(),
                    linebreak_max_chars=self.cafe_maxchars_var.get(),
                    link_btn_image=None,  # 더 이상 사용하지 않음 (댓글 방식)
                    coupang_access_key=coupang_ak,
                    coupang_secret_key=coupang_sk,
                    paid_members=_paid,
                    referrer=_referrer,
                    post_count=post_count_val,
                    use_product_name=self.cafe_use_product_name_var.get(),
                    category=self.selected_category.get(),
                    commission_image_folder=self.commission_image_folder_var.get().strip() or None,
                    program_username=program_username,
                    keep_driver_open=comm_mode,
                    comm_mode=comm_mode)

                if comm_mode_agent_cafe and cafes and len(cafes) > 0:
                    cafe_url = cafes[0].get("_cafe_url", "")
                    if cafe_url:
                        try:
                            from supabase_client import update_program_cafe_list_status, delete_agent_cafe_list
                            from datetime import datetime, timezone
                            sc = result.get("success", 0)
                            fail_reason = result.get("last_cafe_fail_reason")
                            if sc > 0:
                                update_program_cafe_list_status(cafe_url, naver_id=nid, last_posted_at=datetime.now(timezone.utc).isoformat(), log=self._cafe_log)
                                self._cafe_log("[통신] last_posted_at 갱신")
                            elif fail_reason in ("member_required", "button_not_found"):
                                delete_agent_cafe_list(cafe_url, naver_id=nid, log=self._cafe_log)
                                self._cafe_log("[통신] 글작성 실패 — 카페 리스트에서 삭제")
                        except Exception as e:
                            self._cafe_log(f"[통신] agent_cafe_lists 갱신 실패: {e}")
                    # 글작성 성공 시 즉시 post_tasks 완료 등록 (크롬 중간 종료해도 결과 보존)
                    if current_task_id and result.get("success", 0) > 0 and result.get("published_url"):
                        try:
                            from shared.gui_data import finish_post_task_for_gui
                            pub_url = result.get("published_url", "").strip()
                            finish_post_task_for_gui(current_task_id, current_task_user_id, success=True, published_url=pub_url, log=self._cafe_log)
                            self._comm_last_published_url = pub_url
                            self._comm_task_finished_success = True
                            self._cafe_log(f"[통신] 글작성 직후 작업완료 등록 (URL 저장): {pub_url[:50]}...")
                        except Exception as e:
                            self._cafe_log(f"[통신] 즉시 완료 등록 실패: {e}")

                sc = result.get("success", 0)
                fl = result.get("fail", 0)
                next_idx = result.get("next_cafe_idx")
                if next_idx is not None:
                    self._last_cafe_idx = next_idx
                    self._save_cafe_settings()
                self._safe(self._update_cafe_progress, 100,
                           f"완료 — 성공: {sc} / 실패: {fl}")

                if getattr(self, "_posting_stop_flag", False):
                    break
                # 통신모드 agent_cafe: 1사이클 후 다음 사이클로 continue
                if comm_mode_agent_cafe:
                    continue
                # 서버뉴카페 모드: 모두 완료 후 처음 카페부터 반복
                if use_agent_cafe_loop:
                    self._cafe_log("\n[서버뉴카페] 처음 카페부터 재시작...")
                    wait_sec = min(wait_min * 60, 3600)
                    for _ in range(wait_sec):
                        if getattr(self, "_posting_stop_flag", False):
                            break
                        time.sleep(1)
                    continue
                account_idx += 1
                if account_idx >= len(accounts):
                    if infinite:
                        account_idx = 0
                        self._cafe_log(f"\n[무한반복] 첫 아이디부터 재시작. {wait_min}분 대기...")
                    else:
                        break
                if account_idx < len(accounts) or (infinite and account_idx == 0):
                    self._cafe_log(f"\n[다중아이디] 다음 계정으로 전환. {wait_min}분 대기...")
                    wait_sec = min(wait_min * 60, 3600)
                    for _ in range(wait_sec):
                        if getattr(self, "_posting_stop_flag", False):
                            break
                        time.sleep(1)
            self._safe(self._set_status, "done", f"포스팅 완료")
        except Exception as e:
            self._cafe_log(f"[포스팅] 실행 중 오류: {e}")
            result = {"success": 0, "fail": 0, "error": str(e)}
            self._safe(self._update_cafe_progress, 0, "오류 발생")
            self._safe(self._set_status, "error", str(e))
        self.root.after(0, lambda: self._on_posting_done(task_id=task_id, result=result))

    def _on_posting_done(self, task_id=None, result=None):
        self.is_posting = False
        if task_id and result is not None:
            pub = result.get("published_url")
            # 이미 글작성 직후 저장한 URL이 있으면 None으로 덮어쓰지 않음
            if pub or not getattr(self, "_comm_task_finished_success", False):
                self._comm_last_published_url = pub
        # task_id: 레거시(에이전트 모드 제거됨). post_tasks는 worker가 claim/finish 처리.
        # 자동재시작이 켜져 있으면 다음 지정 시간까지 타이머 예약
        if self._auto_restart_enabled:
            self._schedule_auto_restart()

    # ──────────────────────────────────────────────
    # 자동 재시작 설정
    # ──────────────────────────────────────────────
    def _open_auto_restart_settings(self):
        """자동 재시작 설정 팝업"""
        dlg = tk.Toplevel(self.root)
        dlg.title("자동 재시작 설정")
        dlg.configure(bg=BG_CARD)
        dlg.resizable(False, False)
        dlg.grab_set()

        # 크기/위치
        w, h = 400, 360
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        pad = 20

        # 제목
        tk.Label(dlg, text="자동 재시작 설정", font=F_TITLE,
                 bg=BG_CARD, fg=FG).pack(pady=(pad, 10))

        # 안내 문구
        tk.Label(dlg, text="포스팅 완료 후 매일 지정된 시간에\n자동으로 발행을 다시 시작합니다.",
                 font=F_SM, bg=BG_CARD, fg=FG_DIM,
                 justify="center").pack(pady=(0, 15))

        # ── 활성화 토글 ──
        enable_var = tk.BooleanVar(value=self._auto_restart_enabled)
        chk_frame = tk.Frame(dlg, bg=BG_CARD)
        chk_frame.pack(fill="x", padx=pad, pady=(0, 8))
        tk.Checkbutton(chk_frame, text="  자동 재시작 사용",
                       variable=enable_var, font=F,
                       bg=BG_CARD, fg=FG, activebackground=BG_CARD,
                       activeforeground=FG, selectcolor=BG_INPUT,
                       ).pack(side="left")

        # ── 블로그/카페 선택 ──
        type_frame = tk.Frame(dlg, bg=BG_CARD)
        type_frame.pack(fill="x", padx=pad, pady=(0, 8))
        tk.Label(type_frame, text="재시작 대상:", font=F,
                 bg=BG_CARD, fg=FG_LABEL).pack(side="left")
        blog_var = tk.BooleanVar(value=self._auto_restart_blog)
        cafe_var = tk.BooleanVar(value=self._auto_restart_cafe)
        tk.Checkbutton(type_frame, text="  블로그",
                       variable=blog_var, font=F_SM,
                       bg=BG_CARD, fg=FG, activebackground=BG_CARD,
                       activeforeground=FG, selectcolor=BG_INPUT,
                       ).pack(side="left", padx=(12, 0))
        tk.Checkbutton(type_frame, text="  카페",
                       variable=cafe_var, font=F_SM,
                       bg=BG_CARD, fg=FG, activebackground=BG_CARD,
                       activeforeground=FG, selectcolor=BG_INPUT,
                       ).pack(side="left", padx=(8, 0))

        # ── 시간 설정 ──
        time_frame = tk.Frame(dlg, bg=BG_CARD)
        time_frame.pack(fill="x", padx=pad, pady=(0, 8))

        tk.Label(time_frame, text="재시작 시간:", font=F,
                 bg=BG_CARD, fg=FG_LABEL).pack(side="left")

        hour_var = tk.StringVar(value=f"{self._auto_restart_hour:02d}")
        hour_spin = tk.Spinbox(time_frame, from_=0, to=23, width=4,
                               textvariable=hour_var,
                               font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                               buttonbackground=BG_HEADER,
                               highlightthickness=2, highlightbackground=BD,
                               highlightcolor=BD_FOCUS,
                               selectbackground="#cfe8ff", selectforeground=FG,
                               format="%02.0f", wrap=True)
        hour_spin.pack(side="left", padx=(10, 2), ipady=4)
        tk.Label(time_frame, text="시", font=F,
                 bg=BG_CARD, fg=FG_DIM).pack(side="left")

        min_var = tk.StringVar(value=f"{self._auto_restart_minute:02d}")
        min_spin = tk.Spinbox(time_frame, from_=0, to=59, width=4,
                              textvariable=min_var,
                              font=F, bg=BG_INPUT, fg=FG, relief="flat", bd=0,
                              buttonbackground=BG_HEADER,
                              highlightthickness=2, highlightbackground=BD,
                              highlightcolor=BD_FOCUS,
                              selectbackground="#cfe8ff", selectforeground=FG,
                              format="%02.0f", wrap=True)
        min_spin.pack(side="left", padx=(10, 2), ipady=4)
        tk.Label(time_frame, text="분", font=F,
                 bg=BG_CARD, fg=FG_DIM).pack(side="left")

        # ── 현재 상태 표시 ──
        status_text = ""
        if self._auto_restart_enabled:
            targets = []
            if self._auto_restart_blog:
                targets.append("블로그")
            if self._auto_restart_cafe:
                targets.append("카페")
            targets_str = "+".join(targets) if targets else "없음"
            status_text = (f"현재 상태: 활성 ({targets_str})  |  "
                           f"다음 실행: {self._auto_restart_hour:02d}:"
                           f"{self._auto_restart_minute:02d}")
            if self._auto_restart_timer_id is not None:
                now = datetime.datetime.now()
                target = now.replace(hour=self._auto_restart_hour,
                                     minute=self._auto_restart_minute,
                                     second=0, microsecond=0)
                if target <= now:
                    target += datetime.timedelta(days=1)
                remain = target - now
                hours_r = int(remain.total_seconds() // 3600)
                mins_r = int((remain.total_seconds() % 3600) // 60)
                status_text += f"  ({hours_r}시간 {mins_r}분 후)"
        else:
            status_text = "현재 상태: 비활성"

        status_lbl = tk.Label(dlg, text=status_text, font=F_SM,
                              bg=BG_CARD, fg="#7C5CFC")
        status_lbl.pack(pady=(5, 15))

        # ── 버튼 영역 ──
        btn_frame = tk.Frame(dlg, bg=BG_CARD)
        btn_frame.pack(fill="x", padx=pad, pady=(0, pad))

        def _apply():
            self._auto_restart_enabled = enable_var.get()
            self._auto_restart_hour = int(hour_var.get())
            self._auto_restart_minute = int(min_var.get())
            self._auto_restart_blog = blog_var.get()
            self._auto_restart_cafe = cafe_var.get()

            if self._auto_restart_enabled and not self._auto_restart_blog and not self._auto_restart_cafe:
                messagebox.showwarning("안내", "블로그 또는 카페 중 하나 이상을 선택해주세요.")
                return

            # 기존 타이머 취소
            if self._auto_restart_timer_id is not None:
                self.root.after_cancel(self._auto_restart_timer_id)
                self._auto_restart_timer_id = None

            if self._auto_restart_enabled:
                targets = []
                if self._auto_restart_blog:
                    targets.append("블로그")
                if self._auto_restart_cafe:
                    targets.append("카페")
                self._cafe_log(
                    f"[자동재시작] 활성화 — 매일 "
                    f"{self._auto_restart_hour:02d}:{self._auto_restart_minute:02d} "
                    f"에 자동 발행 ({'+'.join(targets)})")
                if not self.is_posting and not self.is_blog_posting:
                    self._schedule_auto_restart()
            else:
                self._cafe_log("[자동재시작] 비활성화")

            # 설정 자동저장
            self._save_cafe_settings()
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        _action_btn(btn_frame, "  적용  ", "#7C5CFC", "#6B4AEB",
                    _apply).pack(side="left", padx=(0, 8))
        _action_btn(btn_frame, "  취소  ", "#6b7280", "#545c66",
                    _cancel).pack(side="left")

    # ──────────────────────────────────────────────
    # 회원가입 / 로그인 / 로그아웃
    # ──────────────────────────────────────────────
    def _is_admin(self):
        """okdog 로그인 시 관리자"""
        try:
            from auth import get_session
            s = get_session()
            return (s or {}).get("username", "").strip().lower() == "okdog"
        except Exception:
            return False

    def _refresh_admin_ui(self):
        """관리자(okdog) 전용 UI 표시/숨김"""
        if hasattr(self, "use_paid_keywords_frame") and self.use_paid_keywords_frame.winfo_exists():
            if self._is_admin():
                self.use_paid_keywords_frame.grid()
            else:
                self.use_paid_keywords_frame.grid_remove()
                self.use_paid_member_keywords_var.set(False)

    def _update_auth_ui(self):
        """로그인 상태에 따라 버튼/라벨 업데이트"""
        if not getattr(self, "_auth_available", False):
            return
        try:
            from auth import is_logged_in, get_session, get_free_use_until, logout
            if is_logged_in():
                s = get_session()
                self.current_user_id = s.get("id") if s else None
                free_until = get_free_use_until() or "?"
                self._auth_btn_register.set_text(" 내 정보 ")
                self._auth_btn_register.set_command(self._open_my_info_dialog)
                self._auth_btn_login.set_text(" 로그아웃 ")
                self._auth_btn_login.set_command(self._on_logout)
                self._auth_status_label.config(text=f"사용 가능 기간: ~{free_until}")
                # [C] 로그인 시 Supabase에서 프로필/키워드 자동 로드
                self._apply_user_profile_from_supabase()
            else:
                self.current_user_id = None
                self._auth_btn_register.set_text(" 회원가입 ")
                self._auth_btn_register.set_command(self._open_register_dialog)
                self._auth_btn_login.set_text(" 로그인 ")
                self._auth_btn_login.set_command(self._open_login_dialog)
                self._auth_status_label.config(text="")
            self._refresh_admin_ui()
        except Exception:
            pass

    def _apply_user_profile_from_supabase(self):
        """[C] 로그인 사용자의 프로필(쿠팡 키) 및 키워드를 Supabase에서 가져와 자동 입력"""
        try:
            from auth import get_session
            from shared.gui_data import get_user_profile, get_user_keywords_or_fallback
            s = get_session()
            if not s:
                return
            username = s.get("username") or ""
            user_id = s.get("id")
            profile = get_user_profile(username=username, user_id=user_id, log=self._log)
            if profile:
                ak = profile.get("coupang_access_key", "")
                sk = profile.get("coupang_secret_key", "")
                if ak and hasattr(self, "coupang_ak_var"):
                    self.coupang_ak_var.set(ak)
                if sk and hasattr(self, "coupang_sk_var"):
                    self.coupang_sk_var.set(sk)
                self._log("[Supabase] 사용자 프로필(쿠팡 키) 자동 입력됨")
            kw = get_user_keywords_or_fallback(username=username, user_id=user_id, log=self._log)
            if kw:
                self.keywords = kw
                if hasattr(self, "_refresh_keywords_display"):
                    self._refresh_keywords_display()
                self._log(f"[Supabase] 키워드 {len(kw)}개 로드됨")
        except Exception as e:
            self._log(f"[Supabase] 프로필 로드 실패: {e}")

    def _open_register_dialog(self):
        """회원가입 팝업"""
        dlg = tk.Toplevel(self.root)
        dlg.title("회원가입")
        dlg.configure(bg=BG_CARD)
        dlg.resizable(False, False)
        dlg.grab_set()
        try:
            ico_path = os.path.join(BASE_DIR, "app_icon.ico")
            if os.path.exists(ico_path):
                dlg.iconbitmap(ico_path)
        except Exception:
            pass
        w, h = 400, 380
        x = self.root.winfo_x() + max(0, (self.root.winfo_width() - w) // 2)
        y = self.root.winfo_y() + max(0, (self.root.winfo_height() - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        pad = 20
        tk.Label(dlg, text="회원가입", font=F_TITLE, bg=BG_CARD, fg=FG).pack(pady=(pad, 12))
        form = tk.Frame(dlg, bg=BG_CARD)
        form.pack(fill="x", padx=pad, pady=4)
        form.columnconfigure(1, weight=1)
        def _bordered_entry(parent, row, var, show=None):
            f = tk.Frame(parent, highlightthickness=1, highlightbackground=BD, highlightcolor=BD_FOCUS, bg=BD)
            f.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=6)
            e = tk.Entry(f, textvariable=var, font=F, width=24, bg=BG_INPUT, relief="flat", bd=0)
            e.pack(fill="both", expand=True, padx=1, pady=1)
            if show:
                e.config(show=show)
            return e
        tk.Label(form, text="아이디:", font=F_SM, bg=BG_CARD, fg=FG_LABEL, width=12, anchor="e").grid(row=0, column=0, sticky="e", pady=6)
        v1 = tk.StringVar()
        _bordered_entry(form, 0, v1)
        tk.Label(form, text="비밀번호:", font=F_SM, bg=BG_CARD, fg=FG_LABEL, width=12, anchor="e").grid(row=1, column=0, sticky="e", pady=6)
        v2 = tk.StringVar()
        _bordered_entry(form, 1, v2, show="*")
        tk.Label(form, text="추천인 아이디:", font=F_SM, bg=BG_CARD, fg=FG_LABEL, width=12, anchor="e").grid(row=2, column=0, sticky="e", pady=6)
        v3 = tk.StringVar()
        _bordered_entry(form, 2, v3)
        tk.Label(form, text="(선택)", font=F_SM, bg=BG_CARD, fg=FG_DIM).grid(row=2, column=2, sticky="w", padx=(4, 0))

        # 약관 동의 체크박스 + [약관 보기] 버튼
        agree_var = tk.BooleanVar(value=False)
        terms_row = tk.Frame(dlg, bg=BG_CARD)
        terms_row.pack(fill="x", padx=pad, pady=(12, 0))
        tk.Checkbutton(terms_row, text="이용약관 및 면책고지 사항을 확인하였으며 이에 동의합니다",
                       variable=agree_var, font=F_SM, bg=BG_CARD, fg=FG, anchor="w",
                       activebackground=BG_CARD, activeforeground=FG, selectcolor=BG_CARD,
                       command=lambda: _on_agree_change()).pack(anchor="w")
        terms_btn_row = tk.Frame(dlg, bg=BG_CARD)
        terms_btn_row.pack(fill="x", padx=pad, pady=(2, 0))
        _soft_btn(terms_btn_row, " [약관 보기] ", lambda: self._open_terms_dialog(dlg)).pack(anchor="w")

        msg_lbl = tk.Label(dlg, text="", font=F_SM, bg=BG_CARD, fg=RED)
        msg_lbl.pack(pady=(8, 0))

        def _do_register():
            from auth import register
            msg_lbl.config(text="처리 중...", fg=FG_DIM)
            dlg.update()
            ok, msg = register(v1.get(), v2.get(), v3.get(), log=self._log)
            msg_lbl.config(text=msg, fg=GREEN if ok else RED)
            if ok:
                dlg.after(800, dlg.destroy)
                self._update_auth_ui()

        def _on_agree_change():
            register_btn.set_enabled(agree_var.get())

        btn_f = tk.Frame(dlg, bg=BG_CARD)
        btn_f.pack(fill="x", padx=pad, pady=(16, pad))
        register_btn = _action_btn(btn_f, "  가입하기  ", TEAL, TEAL_H, _do_register)
        register_btn.pack(side="left", padx=(0, 8))
        register_btn.set_enabled(False)
        _action_btn(btn_f, "  취소  ", "#6b7280", "#545c66", dlg.destroy).pack(side="left")

    def _open_terms_dialog(self, parent):
        """약관 보기 팝업"""
        dlg = tk.Toplevel(parent)
        dlg.title("이용약관 및 면책고지")
        dlg.configure(bg=BG_CARD)
        dlg.resizable(True, True)
        dlg.grab_set()
        w, h = 520, 560
        x = parent.winfo_x() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_y() + max(0, (parent.winfo_height() - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        pad = 20

        tk.Label(dlg, text="📋 프로그램 이용약관 및 면책고지", font=F_TITLE, bg=BG_CARD, fg=FG).pack(pady=(pad, 12))

        txt_frame = tk.Frame(dlg, bg=BG_CARD)
        txt_frame.pack(fill="both", expand=True, padx=pad, pady=(0, 10))
        text = tk.Text(txt_frame, wrap="word", font=F_SM, bg=BG_INPUT, fg=FG,
                      relief="flat", padx=14, pady=12, insertbackground=FG,
                      selectbackground="#cfe8ff", borderwidth=0, spacing1=2)
        sb = tk.Scrollbar(txt_frame, command=text.yview)
        sb.pack(side="right", fill="y")
        text.config(yscrollcommand=sb.set)
        text.pack(fill="both", expand=True)

        terms_content = """제1조 (목적)
본 약관은 '포스팅 도우미'(이하 "프로그램") 개발자(이하 "판매자")가 제공하는 소프트웨어의 이용 조건 및 절차, 판매자와 이용자(이하 "회원") 간의 권리, 의무 및 책임 사항을 규정함을 목적으로 합니다.

제2조 (서비스 이용 및 승인)
회원은 본 약관에 동의하고 회원가입을 완료함으로써 서비스를 이용할 수 있습니다.

• 라이선스 관리: 본 프로그램은 쿠팡 Access Key를 기준으로 실행 대수를 제한하며, 회원은 본인 소유의 유효한 키를 사용해야 합니다.

• 무료 사용 기간: 가입 시점으로부터 6개월간 무료 이용 권한이 부여되며, 기간 만료 후에는 서비스가 제한될 수 있습니다.

제3조 (회원의 의무 및 금지사항)
회원은 본 프로그램을 마케팅 보조 용도로만 사용해야 하며, 플랫폼(네이버, 쿠팡 등)의 가이드라인을 준수할 책임이 있습니다.

• 비정상적 이용 금지: 플랫폼 서버에 과도한 부하를 주거나, 타인의 계정을 도용하여 포스팅하는 등 비정상적인 방법으로 시스템에 접근하는 행위를 금지합니다.

• 재판매 금지: 회원은 구매한 프로그램을 무단 복제, 분해, 재판매하거나 제3자에게 배포할 수 없습니다.

제4조 (개인정보 수집 및 보안)
판매자는 서비스 제공 및 라이선스 확인을 위해 아이디, 비밀번호, 쿠팡 API 키 정보를 수집 및 저장합니다.

수집된 정보는 실행 대수 확인 및 서비스 운영 목적으로만 사용되며, 회원의 명시적 동의 없이 제3자에게 제공되지 않습니다.

제5조 (면책조항 및 책임의 제한) - 중요
• 플랫폼 제재 관련: 본 프로그램은 자동화 툴로서, 네이버 및 쿠팡의 운영 정책에 따라 게시글 삭제, 검색 노출 제한, 계정 정지 등의 불이익을 받을 수 있습니다. 판매자는 플랫폼의 정책 변화로 인해 발생하는 어떠한 유무형의 손해에 대해서도 책임을 지지 않습니다.

• 수익 보장 불가: 본 프로그램은 포스팅을 돕는 도구일 뿐이며, 이를 통한 수익 발생이나 검색 순위 상위 노출을 보장하지 않습니다.

• 서비스 중단: 플랫폼의 API 변경, 서버 점검, 천재지변 등으로 인해 서비스가 일시적 또는 영구적으로 중단될 수 있으며, 이로 인한 보상 책임은 없습니다.

• 콘텐츠 책임: 프로그램을 통해 발행되는 콘텐츠의 저작권 및 내용에 대한 모든 책임은 회원 본인에게 있습니다."""

        text.insert("1.0", terms_content)
        text.config(state="disabled")

        btn_f = tk.Frame(dlg, bg=BG_CARD)
        btn_f.pack(fill="x", padx=pad, pady=(0, pad))
        _action_btn(btn_f, "  닫기  ", TEAL, TEAL_H, dlg.destroy).pack(side="left")

    def _open_login_dialog(self):
        """로그인 팝업"""
        dlg = tk.Toplevel(self.root)
        dlg.title("로그인")
        dlg.configure(bg=BG_CARD)
        dlg.resizable(False, False)
        dlg.grab_set()
        try:
            ico_path = os.path.join(BASE_DIR, "app_icon.ico")
            if os.path.exists(ico_path):
                dlg.iconbitmap(ico_path)
        except Exception:
            pass
        w, h = 380, 300
        x = self.root.winfo_x() + max(0, (self.root.winfo_width() - w) // 2)
        y = self.root.winfo_y() + max(0, (self.root.winfo_height() - h) // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")
        pad = 20
        tk.Label(dlg, text="로그인", font=F_TITLE, bg=BG_CARD, fg=FG).pack(pady=(pad, 12))
        form = tk.Frame(dlg, bg=BG_CARD)
        form.pack(fill="x", padx=pad, pady=4)
        form.columnconfigure(1, weight=1)
        def _bordered_entry(parent, row, var, show=None):
            f = tk.Frame(parent, highlightthickness=1, highlightbackground=BD, highlightcolor=BD_FOCUS, bg=BD)
            f.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=6)
            e = tk.Entry(f, textvariable=var, font=F, width=24, bg=BG_INPUT, relief="flat", bd=0)
            e.pack(fill="both", expand=True, padx=1, pady=1)
            if show:
                e.config(show=show)
            return e
        tk.Label(form, text="아이디:", font=F_SM, bg=BG_CARD, fg=FG_LABEL, width=12, anchor="e").grid(row=0, column=0, sticky="e", pady=6)
        v1 = tk.StringVar()
        _bordered_entry(form, 0, v1)
        tk.Label(form, text="비밀번호:", font=F_SM, bg=BG_CARD, fg=FG_LABEL, width=12, anchor="e").grid(row=1, column=0, sticky="e", pady=6)
        v2 = tk.StringVar()
        _bordered_entry(form, 1, v2, show="*")
        msg_lbl = tk.Label(dlg, text="", font=F_SM, bg=BG_CARD, fg=RED)
        msg_lbl.pack(pady=(8, 0))
        def _do_login():
            from auth import login
            msg_lbl.config(text="처리 중...", fg=FG_DIM)
            dlg.update()
            ok, msg, _ = login(v1.get(), v2.get(), log=self._log)
            msg_lbl.config(text=msg, fg=GREEN if ok else RED)
            if ok:
                dlg.after(500, dlg.destroy)
                self._update_auth_ui()
        btn_f = tk.Frame(dlg, bg=BG_CARD)
        btn_f.pack(fill="x", padx=pad, pady=(20, 24))
        _action_btn(btn_f, "  로그인  ", TEAL, TEAL_H, _do_login).pack(side="left", padx=(0, 8))
        _action_btn(btn_f, "  취소  ", "#6b7280", "#545c66", dlg.destroy).pack(side="left")

    def _open_my_info_dialog(self):
        """내 정보 팝업"""
        try:
            from auth import get_session
            s = get_session()
            if not s:
                return
            msg = f"아이디: {s.get('username', '')}\n사용 가능 기간: ~{s.get('free_use_until', '')}"
            messagebox.showinfo("내 정보", msg)
        except Exception:
            pass

    def _on_logout(self):
        try:
            from auth import logout, remove_active_session
            if getattr(self, "_auth_session_id", None):
                remove_active_session(self._auth_session_id, log=self._log)
                self._auth_session_id = None
            logout(log=self._log)
            self._update_auth_ui()
        except Exception:
            pass

    def _schedule_auto_restart(self):
        """다음 지정 시간까지의 딜레이를 계산하여 타이머 예약"""
        # 기존 타이머 취소
        if self._auto_restart_timer_id is not None:
            self.root.after_cancel(self._auto_restart_timer_id)
            self._auto_restart_timer_id = None

        if not self._auto_restart_enabled:
            return

        now = datetime.datetime.now()
        target = now.replace(hour=self._auto_restart_hour,
                             minute=self._auto_restart_minute,
                             second=0, microsecond=0)
        # 이미 지난 시간이면 다음 날
        if target <= now:
            target += datetime.timedelta(days=1)

        delay_sec = (target - now).total_seconds()
        hours_r = int(delay_sec // 3600)
        mins_r = int((delay_sec % 3600) // 60)

        self._cafe_log(
            f"[자동재시작] 다음 실행 예약: "
            f"{target.strftime('%Y-%m-%d %H:%M')} "
            f"({hours_r}시간 {mins_r}분 후)")

        # tkinter after는 밀리초 단위, 최대 24시간+α
        delay_ms = int(delay_sec * 1000)
        self._auto_restart_timer_id = self.root.after(
            delay_ms, self._auto_restart_trigger)

    def _auto_restart_trigger(self):
        """지정 시간이 되면 자동으로 발행 시작"""
        self._auto_restart_timer_id = None

        if not self._auto_restart_enabled:
            return

        targets = []
        if self._auto_restart_blog:
            targets.append("블로그")
        if self._auto_restart_cafe:
            targets.append("카페")
        if not targets:
            self._schedule_auto_restart()
            return

        self._cafe_log(
            f"\n{'=' * 55}\n"
            f"  [자동재시작] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} "
            f"자동 발행을 시작합니다. ({'+'.join(targets)})\n"
            f"{'=' * 55}")

        # 이미 포스팅 중이면 스킵
        if self.is_posting or self.is_blog_posting:
            self._cafe_log("[자동재시작] 현재 포스팅 진행 중 — 완료 후 다시 예약됩니다.")
            self._schedule_auto_restart()
            return

        # 블로그+카페 둘 다 선택: 블로그 먼저, 완료 후 카페
        if self._auto_restart_blog and self._auto_restart_cafe:
            self._auto_restart_pending_cafe = True
            self._on_start_blog_posting(skip_confirm=True)
        elif self._auto_restart_blog:
            self._on_start_blog_posting(skip_confirm=True)
        else:
            self._on_start_posting(skip_confirm=True)

    def _cancel_auto_restart(self):
        """자동재시작 타이머 취소"""
        if self._auto_restart_timer_id is not None:
            self.root.after_cancel(self._auto_restart_timer_id)
            self._auto_restart_timer_id = None
            self._cafe_log("[자동재시작] 타이머 취소됨")

    # ──────────────────────────────────────────────
    # RESULT
    # ──────────────────────────────────────────────
    def _on_result_kw_change(self, *_):
        if not getattr(self, "result_text", None) or not getattr(self, "result_kw_var", None):
            return
        kw = self.result_kw_var.get()
        if kw in self.results:
            c = self.results[kw].get("post_content", "")
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", c)

    def _copy_result(self):
        if not getattr(self, "result_text", None):
            return
        txt = self.result_text.get("1.0", "end").strip()
        if txt:
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self._log("[복사] 클립보드에 복사됨")
            self.bottom_status.config(text="✔ 복사 완료")
        else:
            messagebox.showinfo("안내", "복사할 내용이 없습니다.")

    # ──────────────────────────────────────────────
    # LOGGING
    # ──────────────────────────────────────────────
    def _log(self, msg):
        if "[BLOG]" in msg or "[CAFE]" in msg or "[실행시작]" in msg:
            self.append_log_global(msg)
        if not getattr(self, "log_text", None):
            return
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _do)

    def _clear_log(self):
        if not getattr(self, "log_text", None):
            return
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _cafe_log(self, msg):
        if "[BLOG]" in msg or "[CAFE]" in msg or "[실행시작]" in msg:
            self.append_log_global(msg)
        def _do():
            self.cafe_log_text.config(state="normal")
            self.cafe_log_text.insert("end", msg + "\n")
            self.cafe_log_text.see("end")
            self.cafe_log_text.config(state="disabled")
        self.root.after(0, _do)

    def _clear_cafe_log(self):
        self.cafe_log_text.config(state="normal")
        self.cafe_log_text.delete("1.0", "end")
        self.cafe_log_text.config(state="disabled")

    # ──────────────────────────────────────────────
    # PROGRESS
    # ──────────────────────────────────────────────
    def _update_progress(self, pct, text=""):
        self._progress_pct = pct
        self.progress_canvas.update_idletasks()
        w = self.progress_canvas.winfo_width()
        bw = int(w * pct / 100)
        self.progress_canvas.coords(self.progress_bar_id, 0, 0, bw, 22)
        self.progress_canvas.itemconfig(
            self.progress_bar_id, fill=GREEN if pct >= 100 else POINT)
        self.progress_canvas.itemconfig(self.progress_text_id,
                                         text=text or f"{pct}%")
        self.bottom_status.config(text=text)

    def _update_cafe_progress(self, pct, text=""):
        self.cafe_progress_canvas.update_idletasks()
        w = self.cafe_progress_canvas.winfo_width()
        bw = int(w * pct / 100)
        self.cafe_progress_canvas.coords(self.cafe_progress_bar, 0, 0, bw, 22)
        self.cafe_progress_canvas.itemconfig(self.cafe_progress_bar, fill=GREEN)
        self.cafe_progress_canvas.itemconfig(self.cafe_progress_text,
                                              text=text or f"{pct}%")

    # ──────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────
    def _set_status(self, state, text=""):
        c = {"running": GREEN, "done": POINT,
             "error": RED, "stopped": FG_DIM}.get(state, FG_DIM)
        self.status_dot.config(fg=c)
        self.status_text.config(text=text, fg=c)

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────
    def _sec(self, parent, text):
        tk.Label(parent, text=text, font=F_SEC, bg=parent["bg"],
                 fg=FG, anchor="w").pack(fill="x", pady=(0, 8))

    def _lbl(self, parent, text, row):
        tk.Label(parent, text=text, font=F_SM, bg=BG_CARD,
                 fg=FG_LABEL, anchor="e", padx=8
                 ).grid(row=row, column=0, sticky="e", pady=8)

    def _safe(self, func, *args, **kw):
        self.root.after(0, lambda: func(*args, **kw))


# ============================================================
def _on_app_exit():
    """앱 종료 시 active_sessions 세션 제거"""
    try:
        app = getattr(_on_app_exit, "_app", None)
        if app and getattr(app, "_auth_session_id", None):
            from auth import remove_active_session
            remove_active_session(app._auth_session_id)
    except Exception:
        pass


if __name__ == "__main__":
    # [E] 실행 확인용 로그
    try:
        from shared.sb import load_config
        cfg = load_config()
        if cfg is None:
            from shared.sb import _config_error
            print(f"[GUI] config 로드 실패: {_config_error}", flush=True)
        else:
            proj = cfg.get("PROJECT", "")
            url = cfg.get("SUPABASE_URL", "")
            print(f"[GUI] PROJECT={proj}, SUPABASE_URL={url[:50]}..." if len(url) > 50 else f"[GUI] PROJECT={proj}, SUPABASE_URL={url}", flush=True)
    except Exception as e:
        print(f"[GUI] config 로드 실패: {e}", flush=True)

    root = tk.Tk()
    app = App(root)
    _on_app_exit._app = app
    atexit.register(_on_app_exit)
    root.mainloop()
