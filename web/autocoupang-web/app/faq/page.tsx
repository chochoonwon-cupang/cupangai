"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HelpCircle } from "lucide-react";

const faqs = [
  {
    q: "포스팅 1건당 비용은 얼마인가요?",
    a: "기본 70원부터 시작합니다. 프로필에서 발행금액을 확인할 수 있으며, 충전 후 잔액에서 1건당 비용이 차감됩니다.",
  },
  {
    q: "발행은 어떻게 시작하나요?",
    a: "대시보드에서 키워드를 입력하거나 엑셀/텍스트 파일로 bulk 등록한 뒤 '발행 시작' 버튼을 누르면 됩니다. 워커가 자동으로 작성·발행합니다.",
  },
  {
    q: "발행 계획은 어떻게 설정하나요?",
    a: "발행계획 메뉴에서 일일 발행량, 전체 발행량, 시작 시간을 설정할 수 있습니다.",
  },
  {
    q: "충전은 어떻게 하나요?",
    a: "충전/월렛 메뉴에서 충전 금액을 입력하고 결제를 진행하면 잔액에 바로 반영됩니다.",
  },
  {
    q: "작업 상태는 어디서 확인하나요?",
    a: "대시보드의 '오늘 완료 / 대기중 / 실패' KPI 카드에서 확인할 수 있습니다.",
  },
  {
    q: "API 키 발급을 위해 15만원 실적을 채우려면?",
    a: "쿠팡 파트너스 최종 승인을 위해서는 파트너스 링크를 통한 누적 판매가 15만원 이상이어야 합니다. 빠르게 승인받으려면 가족·지인 등 다른 계정으로 자신의 파트너스 링크를 통해 구매해야 합니다. 쿠팡파트너스 아이디와 구매하는 아이디가 같으면 실적으로 인정되지 않으니 유의해 주세요.",
  },
];

export default function FAQPage() {
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-2">
        <HelpCircle className="size-8 text-emerald-600 dark:text-emerald-500" />
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
          자주 묻는 질문
        </h1>
      </div>

      <div className="space-y-4">
        {faqs.map((faq, i) => (
          <Card key={i} className="rounded-2xl border shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
                Q. {faq.q}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                {faq.a}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
