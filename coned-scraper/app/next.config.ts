import type { NextConfig } from 'next'
import path from 'path'

const nextConfig: NextConfig = {
  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,

  images: {
    formats: ['image/avif', 'image/webp'],
  },

  experimental: {
    optimizePackageImports: ['react', 'react-dom'],
  },

  output: 'standalone',

  // IMPORTANT: tracing root should be the folder that contains node_modules at build time
  // In Docker, this will be /app (the WORKDIR), so we use process.cwd() or relative path
  // This ensures the build works both locally and in Docker
  outputFileTracingRoot: process.env.DOCKER_BUILD ? '/app' : path.join(__dirname),

  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL || 'http://api:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${apiBaseUrl}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
