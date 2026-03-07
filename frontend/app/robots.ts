import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/dashboard/", "/chat/", "/kb/", "/settings/", "/voice/", "/analytics/", "/channels/", "/inbox/", "/debug/", "/onboarding/", "/admin/"],
      },
    ],
    sitemap: "https://bot.fenloai.com/sitemap.xml",
  };
}
