"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function UserAuthPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMsg(null);

    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setMsg("가입 완료! 이메일 인증이 필요할 수 있어요. 메일함을 확인해 주세요.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        setMsg("로그인 성공! 이 창을 닫고 서비스로 돌아가세요.");
      }
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : "오류가 발생했어요.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#0b1220" }}>
      <div style={{ width: 360, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 16, padding: 18 }}>
        <div style={{ color: "white", fontSize: 18, fontWeight: 700 }}>
          {mode === "login" ? "사용자 로그인" : "사용자 회원가입"}
        </div>
        <div style={{ color: "rgba(255,255,255,0.65)", fontSize: 12, marginTop: 6 }}>
          * 기존 프로그램 로그인과 별개 계정입니다.
        </div>

        <form onSubmit={onSubmit} style={{ marginTop: 14, display: "grid", gap: 10 }}>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="이메일"
            type="email"
            required
            style={{ padding: 12, borderRadius: 12, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "white", outline: "none" }}
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="비밀번호"
            type="password"
            required
            style={{ padding: 12, borderRadius: 12, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "white", outline: "none" }}
          />

          <button
            type="submit"
            disabled={loading}
            style={{ padding: 12, borderRadius: 12, border: "none", background: "#f97316", color: "white", fontWeight: 700, cursor: "pointer", opacity: loading ? 0.7 : 1 }}
          >
            {loading ? "처리중..." : mode === "login" ? "로그인" : "회원가입"}
          </button>

          <button
            type="button"
            onClick={() => setMode(mode === "login" ? "signup" : "login")}
            style={{ padding: 10, borderRadius: 12, border: "1px solid rgba(255,255,255,0.12)", background: "transparent", color: "rgba(255,255,255,0.8)", cursor: "pointer" }}
          >
            {mode === "login" ? "회원가입으로 전환" : "로그인으로 전환"}
          </button>
        </form>

        {msg && (
          <div style={{ marginTop: 12, color: "rgba(255,255,255,0.85)", fontSize: 12, lineHeight: 1.4 }}>
            {msg}
          </div>
        )}
      </div>
    </div>
  );
}
