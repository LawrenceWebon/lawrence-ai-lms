import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  async rewrites() {
    const internalApiUrl = process.env.AI_LMS_API_INTERNAL_URL;
    if (!internalApiUrl) {
      return [];
    }
    return [
      {
        source: "/f001-api/:path*",
        destination: `${internalApiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
