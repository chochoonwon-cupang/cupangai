import * as React from "react";
import { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50 py-16 px-6 dark:border-zinc-800 dark:bg-zinc-900/50",
        className
      )}
    >
      {Icon && (
        <div className="mb-4 rounded-full bg-zinc-100 p-4 dark:bg-zinc-800">
          <Icon className="size-10 text-zinc-500 dark:text-zinc-400" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{title}</h3>
      {description && (
        <p className="mt-1 text-center text-sm text-zinc-500 dark:text-zinc-400">
          {description}
        </p>
      )}
      {action && (
        <Button className="mt-6" size="lg" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}
