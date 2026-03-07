import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  eslint: {
    // ESLint runs during builds to catch errors before deployment
    ignoreDuringBuilds: false,
  },
  // NEXT_PUBLIC_API_URL comes from .env.local (dev) or is empty (production, same-origin).
  // Do NOT set a default here — it overrides .env.* files.
};

export default nextConfig;
