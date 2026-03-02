import { NextResponse } from "next/server";
import { createHash, randomBytes } from "crypto";
import { supabaseAdmin } from "@/lib/supabaseAdmin";

function hashPassword(password: string): string {
  const salt = randomBytes(16).toString("hex");
  const h = createHash("sha256").update(salt + password).digest("hex");
  return `${salt}:${h}`;
}

export async function POST(request: Request) {
  try {
    const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY;
    if (!url || !key) {
      return NextResponse.json(
        { error: "서버 설정 오류: .env.local에 SUPABASE_URL, SUPABASE_SERVICE_KEY를 설정하세요." },
        { status: 500 }
      );
    }

    const body = await request.json();
    const username = (body.username || "").trim();
    const password = (body.password || "").trim();
    const referrer_id = (body.referrer_id || body.referral_username || "").trim() || null;
    const agreed_to_terms = Boolean(body.agreed_to_terms);

    if (!username || username.length < 2) {
      return NextResponse.json({ error: "아이디는 2자 이상이어야 합니다." }, { status: 400 });
    }
    if (!password || password.length < 4) {
      return NextResponse.json({ error: "비밀번호는 4자 이상이어야 합니다." }, { status: 400 });
    }
    if (!agreed_to_terms) {
      return NextResponse.json({ error: "이용약관에 동의해주세요." }, { status: 400 });
    }

    const { data: existing } = await supabaseAdmin
      .from("users")
      .select("id")
      .eq("username", username)
      .limit(1);

    if (existing && existing.length > 0) {
      return NextResponse.json({ error: "이미 사용 중인 아이디입니다." }, { status: 400 });
    }

    const freeUntil = new Date();
    freeUntil.setMonth(freeUntil.getMonth() + 6);
    const free_use_until = freeUntil.toISOString().slice(0, 10);

    const row: Record<string, unknown> = {
      username,
      password_hash: hashPassword(password),
      max_devices: 5,
      free_use_until,
      referral_count: 0,
      agreed_to_terms: true,
    };
    if (referrer_id) {
      row.referrer_id = referrer_id;
    }

    const { error } = await supabaseAdmin.from("users").insert(row);

    if (error) {
      if (error.message?.includes("agreed_to_terms") || error.message?.includes("column")) {
        delete row.agreed_to_terms;
        const { error: retryErr } = await supabaseAdmin.from("users").insert(row);
        if (retryErr) {
          console.error("[API] register error:", retryErr);
          return NextResponse.json({ error: retryErr.message }, { status: 500 });
        }
      } else {
        console.error("[API] register error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
      }
    }

    if (referrer_id) {
      const { data: refRow } = await supabaseAdmin
        .from("users")
        .select("id, referral_count")
        .eq("username", referrer_id)
        .single();
      if (refRow) {
        const refCount = (refRow.referral_count ?? 0) as number;
        await supabaseAdmin
          .from("users")
          .update({ referral_count: refCount + 1 })
          .eq("id", refRow.id);
      }
    }

    return NextResponse.json({ ok: true, message: "회원가입이 완료되었습니다. 로그인해주세요." });
  } catch (e) {
    console.error("[API] register error:", e);
    return NextResponse.json(
      { error: "회원가입 처리 중 오류가 발생했습니다." },
      { status: 500 }
    );
  }
}
