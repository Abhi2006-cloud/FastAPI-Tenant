import React, { createContext, useContext, useState, useEffect } from "react";
import { CheckCircle2, AlertTriangle, X } from "lucide-react";
import { onRateLimited } from "../api/client.ts";

interface ToastMessage {
  id: string;
  type: "success" | "warning" | "error";
  message: string;
  duration?: number;
}

interface ToastContextValue {
  showToast: (message: string, type?: "success" | "warning" | "error", duration?: number) => void;
  rateLimitCountdown: number | null;
}

const ToastContext = createContext<ToastContextValue>({
  showToast: () => {},
  rateLimitCountdown: null,
});

export const useToast = () => useContext(ToastContext);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [rateLimitCountdown, setRateLimitCountdown] = useState<number | null>(null);

  // Listen to 429 rate limit events from axios layer
  useEffect(() => {
    onRateLimited((seconds) => {
      setRateLimitCountdown(seconds);
    });

    return () => {
      onRateLimited(null);
    };
  }, []);

  // Countdown timer for rate limit
  useEffect(() => {
    if (rateLimitCountdown === null || rateLimitCountdown <= 0) {
      if (rateLimitCountdown === 0) setRateLimitCountdown(null);
      return;
    }

    const timer = setInterval(() => {
      setRateLimitCountdown((prev) => (prev && prev > 1 ? prev - 1 : null));
    }, 1000);

    return () => clearInterval(timer);
  }, [rateLimitCountdown]);

  const showToast = (message: string, type: "success" | "warning" | "error" = "success", duration = 4000) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message, duration }]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ showToast, rateLimitCountdown }}>
      {children}

      {/* Floating Toast Container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
        {rateLimitCountdown !== null && (
          <div className="pointer-events-auto flex items-center gap-2 p-3 bg-[#18181B] text-white text-[13px] rounded-[6px] shadow-lg border border-[#27272A]">
            <AlertTriangle className="w-4 h-4 text-[#F59E0B] shrink-0" />
            <span>Too many requests. Please wait {rateLimitCountdown}s before retrying.</span>
          </div>
        )}

        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-center justify-between gap-3 p-3 text-[13px] rounded-[6px] shadow border bg-white ${
              toast.type === "success"
                ? "border-[#BBF7D0] text-[#15803D]"
                : toast.type === "error"
                ? "border-[#FECACA] text-[#B91C1C]"
                : "border-[#FDE68A] text-[#B45309]"
            }`}
          >
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{toast.message}</span>
            </div>
            <button
              type="button"
              onClick={() => removeToast(toast.id)}
              className="p-1 hover:bg-[#F4F4F5] rounded text-[#71717A]"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};
