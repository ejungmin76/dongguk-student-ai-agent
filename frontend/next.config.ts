import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Django keeps trailing slashes on API routes. Prevent Next from redirecting
  // `/api/csrf/` to `/api/csrf` before the rewrite can run.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const django = "http://127.0.0.1:8000";
    return [
      { source: "/api/csrf/", destination: `${django}/api/csrf/` },
      { source: "/api/chat/", destination: `${django}/api/chat/` },
      { source: "/api/chat/stream/", destination: `${django}/api/chat/stream/` },
      {
        source: "/api/chat/streams/:runId/events/",
        destination: `${django}/api/chat/streams/:runId/events/`,
      },
      {
        source: "/api/chat/streams/:runId/cancel/",
        destination: `${django}/api/chat/streams/:runId/cancel/`,
      },
    ];
  },
};

export default nextConfig;
