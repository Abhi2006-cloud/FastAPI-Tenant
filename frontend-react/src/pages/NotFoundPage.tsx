import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center p-6 text-center">
      <div className="bg-white border border-[#E4E4E7] rounded-[6px] p-8 max-w-sm w-full shadow-sm space-y-4">
        <div className="text-[32px] font-bold text-[#18181B] font-mono">404</div>
        <div>
          <h1 className="text-[16px] font-semibold text-[#18181B]">Page Not Found</h1>
          <p className="text-[13px] text-[#71717A] mt-1">
            The page you requested does not exist or has been moved.
          </p>
        </div>
        <div className="pt-2">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0F766E] hover:bg-[#115E59] text-white text-[13px] font-medium rounded-[6px] transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Workspace</span>
          </Link>
        </div>
      </div>
    </div>
  );
};

