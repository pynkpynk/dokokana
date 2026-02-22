"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type ShareButtonsProps = {
  name: string;
  katakana: string;
  hiragana: string;
  script: "katakana" | "hiragana";
  triggerClassName?: string;
};

const siteUrlFromEnv = process.env.NEXT_PUBLIC_SITE_URL?.trim() || "";

function buildOrigin(): string {
  if (siteUrlFromEnv) {
    return siteUrlFromEnv.replace(/\/+$/, "");
  }
  if (typeof window !== "undefined" && window.location.origin) {
    return window.location.origin;
  }
  return "";
}

function buildShareUrl(name: string, kana: string, script: "katakana" | "hiragana"): string {
  const origin = buildOrigin();
  const params = new URLSearchParams({
    name,
    kana,
    script,
  });
  const path = `/?${params.toString()}`;
  return origin ? `${origin}${path}` : path;
}

function openShareUrl(url: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

async function copyToClipboard(value: string): Promise<boolean> {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch {
      return false;
    }
  }

  if (typeof document === "undefined") {
    return false;
  }

  try {
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}

export default function ShareButtons({ name, katakana, hiragana, script, triggerClassName }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);

  const payload = useMemo(() => {
    const kana = script === "katakana" ? katakana : hiragana;
    const scriptLabel = script === "katakana" ? "Katakana" : "Hiragana";
    const shareUrl = buildShareUrl(name, kana, script);
    const text = `I can write my name in Japanese now･:*+.\\(( °ω° ))/.:+${kana} (${scriptLabel})\n${shareUrl}`;
    return { shareUrl, text };
  }, [hiragana, katakana, name, script]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      triggerRef.current?.focus();
    };
  }, [open]);

  const handleCopyLink = async () => {
    const ok = await copyToClipboard(payload.shareUrl);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  return (
    <div>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen(true)}
        className={triggerClassName || "rounded-lg border border-[#3b82f680] bg-[#e8f0fe] px-4 py-2 text-sm font-medium text-[var(--km-ink)]"}
      >
        <span className="inline-flex items-center justify-center gap-2">
          {/* Share icon from Tabler Icons (MIT). */}
          <svg viewBox="0 0 24 24" aria-hidden="true" className="h-[17px] w-[17px]">
            <circle cx="18" cy="5" r="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <circle cx="6" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <circle cx="18" cy="19" r="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path d="M8.7 13.5l6.6 3.8M15.3 6.7L8.7 10.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          Share
        </span>
      </button>
      {open ? (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/20 px-4" onClick={() => setOpen(false)}>
          <div
            role="dialog"
            aria-modal="true"
            className="relative w-full max-w-md rounded-2xl border border-[#3b82f680] bg-white p-5 shadow-lg"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              ref={closeRef}
              type="button"
              onClick={() => setOpen(false)}
              className="absolute right-3 top-3 rounded-md border border-[#3b82f680] bg-[#e8f0fe] px-2 py-1 text-xs text-[var(--km-ink)]"
            >
              Close
            </button>

            <h3 className="mb-4 text-center text-lg font-semibold text-[var(--km-ink)]">Share result</h3>

            <div className="mx-auto grid max-w-xs grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => openShareUrl(`https://twitter.com/intent/tweet?text=${encodeURIComponent(payload.text)}`)}
                className="km-copy-button inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[#3b82f680] bg-[#eef4ff] px-4 text-sm font-medium text-[var(--km-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--km-pink)]/40"
              >
                <img src="/icons/x.svg" alt="" aria-hidden="true" className="h-4 w-4" />
                X
              </button>
              <button
                type="button"
                onClick={() => openShareUrl(`https://www.threads.net/intent/post?text=${encodeURIComponent(payload.text)}`)}
                className="km-copy-button inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[#3b82f680] bg-[#eef4ff] px-4 text-sm font-medium text-[var(--km-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--km-pink)]/40"
              >
                <img src="/icons/threads.svg" alt="" aria-hidden="true" className="h-4 w-4" />
                Threads
              </button>
              <button
                type="button"
                onClick={() => openShareUrl(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(payload.shareUrl)}`)}
                className="km-copy-button inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[#3b82f680] bg-[#eef4ff] px-4 text-sm font-medium text-[var(--km-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--km-pink)]/40"
              >
                <img src="/icons/facebook.svg" alt="" aria-hidden="true" className="h-4 w-4" />
                Facebook
              </button>
              <button
                type="button"
                onClick={() => openShareUrl(`https://wa.me/?text=${encodeURIComponent(payload.text)}`)}
                className="km-copy-button inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[#3b82f680] bg-[#eef4ff] px-4 text-sm font-medium text-[var(--km-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--km-pink)]/40"
              >
                <img src="/icons/whatsapp.svg" alt="" aria-hidden="true" className="h-4 w-4" />
                WhatsApp
              </button>
            </div>

            <div className="mt-3 flex justify-center">
              <button
                type="button"
                onClick={handleCopyLink}
                className="km-copy-button inline-flex h-10 items-center justify-center rounded-full border border-[#3b82f680] bg-[#eef4ff] px-4 text-sm font-medium text-[var(--km-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--km-pink)]/40"
              >
                Copy link
              </button>
            </div>
            {copied ? <p className="mt-2 text-center text-xs text-[var(--km-ink)]/70">Copied</p> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
