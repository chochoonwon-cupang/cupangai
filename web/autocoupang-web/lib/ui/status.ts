import * as React from "react";
import { Badge, badgeVariants } from "@/components/ui/badge";
import type { VariantProps } from "class-variance-authority";

type TaskStatus = "pending" | "assigned" | "doing" | "done" | "failed" | "canceled";
type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];

const STATUS_CONFIG: Record<TaskStatus, { label: string; variant: NonNullable<BadgeVariant> }> = {
  pending: { label: "대기", variant: "info" },
  assigned: { label: "진행중", variant: "info" },
  doing: { label: "진행중", variant: "info" },
  done: { label: "완료", variant: "success" },
  failed: { label: "실패", variant: "destructive" },
  canceled: { label: "취소", variant: "secondary" },
};

export function getStatusBadge(status: string) {
  const config = STATUS_CONFIG[status as TaskStatus] ?? {
    label: status || "-",
    variant: "secondary" as const,
  };
  return { label: config.label, variant: config.variant };
}

export function StatusBadge(props: { status: string }) {
  const { label, variant } = getStatusBadge(props.status);
  return React.createElement(Badge, { variant: variant ?? "secondary" }, label);
}
