import { NextResponse } from "next/server";

const MAX_NAME_LENGTH = 200;
const DEFAULT_REQUEST_TIMEOUT_MS = 35000;
const DEFAULT_RETRY_ATTEMPTS = 2;
const DEFAULT_RETRY_BACKOFF_MS = 2500;
const RETRYABLE_STATUS_CODES = new Set([408, 425, 429]);
const BACKEND_UNKNOWN_COUNTRY_DETAIL = "Please enter a valid country name.";
const UNKNOWN_COUNTRY_ERROR_MESSAGE = "Please enter a valid country name.";

function readPositiveIntEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return fallback;
  }
  return parsed;
}

function readPositiveIntEnvAny(names: string[], fallback: number): number {
  for (const name of names) {
    const raw = process.env[name];
    if (!raw) {
      continue;
    }
    const parsed = Number.parseInt(raw, 10);
    if (!Number.isFinite(parsed) || parsed < 0) {
      continue;
    }
    return parsed;
  }
  return fallback;
}

function isRetryableStatus(status: number): boolean {
  return RETRYABLE_STATUS_CODES.has(status) || status >= 500;
}

function sleep(ms: number): Promise<void> {
  if (ms <= 0) {
    return Promise.resolve();
  }
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function backendBaseUrl(): string | null {
  const raw = process.env.DOKOKANA_API_URL || process.env.NAMEKANA_API_URL;
  if (!raw) {
    return null;
  }
  return raw.replace(/\/+$/, "");
}

function isUnknownCountryBackendError(status: number, raw: string): boolean {
  if (status !== 400) {
    return false;
  }
  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };
    return parsed.detail === BACKEND_UNKNOWN_COUNTRY_DETAIL;
  } catch {
    return false;
  }
}

async function proxyTransliterate(name: string) {
  const baseUrl = backendBaseUrl();
  if (!baseUrl) {
    return NextResponse.json({ error: "Backend URL is not configured." }, { status: 500 });
  }

  const requestTimeoutMs = readPositiveIntEnvAny(
    ["DOKOKANA_PROXY_TIMEOUT_MS", "NAMEKANA_PROXY_TIMEOUT_MS"],
    DEFAULT_REQUEST_TIMEOUT_MS,
  );
  const retryAttempts = readPositiveIntEnvAny(
    ["DOKOKANA_PROXY_RETRY_ATTEMPTS", "NAMEKANA_PROXY_RETRY_ATTEMPTS"],
    DEFAULT_RETRY_ATTEMPTS,
  );
  const retryBackoffMs = readPositiveIntEnvAny(
    ["DOKOKANA_PROXY_RETRY_BACKOFF_MS", "NAMEKANA_PROXY_RETRY_BACKOFF_MS"],
    DEFAULT_RETRY_BACKOFF_MS,
  );

  const maxAttempts = Math.max(1, retryAttempts + 1);
  const targetUrl = `${baseUrl}/transliterate?name=${encodeURIComponent(name)}`;

  let lastRetryableResponse: { status: number; details: string } | null = null;
  let hadRetryableNetworkFailure = false;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), requestTimeoutMs);

    try {
      const upstream = await fetch(targetUrl, {
        method: "GET",
        headers: { Accept: "application/json" },
        signal: controller.signal,
        cache: "no-store",
      });

      const contentType = (upstream.headers.get("content-type") || "").toLowerCase();
      const raw = await upstream.text();

      if (!upstream.ok) {
        const details = raw.slice(0, 500) || "";
        if (isRetryableStatus(upstream.status) && attempt < maxAttempts) {
          lastRetryableResponse = { status: upstream.status, details };
          await sleep(retryBackoffMs * attempt);
          continue;
        }
        if (isUnknownCountryBackendError(upstream.status, raw)) {
          return NextResponse.json({ error: UNKNOWN_COUNTRY_ERROR_MESSAGE }, { status: 400 });
        }
        return NextResponse.json(
          {
            error: "Backend request failed.",
            status: upstream.status,
            details: details || null,
          },
          { status: 502 },
        );
      }

      if (!contentType.includes("json")) {
        return NextResponse.json({ error: "Backend returned non-JSON success response." }, { status: 502 });
      }

      try {
        return NextResponse.json(JSON.parse(raw));
      } catch {
        return NextResponse.json({ error: "Backend returned invalid JSON." }, { status: 502 });
      }
    } catch (error) {
      const isAbort = (error as { name?: string }).name === "AbortError";
      if (attempt < maxAttempts) {
        hadRetryableNetworkFailure = true;
        await sleep(retryBackoffMs * attempt);
        continue;
      }
      if (isAbort) {
        return NextResponse.json({ error: "Backend request timed out." }, { status: 502 });
      }
      return NextResponse.json({ error: "Backend request could not be completed." }, { status: 502 });
    } finally {
      clearTimeout(timeout);
    }
  }

  if (lastRetryableResponse) {
    return NextResponse.json(
      {
        error: "Backend request failed after retries.",
        status: lastRetryableResponse.status,
        details: lastRetryableResponse.details || null,
      },
      { status: 502 },
    );
  }
  if (hadRetryableNetworkFailure) {
    return NextResponse.json({ error: "Backend request could not be completed after retries." }, { status: 502 });
  }
  return NextResponse.json({ error: "Backend request could not be completed." }, { status: 502 });
}

function parseAndValidateName(nameRaw: string, missingMessage: string) {
  const name = nameRaw.trim();
  if (!name) {
    return { ok: false as const, response: NextResponse.json({ error: missingMessage }, { status: 400 }) };
  }
  if (name.length > MAX_NAME_LENGTH) {
    return {
      ok: false as const,
      response: NextResponse.json(
        { error: `Field 'name' must be ${MAX_NAME_LENGTH} characters or fewer.` },
        { status: 400 },
      ),
    };
  }
  return { ok: true as const, name };
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const raw = url.searchParams.get("name") ?? "";
  const parsed = parseAndValidateName(raw, "Query param 'name' is required.");
  if (!parsed.ok) {
    return parsed.response;
  }
  return proxyTransliterate(parsed.name);
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const raw = typeof (body as { name?: unknown })?.name === "string" ? (body as { name: string }).name : "";
  const parsed = parseAndValidateName(raw, "Field 'name' is required.");
  if (!parsed.ok) {
    return parsed.response;
  }
  return proxyTransliterate(parsed.name);
}
