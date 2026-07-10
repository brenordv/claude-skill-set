# Next.js Deployment & next.config.js

Full examples referenced from SKILL.md §18 (Deployment) and §20 (next.config.js). The Vercel workflow and caching/revalidation rules stay in the skill body.

## Docker

```dockerfile
FROM node:20-alpine AS base
RUN corepack enable

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

Enable standalone output in `next.config.js`:

```js
module.exports = { output: 'standalone' }
```

## Quick Reference: next.config.js

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Optimize large library imports
  experimental: {
    optimizePackageImports: ['lucide-react', '@mui/material'],
  },
  // Standalone output for Docker
  output: 'standalone',
  // Image optimization
  images: {
    remotePatterns: [{ protocol: 'https', hostname: 'cdn.example.com' }],
  },
  // Security headers
  async headers() {
    return [{
      source: '/(.*)',
      headers: [
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      ],
    }]
  },
}

module.exports = nextConfig
```
