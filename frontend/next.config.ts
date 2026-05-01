import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // Turbopack configuration (Next.js 16 default)
  // Keep empty to use Turbopack defaults
  turbopack: {},

  // Rewrites to handle API proxying (optional)
  async rewrites() {
    return {
      beforeFiles: [
        // Proxy all /api requests server-side to the backend service to avoid CORS
        {
          source: '/api/:path*',
          destination: `https://${process.env.RAILWAY_SERVICE_AI_TALENT_FINDER_BACKEND_URL}/:path*`,
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
