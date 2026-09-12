import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Django keeps trailing slashes on API routes. Prevent Next from redirecting
  // `/api/csrf/` to `/api/csrf` before the rewrite can run.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }];
  },
};

export default nextConfig;
