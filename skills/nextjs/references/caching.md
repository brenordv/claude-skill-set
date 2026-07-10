# Next.js Caching: Niche Patterns

Full examples referenced from SKILL.md §6. The cache-layers table and revalidation patterns stay in the skill body.

## Cross-Request LRU Caching

```tsx
import { LRUCache } from 'lru-cache'

const cache = new LRUCache<string, any>({ max: 1000, ttl: 5 * 60 * 1000 })

export async function getUser(id: string) {
  const cached = cache.get(id)
  if (cached) return cached
  const user = await db.user.findUnique({ where: { id } })
  cache.set(id, user)
  return user
}
```

## Non-Blocking Post-Response Work

```tsx
import { after } from 'next/server'

export async function POST(request: Request) {
  await updateDatabase(request)

  after(async () => {
    // Runs after response is sent: analytics, logging, cache invalidation
    await logUserAction({ userAgent: (await headers()).get('user-agent') })
  })

  return Response.json({ status: 'success' })
}
```
