import { cva } from "class-variance-authority";
import { cn } from "../../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2 py-[2px] font-sans text-[14px] font-medium leading-4 tracking-[0.02em]",
  {
    variants: {
      variant: {
        default: "border-[#15140f1f] bg-[#ece4cf80] text-[#5a5448]",
        outline: "border-[#15140f1f] bg-transparent text-[#8b8676]",
        solid: "border-transparent bg-[#15140f] text-[#f7f1de]",
        coral: "border-transparent bg-[#ed6f5c] text-white",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export function Badge({ className, variant, ...props }) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
