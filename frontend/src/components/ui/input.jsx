import * as React from "react";
import { cn } from "../../lib/utils";

const Input = React.forwardRef(({ className, type, ...props }, ref) => (
  <input
    type={type}
    ref={ref}
    className={cn(
      "h-9 w-full rounded-[10px] border border-[#15140f26] bg-[#f7f1de80] px-3 text-[12.5px] text-[#15140f] outline-none transition-colors placeholder:text-[#8b8676] hover:border-[#15140f59] focus-visible:border-[#ed6f5c] focus-visible:ring-2 focus-visible:ring-[#ed6f5c33] disabled:pointer-events-none disabled:opacity-40",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";

export { Input };
