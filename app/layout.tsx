import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'ConEd Scraper',
  description: 'ConEd account scraper with TOTP authentication',
  keywords: ['ConEd', 'scraper', 'utility', 'billing'],
  authors: [{ name: 'ConEd Scraper' }],
  creator: 'ConEd Scraper',
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: 'ConEd Scraper',
    description: 'ConEd account scraper with TOTP authentication',
    type: 'website',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  themeColor: '#ffffff',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
