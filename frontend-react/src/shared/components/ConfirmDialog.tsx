import React, { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, X } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmWord?: string; // If provided, user MUST type this exact word/name to enable confirm
  confirmButtonText?: string;
  isDestructive?: boolean;
  onConfirm: () => void | Promise<void>;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  onOpenChange,
  title,
  description,
  confirmWord,
  confirmButtonText = "Confirm",
  isDestructive = true,
  onConfirm,
}) => {
  const [typedInput, setTypedInput] = useState("");
  const [loading, setLoading] = useState(false);

  const isMatch = !confirmWord || typedInput.trim() === confirmWord.trim();

  const handleConfirm = async () => {
    if (!isMatch || loading) return;
    setLoading(true);
    try {
      await onConfirm();
      handleClose();
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setTypedInput("");
    setLoading(false);
    onOpenChange(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={handleClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-50 backdrop-blur-[1px]" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-[6px] border border-[#E4E4E7] p-6 w-full max-w-[440px] shadow-lg z-50 focus:outline-none">
          <div className="flex items-center justify-between pb-3 border-b border-[#E4E4E7]">
            <div className="flex items-center gap-2">
              {isDestructive ? (
                <AlertTriangle className="w-4 h-4 text-[#DC2626]" />
              ) : null}
              <Dialog.Title className="text-[15px] font-semibold text-[#18181B]">
                {title}
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="text-[#71717A] hover:text-[#18181B] p-1 rounded hover:bg-[#FAFAFA]"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="py-4 space-y-4">
            <Dialog.Description className="text-[13px] text-[#52525B] leading-relaxed">
              {description}
            </Dialog.Description>

            {confirmWord ? (
              <div className="space-y-1.5">
                <label htmlFor="confirm-typed-word" className="block text-[12px] font-medium text-[#71717A]">
                  Type <span className="font-semibold text-[#18181B]">{confirmWord}</span> to confirm:
                </label>
                <input
                  id="confirm-typed-word"
                  type="text"
                  value={typedInput}
                  onChange={(e) => setTypedInput(e.target.value)}
                  placeholder={confirmWord}
                  className="w-full text-[13px] px-3 py-1.5 border border-[#E4E4E7] rounded-[6px] focus:outline-none focus:ring-1 focus:ring-[#DC2626]"
                />
              </div>
            ) : null}

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="px-3 py-1.5 border border-[#E4E4E7] text-[13px] text-[#52525B] hover:bg-[#FAFAFA] rounded-[6px]"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!isMatch || loading}
                onClick={handleConfirm}
                className={`px-4 py-1.5 text-[13px] font-medium rounded-[6px] text-white disabled:opacity-40 transition-colors ${
                  isDestructive
                    ? "bg-[#DC2626] hover:bg-[#B91C1C]"
                    : "bg-[#0F766E] hover:bg-[#115E59]"
                }`}
              >
                {loading ? "Processing..." : confirmButtonText}
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
