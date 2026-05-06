import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // Turbopack configuration (Next.js 16 default)
  // Keep empty to use Turbopack defaults
  turbopack: {},

  // Rewrites to proxy /api/* to the FastAPI backend server-side (avoids CORS).
  // NEXT_PUBLIC_API_URL must be a full http(s) URL; if it is a path like "/api"
  // we fall back to the known production backend URL.
  async rewrites() {
    const rawUrl = process.env.NEXT_PUBLIC_API_URL || '';
    const defaultBackendUrl = process.env.NODE_ENV === 'production'
      ? 'https://ai-talent-finder-backend-production.up.railway.app'
      : 'http://127.0.0.1:8000';
    const backendUrl = rawUrl.startsWith('http')
      ? rawUrl.replace(/\/$/, '')
      : defaultBackendUrl;
    return {
      beforeFiles: [
        {
          source: '/api/:path*',
          destination: `${backendUrl}/api/:path*`,
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
