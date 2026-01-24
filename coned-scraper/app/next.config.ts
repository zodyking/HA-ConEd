import type { NextConfig } from 'next'
import path from 'path'

const nextConfig: NextConfig = {
  // Production optimizations
  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,
  
  // Image optimization
  images: {
    formats: ['image/avif', 'image/webp'],
  },
  
  // Performance optimizations
  experimental: {
    optimizePackageImports: ['react', 'react-dom'],
  },
  
  // Output configuration
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname, '../../'),
  
  // API rewrites for Docker/Dokploy deployment
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
