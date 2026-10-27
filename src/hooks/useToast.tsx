import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

interface Toast {
  id: number;
  tone: "success" | "error";
  text: string;
}

interface ToastApi {
  success: (text: string) => void;
  error: (text: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => setToasts((items) => items.filter((t) => t.id !== id)), []);
  const push = useCallback(
    (tone: Toast["tone"], text: string) => {
      const id = nextId.current++;
      setToasts((items) => [...items.slice(-3), { id, tone, text }]);
      window.setTimeout(() => dismiss(id), tone === "error" ? 9000 : 5000);
    },
    [dismiss],
  );
  const api = useMemo<ToastApi>(
    () => ({ success: (text) => push("success", text), error: (text) => push("error", text) }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 lg:bottom-6 lg:items-end lg:px-6"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex max-w-md items-start gap-3 rounded-md border px-4 py-3 text-sm ${
              toast.tone === "error" ? "border-high bg-high-bg text-ink" : "border-low bg-low-bg text-ink"
            }`}
          >
            <span aria-hidden="true" className="font-bold">
              {toast.tone === "error" ? "!" : "✓"}
            </span>
            <span>{toast.text}</span>
            <button
              type="button"
              className="ml-2 font-semibold underline"
              onClick={() => dismiss(toast.id)}
              aria-label="Dismiss message"
            >
              Close
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const value = useContext(ToastContext);
  if (!value) throw new Error("useToast must be used inside ToastProvider");
  return value;
}
