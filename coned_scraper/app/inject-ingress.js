#!/usr/bin/env node
/**
 * Injects INGRESS_PATH into Next.js standalone build (server.js, required-server-files.json)
 * so assetPrefix points to the correct ingress path for HA addon panels.
 */
const fs = require('fs')
const path = require('path')

const ingressPath = (process.env.INGRESS_PATH || '').trim()
if (!ingressPath) process.exit(0)

const dir = __dirname
const escaped = ingressPath.replace(/\\/g, '\\\\').replace(/"/g, '\\"')

for (const file of ['server.js', '.next/required-server-files.json']) {
  const fp = path.join(dir, file)
  if (!fs.existsSync(fp)) continue
  let content = fs.readFileSync(fp, 'utf8')
  // Match "assetPrefix":"" or "assetPrefix": "" (Next.js serialized config)
  const before = content
  content = content.replace(/"assetPrefix"\s*:\s*""/g, `"assetPrefix":"${ingressPath.replace(/"/g, '\\"')}"`)
  if (content !== before) {
    fs.writeFileSync(fp, content)
    console.log(`Injected assetPrefix into ${file}`)
  }
}
