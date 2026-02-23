"use client";

import ShareButtons from "../components/ShareButtons";
import Image from "next/image";
import { FormEvent, useEffect, useState, type CSSProperties } from "react";
import splashImg from "../img/japanotes-character-hi-five-final.png";

type TransliterationResult = {
  input: string;
  katakana: string;
  hiragana: string;
  source?: string | null;
  warning?: string | null;
};

const MAX_NAME_LENGTH = 200;
const SPLASH_TOTAL_MS = 5000;

const showDebug = process.env.NODE_ENV !== "production";
const headerCardChrome = {
  "--km-card-border": "1px solid #84c0c7",
  "--km-card-shadow": "0 12px 28px rgba(55, 56, 56, 0.12)",
} as CSSProperties;

function kataToHira(text: string): string {
  let out = "";
  for (const ch of text) {
    const code = ch.charCodeAt(0);
    if (code >= 0x30a1 && code <= 0x30f6) {
      out += String.fromCharCode(code - 0x60);
    } else {
      out += ch;
    }
  }
  return out;
}

function hiraToKata(text: string): string {
  let out = "";
  for (const ch of text) {
    const code = ch.charCodeAt(0);
    if (code >= 0x3041 && code <= 0x3096) {
      out += String.fromCharCode(code + 0x60);
    } else {
      out += ch;
    }
  }
  return out;
}

export default function HomePage() {
  const [singleName, setSingleName] = useState("");
  const [singleLoading, setSingleLoading] = useState(false);
  const [singleError, setSingleError] = useState<string | null>(null);
  const [singleResult, setSingleResult] = useState<TransliterationResult | null>(null);

  const [copyStatus, setCopyStatus] = useState<{ label: "Katakana" | "Hiragana"; ok: boolean } | null>(null);
  const [currentScript, setCurrentScript] = useState<"katakana" | "hiragana">("katakana");
  const [showSplash, setShowSplash] = useState(true);

  const setCopyMessage = (label: "Katakana" | "Hiragana", ok: boolean) => {
    setCopyStatus({ label, ok });
    setTimeout(() => setCopyStatus(null), 1500);
  };

  const copyText = async (value: string, label: "Katakana" | "Hiragana") => {
    if (!value) {
      setCopyMessage(label, false);
      return;
    }
    try {
      await navigator.clipboard.writeText(value);
      setCopyMessage(label, true);
    } catch {
      setCopyMessage(label, false);
    }
  };

  const handleSingleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSingleError(null);
    setSingleResult(null);

    const trimmed = singleName.trim();
    if (!trimmed) {
      setSingleError("Please enter a name.");
      return;
    }
    if (trimmed.length > MAX_NAME_LENGTH) {
      setSingleError(`Please keep names under ${MAX_NAME_LENGTH} characters.`);
      return;
    }

    setSingleLoading(true);
    try {
      const response = await fetch("/api/transliterate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: trimmed }),
      });

      const payload = (await response.json().catch(() => null)) as TransliterationResult | { error?: string } | null;

      if (!response.ok) {
        setSingleError(payload && "error" in payload && payload.error ? payload.error : "Conversion failed.");
        return;
      }

      if (!payload || !("katakana" in payload) || !("hiragana" in payload)) {
        setSingleError("Unexpected response format.");
        return;
      }

      setSingleResult(payload as TransliterationResult);
      setCurrentScript("katakana");
    } catch {
      setSingleError("Network error. Please try again.");
    } finally {
      setSingleLoading(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const name = (params.get("name") || "").trim();
    const kana = (params.get("kana") || "").trim();
    const script = (params.get("script") || "").trim().toLowerCase();

    if (name && kana && (script === "katakana" || script === "hiragana")) {
      const katakana = script === "katakana" ? kana : hiraToKata(kana);
      const hiragana = script === "hiragana" ? kana : kataToHira(kana);
      setCurrentScript(script);
      setSingleName(name);
      setSingleResult({
        input: name,
        katakana,
        hiragana,
        source: null,
        warning: null,
      });
    }

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShowSplash(false);
      return;
    }
    const timer = window.setTimeout(() => setShowSplash(false), SPLASH_TOTAL_MS);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <>
      {showSplash ? (
        <div className="km-splash-overlay fixed inset-0 z-50 flex flex-col items-center justify-center bg-white">
          <Image src={splashImg} alt="JapaNotes mascot" width={280} height={280} priority className="km-splash-image h-auto w-[220px] max-w-[62vw]" />
          <p className="km-splash-text mt-4 text-3xl font-semibold text-[var(--km-ink)]">JapaNotes</p>
        </div>
      ) : null}

      <main className="mx-auto min-h-screen w-full max-w-3xl space-y-6 overflow-visible px-4 py-8 sm:px-6 lg:px-8">
        <section className="km-card rounded-3xl bg-white/85 p-6 sm:p-7" style={headerCardChrome}>
          <div className="space-y-3 text-center">
            <h1 className="text-3xl font-bold tracking-[0.08em] text-[var(--km-ink)]">DokoKana?</h1>
            <p className="text-sm text-[var(--km-ink)]/65">
              by{" "}
              <a href="https://japanotes.carrd.co/" target="_blank" rel="noreferrer noopener" className="underline">
                JapaNotes
              </a>
            </p>
            <p className="text-[var(--km-ink)]/85">Turn your country name into Japanese Katakana and Hiragana.</p>
          </div>

          <div className="my-5 h-px bg-[var(--km-border)]/70" />

          <form onSubmit={handleSingleSubmit} className="mx-auto max-w-xl space-y-3">
            <label htmlFor="single-name" className="block text-sm font-medium text-[var(--km-ink)]/85">
              Enter your country
            </label>
            <input
              id="single-name"
              type="text"
              value={singleName}
              maxLength={MAX_NAME_LENGTH}
              onChange={(event) => setSingleName(event.target.value)}
              className="w-full rounded-xl border border-[#3b82f680] bg-white px-3 py-2 outline-none ring-2 ring-[#3b82f680]/15 transition focus:ring-[#3b82f680]/30"
              placeholder="e.g. Japan"
            />
            <div className="flex justify-center pt-1">
              <button
                type="submit"
                disabled={singleLoading}
                className="km-button-primary rounded-full px-5 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
              >
                {singleLoading ? "Converting..." : "Convert to Kana"}
              </button>
            </div>
          </form>

          <p className="mx-auto mt-3 max-w-xl text-center text-xs text-[var(--km-ink)]/65">
            First request may take longer (up to about 1 minute) while the server wakes up.
          </p>

          {singleError ? <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{singleError}</p> : null}
        </section>

        {singleResult ? (
          <section className="km-reveal km-card rounded-3xl bg-white/85 p-6 sm:p-7" style={headerCardChrome}>
            <div className="relative rounded-[2rem] bg-[#fffdfb] p-6 shadow-[0_16px_34px_rgba(55,56,56,0.12)] sm:p-8">
              <div aria-hidden="true" className="pointer-events-none absolute inset-3 rounded-[1.5rem] border border-[var(--km-border)]/55" />
              <Image
                src="/img/DokoKana-stamp.png"
                alt="DokoKana stamp"
                width={136}
                height={136}
                className="pointer-events-none absolute -right-7 -top-8 z-20 h-28 w-28 object-contain opacity-95 drop-shadow-[0_6px_12px_rgba(55,56,56,0.16)] sm:-right-5 sm:-top-6 sm:h-36 sm:w-36"
              />

              <div className="relative z-10 mb-3 text-center text-xs font-semibold tracking-[0.14em] text-[var(--km-ink)]/55">I'm from</div>

              <div className="relative z-10 rounded-[1.7rem] bg-[#fffdfb] px-5 py-6 shadow-none sm:px-8 sm:py-9">
                <p className="km-kana-font text-center text-3xl font-semibold leading-tight text-[var(--km-ink)] sm:text-[2.6rem]">{singleResult.katakana || "-"}</p>
                <div className="mx-auto mt-4 h-px w-24 bg-[var(--km-pink)]/30" />
                <p className="km-kana-font mt-4 text-center text-[1.3rem] leading-tight text-[var(--km-ink)]/82 sm:text-[1.7rem]">{singleResult.hiragana || "-"}</p>
              </div>
              <div className="relative z-10 mt-4 space-y-3 rounded-2xl bg-[#fffdfb] px-3 py-3">
                <div className="flex flex-wrap items-center justify-center gap-2">
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => copyText(singleResult.katakana, "Katakana")}
                      className="km-copy-button inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[#3b82f680] bg-[#eef4ff] px-4 text-sm font-medium text-[var(--km-ink)] transition hover:shadow-[0_4px_10px_rgba(59,130,246,0.18)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--km-pink)]/40"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
                        <path
                          d="M9 4h6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm-1 4H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h6m-1-16h2"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      Copy Katakana
                    </button>
                    {copyStatus && copyStatus.label === "Katakana" ? (
                      <span
                        className={`pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 rounded-full px-2 py-0.5 text-xs whitespace-nowrap ${
                          copyStatus.ok ? "bg-[#e8f0fe] text-[var(--km-ink)]" : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        {copyStatus.ok ? "Copied!" : "Try again"}
                      </span>
                    ) : null}
                  </div>

                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => copyText(singleResult.hiragana, "Hiragana")}
                      className="km-copy-button inline-flex h-10 items-center justify-center gap-2 rounded-full border border-[#3b82f680] bg-[#eef4ff] px-4 text-sm font-medium text-[var(--km-ink)] transition hover:shadow-[0_4px_10px_rgba(59,130,246,0.18)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--km-pink)]/40"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4">
                        <path
                          d="M9 4h6a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm-1 4H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h6m-1-16h2"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      Copy Hiragana
                    </button>
                    {copyStatus && copyStatus.label === "Hiragana" ? (
                      <span
                        className={`pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 rounded-full px-2 py-0.5 text-xs whitespace-nowrap ${
                          copyStatus.ok ? "bg-[#e8f0fe] text-[var(--km-ink)]" : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        {copyStatus.ok ? "Copied!" : "Try again"}
                      </span>
                    ) : null}
                  </div>
                </div>

              </div>
            </div>

            {showDebug && singleResult.source ? (
              <p className="mt-3 text-sm text-[var(--km-ink)]/70">Source used: {singleResult.source === "model" ? "e2k" : singleResult.source}</p>
            ) : null}

            {showDebug && singleResult.warning ? (
              <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">Note: {singleResult.warning}</p>
            ) : null}

            <div className="mt-3 flex justify-center">
              <ShareButtons
                name={singleResult.input || singleName.trim()}
                katakana={singleResult.katakana}
                hiragana={singleResult.hiragana}
                script={currentScript}
                triggerClassName="inline-flex items-center justify-center gap-2 rounded-full !border-[1.5px] !border-[rgba(239,177,203,0.95)] !bg-[rgba(239,177,203,0.22)] px-5 py-2.5 text-sm font-semibold !text-[var(--km-ink)] transition-[transform,filter,box-shadow,background-color,border-color] duration-150 hover:!bg-white hover:brightness-[0.98] hover:shadow-[0_6px_14px_rgba(239,177,203,0.25)] active:translate-y-[1px] active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--km-pink)]/45"
              />
            </div>

            <p className="mt-4 text-xs text-[var(--km-ink)]/55 sm:text-center">Kana is a best-effort approximation; pronunciation may vary.</p>
          </section>
        ) : null}

        <footer className="pb-3 pt-4 text-center text-xs text-[var(--km-ink)]/55">
          <a href="https://japanotes.carrd.co/" target="_blank" rel="noreferrer noopener" className="underline">
            JapaNotes
          </a>
        </footer>
      </main>
    </>
  );
}
