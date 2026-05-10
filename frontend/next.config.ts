import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Turbopack configuration (Next.js 16 default)
  // Keep empty to use Turbopack defaults
  turbopack: {},

  // Rewrites to proxy /api/* to the FastAPI backend server-side (only in development).
  // In production, relative paths are used and will automatically respect the page's HTTPS protocol.
  async rewrites() {
    // In production, don't rewrite - let relative paths work with HTTPS (same-origin)
    if (process.env.NODE_ENV === 'production') {
      return { beforeFiles: [] };
    }

    // In development, proxy to local backend
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: 'http://127.0.0.1:8000/api/:path*',
        },
      ],
    };
  },

  // Headers for security and CORS
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
        ],
      },
    ];
  },

  // Image optimization - updated to remotePatterns
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'http',
        hostname: 'api.example.com',
      },
    ],
  },
};

export default nextConfig;
