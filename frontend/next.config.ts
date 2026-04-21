import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Build a self-contained `.next/standalone` server for the Docker image.
  output: 'standalone',

  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },

  // Pin the workspace root so Next.js doesn't pick up the parent-directory lockfile.
  turbopack: {
    root: __dirname,
  },

  // Rewrites to handle API proxying (optional)
  async rewrites() {
    return {
      beforeFiles: [
        // Allow direct access to API without CORS issues if needed
        // {
        //   source: '/api/:path*',
        //   destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/:path*`,
        // },
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
