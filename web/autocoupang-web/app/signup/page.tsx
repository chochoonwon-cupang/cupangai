"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useRouter } from "next/navigation";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSignup = async () => {
    setLoading(true);
    const { error } = await supabase.auth.signUp({ email, password });
    setLoading(false);

    if (error) return alert(error.message);

    alert("회원가입 완료! 이제 로그인 해주세요.");
    router.push("/login");
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-sm border rounded-xl p-6 space-y-4">
        <h1 className="text-xl font-bold">회원가입</h1>
        <input
          className="w-full border rounded-lg p-2"
          placeholder="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="w-full border rounded-lg p-2"
          placeholder="비밀번호"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button
          className="w-full rounded-lg bg-black text-white p-2 disabled:opacity-50"
          onClick={onSignup}
          disabled={loading}
        >
          {loading ? "처리중..." : "가입하기"}
        </button>

        <button
          className="w-full rounded-lg border p-2"
          onClick={() => router.push("/login")}
        >
          로그인으로
        </button>
      </div>
    </div>
  );
}
