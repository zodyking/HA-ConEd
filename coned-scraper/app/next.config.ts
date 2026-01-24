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
  // In our Dockerfile, node_modules is at /app (which is built from coned-scraper/app)
  // This maps to the "app" folder, so tracing root should be __dirname (not ../../)
  outputFileTracingRoot: path.join(__dirname),

  async rewrites() {
    const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${apiBaseUrl}/:path*`,
      },
    ]
  },
}

export default nextConfig
