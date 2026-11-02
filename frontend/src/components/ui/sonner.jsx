import { Toaster as Sonner } from "sonner";

export function Toaster(props) {
  return (
    <Sonner
      theme="light"
      position="bottom-right"
      gap={8}
      offset={16}
      toastOptions={{
        classNames: {
          toast:
            "!rounded-[12px] !border-0 !bg-[#f7f1de] !text-[#15140f] !text-[14px] !shadow-[0_20px_40px_-20px_rgba(21,20,15,0.35),inset_0_0_0_1px_rgba(21,20,15,0.08)]",
          description: "!text-[#5a5448] !text-[14px]",
          actionButton: "!rounded-full !bg-[#ed6f5c] !text-white",
          cancelButton: "!rounded-full !bg-[#ece4cf] !text-[#15140f]",
          icon: "!text-[#15140f]",
        },
      }}
      {...props}
    />
  );
}
