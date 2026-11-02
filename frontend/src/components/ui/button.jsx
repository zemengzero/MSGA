import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva } from "class-variance-authority";
import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full border border-transparent text-[14px] font-medium tracking-[-0.005em] transition-[background,color,transform,box-shadow] duration-150 outline-none focus-visible:ring-2 focus-visible:ring-[#ed6f5c55] focus-visible:ring-offset-2 focus-visible:ring-offset-[#efe7d2] disabled:pointer-events-none disabled:opacity-40 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-[#ed6f5c] text-white shadow-[0_14px_26px_-16px_rgba(237,111,92,0.95)] hover:bg-[#e35f4c]",
        secondary:
          "border-[#15140f33] bg-transparent text-[#15140f] hover:border-[#15140f] hover:bg-[#15140f0a]",
        outline:
          "border-[#15140f33] bg-transparent text-[#15140f] hover:border-[#15140f] hover:bg-[#15140f0a]",
        ghost: "text-[#5a5448] hover:bg-[#e8dfc9] hover:text-[#15140f]",
        destructive: "bg-[#c0442f] text-white hover:bg-[#a83a27]",
        link: "text-[#15140f] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-[18px] [&_svg]:size-4",
        sm: "h-7 px-3 text-[14px] [&_svg]:size-3.5",
        lg: "h-11 px-6 text-[14px] [&_svg]:size-4",
        icon: "size-8 [&_svg]:size-4",
        "icon-sm": "size-7 [&_svg]:size-3.5",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

const Button = React.forwardRef(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
