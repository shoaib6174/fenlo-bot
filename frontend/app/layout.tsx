import type { Metadata } from "next";
import { headers } from "next/headers";
import { JetBrains_Mono, DM_Sans, Instrument_Serif } from "next/font/google";
import "./globals.css";
import { Providers } from "@/providers";
import { getSkinFromHost } from "@/lib/skin";

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const headersList = await headers();
  const host = headersList.get("host") || "";
  const skin = getSkinFromHost(host);

  if (skin === "ragchat") {
    return {
      title: {
        default: "RAGChat — AI That Knows Your Business",
        template: "%s | RAGChat",
      },
      description:
        "Upload your documents, get an AI chatbot that answers with citations. Real-time analytics, knowledge gap detection, and embeddable widget.",
      metadataBase: new URL("https://rag.fenloai.com"),
      openGraph: {
        title: "RAGChat — AI That Knows Your Business",
        description:
          "Document-powered AI chatbot with citations, analytics, and embeddable widget. Production-ready RAG solution.",
        url: "https://rag.fenloai.com",
        siteName: "RAGChat",
        type: "website",
        locale: "en_US",
      },
      twitter: {
        card: "summary_large_image",
        title: "RAGChat — AI That Knows Your Business",
        description:
          "Upload docs, get an AI chatbot with citations. Analytics included.",
      },
      robots: { index: true, follow: true },
      alternates: { canonical: "https://rag.fenloai.com" },
    };
  }

  return {
    title: {
      default: "Fenlo AI — Intelligent Automation Solutions",
      template: "%s | Fenlo AI",
    },
    description:
      "AI-powered chatbots, voice agents, and multi-channel automation. RAG-powered knowledge bases, real-time analytics, and seamless deployment.",
    metadataBase: new URL("https://bot.fenloai.com"),
    openGraph: {
      title: "Fenlo AI — Intelligent Automation Solutions",
      description:
        "Custom AI chatbots and voice agents with RAG, multi-channel deployment, and enterprise-grade analytics.",
      url: "https://bot.fenloai.com",
      siteName: "Fenlo AI",
      type: "website",
      locale: "en_US",
    },
    twitter: {
      card: "summary_large_image",
      title: "Fenlo AI — Intelligent Automation Solutions",
      description:
        "AI-powered chatbots, voice agents, and multi-channel automation.",
    },
    robots: { index: true, follow: true },
    alternates: { canonical: "https://bot.fenloai.com" },
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const headersList = await headers();
  const host = headersList.get("host") || "";
  const skin = getSkinFromHost(host);

  return (
    <html
      lang="en"
      suppressHydrationWarning
      data-skin={skin}
      className={`${jetbrainsMono.variable} ${dmSans.variable} ${instrumentSerif.variable}`}
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('botforge_theme');
                  if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches) || theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                    document.documentElement.classList.add('dark');
                  }
                } catch(e) {}
              })();
            `,
          }}
        />
      </head>
      <body className={dmSans.className}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
