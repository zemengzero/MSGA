import * as React from "react";
import { cn } from "../../lib/utils";

const Textarea = React.forwardRef(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "w-full resize-none rounded-[12px] border border-[#15140f26] bg-[#f7f1de66] px-3.5 py-3 text-[13px] leading-7 text-[#15140f] outline-none transition-colors placeholder:text-[#8b8676] focus-visible:border-[#ed6f5c] focus-visible:ring-2 focus-visible:ring-[#ed6f5c33]",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export { Textarea };
