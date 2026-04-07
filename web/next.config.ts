import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  // Proxy API calls to the FastAPI backend
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/health",     destination: `${api}/health` },
      { source: "/v1/:path*",  destination: `${api}/v1/:path*` },
    ];
  },
};

export default nextConfig;
