import { NextResponse } from "next/server";

const MAX_NAME_LENGTH = 200;
const REQUEST_TIMEOUT_MS = 7000;

function backendBaseUrl(): string | null {
  const raw = process.env.NAMEKANA_API_URL;
  if (!raw) {
    return null;
  }
  return raw.replace(/\/+$/, "");
}

export async function POST(request: Request) {
  const baseUrl = backendBaseUrl();
  if (!baseUrl) {
    return NextResponse.json({ error: "Backend URL is not configured." }, { status: 500 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const name = typeof (body as { name?: unknown })?.name === "string" ? (body as { name: string }).name.trim() : "";

  if (!name) {
    return NextResponse.json({ error: "Field 'name' is required." }, { status: 400 });
  }
  if (name.length > MAX_NAME_LENGTH) {
    return NextResponse.json(
      { error: `Field 'name' must be ${MAX_NAME_LENGTH} characters or fewer.` },
      { status: 400 },
    );
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const upstream = await fetch(`${baseUrl}/transliterate?name=${encodeURIComponent(name)}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
      cache: "no-store",
    });

    const contentType = (upstream.headers.get("content-type") || "").toLowerCase();
    const raw = await upstream.text();

    if (!upstream.ok) {
      return NextResponse.json(
        {
          error: "Backend request failed.",
          status: upstream.status,
          details: raw.slice(0, 500) || null,
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
    if ((error as { name?: string }).name === "AbortError") {
      return NextResponse.json({ error: "Backend request timed out." }, { status: 502 });
    }
    return NextResponse.json({ error: "Backend request could not be completed." }, { status: 502 });
  } finally {
    clearTimeout(timeout);
  }
}
