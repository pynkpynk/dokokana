import type { Metadata } from "next";
import { headers } from "next/headers";
import Script from "next/script";
import type { ReactNode } from "react";
import "./globals.css";

const appName = process.env.NEXT_PUBLIC_APP_NAME || "KanaMe";
const description = `${appName} helps convert Western names into Japanese Kana.`;

function resolveMetadataBase(): URL {
  const fromEnv = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  if (fromEnv) {
    try {
      return new URL(fromEnv);
    } catch {
      return new URL(`https://${fromEnv}`);
    }
  }

  const h = headers();
  const host = h.get("x-forwarded-host") || h.get("host");
  const proto = h.get("x-forwarded-proto") || "https";
  if (host) {
    return new URL(`${proto}://${host}`);
  }
  return new URL("http://localhost:3000");
}

export async function generateMetadata(): Promise<Metadata> {
  const metadataBase = resolveMetadataBase();
  return {
    metadataBase,
    title: appName,
    description,
    openGraph: {
      title: appName,
      description,
      url: "/",
      siteName: appName,
      type: "website",
      images: [
        {
          url: "/img/KanaMe-OGP.png",
          width: 1200,
          height: 630,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: appName,
      description,
      images: ["/img/KanaMe-OGP.png"],
    },
  };
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Script
          id="adobe-fonts-kit"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(d) {
  var config = {
    kitId: 'ahk6hmo',
    scriptTimeout: 3000,
    async: true
  },
  h=d.documentElement,t=setTimeout(function(){h.className=h.className.replace(/\\bwf-loading\\b/g,"")+" wf-inactive";},config.scriptTimeout),tk=d.createElement("script"),f=false,s=d.getElementsByTagName("script")[0],a;h.className+=" wf-loading";tk.src='https://use.typekit.net/'+config.kitId+'.js';tk.async=true;tk.onload=tk.onreadystatechange=function(){a=this.readyState;if(f||a&&a!="complete"&&a!="loaded")return;f=true;clearTimeout(t);try{Typekit.load(config)}catch(e){}};s.parentNode.insertBefore(tk,s)
})(document);`,
          }}
        />
        {children}
      </body>
    </html>
  );
}
