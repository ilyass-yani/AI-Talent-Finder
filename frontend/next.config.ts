import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Rewrites to proxy /api/* to the FastAPI backend server-side.
  // In both development and production, we need to rewrite to the backend.
  async rewrites() {
    // In production, use Railway backend service URL
    if (process.env.NODE_ENV === 'production') {
      return {
        beforeFiles: [
          {
            source: '/api/:path*',
            destination: 'https://ai-talent-finder-backend-production.up.railway.app/api/:path*',
          },
        ],
      };
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
