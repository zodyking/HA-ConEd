#!/usr/bin/env node
/**
 * Wrapper for Next.js standalone when running under Home Assistant ingress.
 * Injects <base href="INGRESS_PATH/"> into HTML so relative asset/API URLs resolve correctly.
 * Run with: INGRESS_PATH=/api/hassio_ingress/XXX node server-ingress.js
 * Falls back to direct server.js if INGRESS_PATH is empty (e.g. direct port access).
 */
const { spawn } = require('child_process')
const http = require('http')

const PORT = parseInt(process.env.PORT || '3000', 10)
const NEXT_PORT = PORT + 1
const INGRESS_PATH = (process.env.INGRESS_PATH || '').replace(/\/$/, '')

if (!INGRESS_PATH) {
  // No ingress path: run Next.js directly
  process.env.PORT = String(PORT)
  require('./server.js')
  process.exit(0)
}

const BASE_TAG = `<base href="${INGRESS_PATH}/">`

function forward(req, res) {
  const opts = {
    hostname: '127.0.0.1',
    port: NEXT_PORT,
    path: req.url,
    method: req.method,
    headers: req.headers,
  }
  const proxy = http.request(opts, (proxyRes) => {
    const contentType = proxyRes.headers['content-type'] || ''
    if (contentType.includes('text/html')) {
      const chunks = []
      proxyRes.on('data', (c) => chunks.push(c))
      proxyRes.on('end', () => {
        let body = Buffer.concat(chunks).toString('utf8')
        if (body.includes('<head>') && !body.includes('<base')) {
          body = body.replace('<head>', `<head>${BASE_TAG}`)
        } else if (/<head\s/.test(body) && !body.includes('<base')) {
          body = body.replace(/<head\s/, `<head>${BASE_TAG}<head `)
        }
        const h = { ...proxyRes.headers }
        delete h['content-length']
        res.writeHead(proxyRes.statusCode, h)
        res.end(body)
      })
    } else {
      res.writeHead(proxyRes.statusCode, proxyRes.headers)
      proxyRes.pipe(res)
    }
  })
  proxy.on('error', (err) => {
    console.error('Proxy error:', err)
    res.writeHead(502, { 'Content-Type': 'text/plain' })
    res.end('Bad Gateway')
  })
  req.pipe(proxy)
}

const server = http.createServer(forward)
server.listen(PORT, process.env.HOSTNAME || '0.0.0.0', () => {
  console.log(`Ingress proxy on port ${PORT}, base path: ${INGRESS_PATH}`)
})

const next = spawn('node', ['server.js'], {
  cwd: __dirname,
  env: { ...process.env, PORT: String(NEXT_PORT) },
  stdio: 'inherit',
})
next.on('exit', (code) => process.exit(code || 0))
