export type Skin = "fenloai" | "ragchat";

export interface SkinConfig {
  skin: Skin;
  brandName: string;
  tagline: string;
  accentColor: string;
  isFenloai: boolean;
  isRagchat: boolean;
}

const SKIN_CONFIGS: Record<Skin, Omit<SkinConfig, "skin" | "isFenloai" | "isRagchat">> = {
  fenloai: {
    brandName: "Fenlo AI",
    tagline: "Intelligent Automation",
    accentColor: "#5d6e34",
  },
  ragchat: {
    brandName: "RAGChat",
    tagline: "AI That Knows Your Business",
    accentColor: "#0ea5e9",
  },
};

/** Nav items to show per skin (null = show all) */
export const SKIN_NAV_ITEMS: Record<Skin, string[] | null> = {
  fenloai: null,  // show all
  ragchat: ["Dashboard", "Chat", "Knowledge Base", "Analytics", "Why RAGChat", "Settings"],
};

/**
 * Detect skin from hostname.
 * Precedence: NEXT_PUBLIC_FORCE_SKIN env var > hostname detection.
 */
export function getSkinFromHost(host: string): Skin {
  const forced = process.env.NEXT_PUBLIC_FORCE_SKIN;
  if (forced === "fenloai" || forced === "ragchat") return forced;

  const hostname = host.split(":")[0].toLowerCase();

  // RAGChat domain
  if (hostname === "rag.fenloai.com") return "ragchat";
  if (hostname.startsWith("ragchat.")) return "ragchat";

  // Everything else: fenloai (covers bot.fenloai.com, localhost, unknown hosts)
  return "fenloai";
}

export function getSkinConfig(skin: Skin): SkinConfig {
  return {
    skin,
    isFenloai: skin === "fenloai",
    isRagchat: skin === "ragchat",
    ...SKIN_CONFIGS[skin],
  };
}
