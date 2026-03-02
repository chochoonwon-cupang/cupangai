"use client";

import { useEffect, useState } from "react";

type Props = {
  onGuideClick?: () => void;
};

export default function FloatingHelpBanner({ onGuideClick }: Props) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex flex-col gap-3 pb-[env(safe-area-inset-bottom,0)] pr-[env(safe-area-inset-right,0)] transition-all duration-500 ${
        mounted ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
      }`}
    >
      {/* 사용자 로그인 버튼 */}
      <button
        type="button"
        onClick={() => {
          window.open(
            "/user-auth",
            "userAuth",
            "width=420,height=680,menubar=no,toolbar=no,location=no,status=no,resizable=yes,scrollbars=yes"
          );
        }}
        className="rounded-full bg-indigo-500 px-4 py-3 text-sm font-semibold text-white shadow-lg transition-all duration-300 hover:scale-105 hover:bg-indigo-600 md:px-6 md:py-4 md:text-base"
      >
        사용자 로그인
      </button>

      {/* 이용안내 버튼 */}
      <button
        type="button"
        onClick={onGuideClick}
        className="rounded-full bg-green-500 px-4 py-3 text-sm font-semibold text-white shadow-lg transition-all duration-300 hover:scale-105 hover:bg-green-600 md:px-6 md:py-4 md:text-base"
      >
        이용안내
      </button>

      {/* 카톡문의 버튼 */}
      <button
        type="button"
        onClick={() => console.log("카톡문의 클릭")}
        className="rounded-full bg-yellow-400 px-4 py-3 text-sm font-semibold text-black shadow-lg transition-all duration-300 hover:scale-105 hover:bg-yellow-500 md:px-6 md:py-4 md:text-base"
      >
        카톡문의
      </button>
    </div>
  );
}
