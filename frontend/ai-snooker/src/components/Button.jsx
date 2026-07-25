import React from "react";
import { cn } from "../lib/utils";

export default function Button({
  children,
  variant = "primary",
  className,
  onClick,
}) {
  const variants = {
    primary: "bg-gray-900 hover:bg-black text-white",
    danger: "bg-red-600 hover:bg-red-700 text-white",
    success: "bg-green-600 hover:bg-green-700 text-white",
    outline: "border-2 border-gray-200 text-gray-700 hover:bg-gray-50",
  };

  return (
    <button
      className={cn(
        "px-6 py-3 font-bold rounded-lg transition",
        variants[variant],
        className,
      )}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
