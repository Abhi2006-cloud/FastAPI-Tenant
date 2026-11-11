import React, { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import axios from "axios";

export const ColdStartBanner: React.FC = () => {
  const [isWaking, setIsWaking] = useState(false);

  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    let isCancelled = false;

    const checkServerHealth = async () => {
      // Set a 4 second timer to show the cold start message if waking takes longer
      timer = setTimeout(() => {
        if (!isCancelled) {
          setIsWaking(true);
        }
      }, 4000);

      const apiBaseUrl = (import.meta as unknown as { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL || "http://localhost:8000";

      let attempts = 0;
      const maxAttempts = 15;

      while (!isCancelled && attempts < maxAttempts) {
        attempts++;
        try {
          await axios.get(`${apiBaseUrl}/health/live`, { timeout: 8000 });
          // Success: server is awake!
          if (timer) clearTimeout(timer);
          if (!isCancelled) setIsWaking(false);
          break;
        } catch {
          // If server is cold starting, wait 3 seconds and retry
          if (isCancelled) break;
          await new Promise((res) => setTimeout(res, 3000));
        }
      }
    };

    checkServerHealth();

    return () => {
      isCancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (!isWaking) return null;

  return (
    <div
      role="status"
      className="bg-[#FFFBEB] border-b border-[#FEF3C7] text-[#92400E] px-4 py-2 text-[13px] flex items-center justify-center gap-2 select-none z-50 sticky top-0"
    >
      <Loader2 className="w-3.5 h-3.5 animate-spin text-[#D97706]" />
      <span>Free hosting is waking the server. This can take up to a minute.</span>
    </div>
  );
};
