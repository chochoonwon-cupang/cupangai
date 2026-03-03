import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-lg px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-zinc-900 text-zinc-50 dark:bg-zinc-50 dark:text-zinc-900",
        secondary: "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50",
        destructive: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
        outline: "border border-zinc-200 bg-white dark:border-zinc-800",
        success: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
        warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400",
        info: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
