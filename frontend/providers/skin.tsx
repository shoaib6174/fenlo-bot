"use client";

import { createContext, useContext, useState, useEffect } from "react";
import type { Skin, SkinConfig } from "@/lib/skin";
import { getSkinConfig } from "@/lib/skin";

const SkinContext = createContext<SkinConfig>(getSkinConfig("fenloai"));

export function SkinProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<SkinConfig>(getSkinConfig("fenloai"));

  useEffect(() => {
    const attr = document.documentElement.getAttribute("data-skin") as Skin | null;
    const skin: Skin = attr === "ragchat" ? "ragchat" : "fenloai";
    setConfig(getSkinConfig(skin));
  }, []);

  return (
    <SkinContext.Provider value={config}>
      {children}
    </SkinContext.Provider>
  );
}

export function useSkin(): SkinConfig {
  return useContext(SkinContext);
}
