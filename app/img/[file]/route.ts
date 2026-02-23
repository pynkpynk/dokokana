import type { NextRequest } from "next/server";
import ogp from "../../../img/DokoKana-OGP.png";
import stamp from "../../../img/DokoKana-stamp.png";

type StaticImageImport = { src: string } | string;

const WHITELIST: Record<string, StaticImageImport> = {
  "DokoKana-stamp.png": stamp,
  "DokoKana-OGP.png": ogp,
  "KanaMe-stamp.png": stamp,
  "KanaMe-OGP.png": ogp,
};

function resolveImportedSrc(value: StaticImageImport): string {
  if (typeof value === "string") {
    return value;
  }
  return value.src;
}

export async function GET(request: NextRequest, context: { params: { file: string } }) {
  const asset = WHITELIST[context.params.file];
  if (!asset) {
    return new Response("Not found", { status: 404 });
  }

  const src = resolveImportedSrc(asset);
  const assetUrl = new URL(src, request.nextUrl.origin);

  if (assetUrl.pathname.startsWith("/img/")) {
    return new Response("Invalid asset target", { status: 500 });
  }

  const upstream = await fetch(assetUrl.toString(), { cache: "force-cache" });
  if (!upstream.ok) {
    return new Response("Asset unavailable", { status: 404 });
  }

  const body = await upstream.arrayBuffer();
  const contentType = upstream.headers.get("content-type") || "application/octet-stream";

  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  });
}
