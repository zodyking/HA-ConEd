import type { NextConfig } from 'next'
import path from 'path'

const isAddonBuild = process.env.DOCKER_BUILD === 'true'

const nextConfig: NextConfig = {
  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,
  trailingSlash: true,

  images: {
    formats: ['image/avif', 'image/webp'],
  },

  experimental: {
    optimizePackageImports: ['react', 'react-dom'],
  },

  output: 'standalone',

  // For addon: assetPrefix is replaced at startup via sed with INGRESS_PATH (see web/run)
  // Build with empty so sed can find and replace in server.js
  ...(isAddonBuild && { assetPrefix: '' }),

  // IMPORTANT: tracing root should be the folder that contains node_modules at build time
  // In Docker, this will be /app (the WORKDIR), so we use process.cwd() or relative path
  // This ensures the build works both locally and in Docker
  outputFileTracingRoot: process.env.DOCKER_BUILD ? '/app' : path.join(__dirname),

  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL || 'http://127.0.0.1:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
