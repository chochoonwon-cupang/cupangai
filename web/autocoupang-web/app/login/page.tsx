"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onLogin = async () => {
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);

    if (error) return alert(error.message);
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-sm border rounded-xl p-6 space-y-4">
        <h1 className="text-xl font-bold">로그인</h1>
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
          onClick={onLogin}
          disabled={loading}
        >
          {loading ? "처리중..." : "로그인"}
        </button>

        <button
          className="w-full rounded-lg border p-2"
          onClick={() => router.push("/signup")}
        >
          회원가입으로
        </button>
      </div>
    </div>
  );
}
