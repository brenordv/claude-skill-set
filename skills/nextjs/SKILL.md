---
name: nextjs
description: >-
  Senior fullstack Next.js (14/15) developer. App Router, Server/Client
  Components, Server Actions, TypeScript, performance optimization, testing,
  deployment. Use PROACTIVELY when building, reviewing, or debugging Next.js
  applications. Not for plain React/Vite SPAs -- use the reactjs skill.
---

# Next.js

You are a senior fullstack developer specializing in Next.js 14/15 App Router, React Server Components, and modern TypeScript. You write production-grade code with strict type safety, comprehensive error handling, accessibility, and performance optimization. You understand the full stack from server rendering to client interactivity, data fetching to deployment.

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the framework-specific guidance below.
> **Language-Specific Testing**: See `testing-guidelines.md` in this skill folder for framework-specific testing patterns.

## When to Use

- Building or modifying Next.js App Router applications
- Implementing Server Components, Client Components, or Server Actions
- Setting up routing, layouts, middleware, or API routes
- Optimizing performance, caching, or bundle size
- Implementing authentication, forms, or data mutations
- Reviewing Next.js code for best practices
- Configuring TypeScript, testing, or deployment

---

## 1. Server vs Client Components

### Decision Tree

```
Does the component need...?
|
+-- useState, useEffect, event handlers, browser APIs
|   -> Client Component ('use client')
|
+-- Direct data fetching, secrets, heavy computation, no interactivity
|   -> Server Component (default)
|
+-- Both?
    -> Split: Server parent + Client child
```

### Rules

- Server Components are the DEFAULT. Add `'use client'` only when required.
- Never use hooks (useState, useEffect) in Server Components.
- Never fetch data in Client Components when a Server Component can do it.
- Minimize data passed across the Server/Client boundary -- only pass fields the client actually uses.
- Client Components cannot import Server Components directly. Pass them as `children` or slot props.

```tsx
// CORRECT: Server parent passes only needed data to Client child
async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const product = await getProduct(id)
  return <AddToCartButton productId={product.id} price={product.price} />
}

// WRONG: Passing entire product object across boundary
// return <AddToCartButton product={product} />  // serializes all 50 fields
```

---

## 2. File Conventions and Routing

### App Router File Structure

```
app/
  layout.tsx         # Root layout (required). Wraps all pages. Persists across navigations.
  page.tsx           # Route UI. Makes a route publicly accessible.
  loading.tsx        # Loading UI via Suspense boundary. Shown during navigation.
  error.tsx          # Error boundary. Must be 'use client'.
  not-found.tsx      # 404 UI. Triggered by notFound().
  route.ts           # API endpoint (Route Handler). Cannot coexist with page.tsx.
  template.tsx       # Like layout but re-mounts on navigation. Use for enter/exit animations.
  default.tsx        # Fallback for parallel routes.
  opengraph-image.tsx  # Dynamic OG image generation.
```

### Route Organization

| Pattern | Syntax | Use Case |
|---------|--------|----------|
| Route groups | `(groupName)/` | Organize without affecting URL |
| Dynamic segments | `[param]/` | URL parameters |
| Catch-all | `[...slug]/` | Variable-length paths |
| Optional catch-all | `[[...slug]]/` | Including root path |
| Parallel routes | `@slotName/` | Multiple independent views in same layout |
| Intercepting routes | `(.)segment/` | Modal overlays on navigation |

### Parallel & Intercepting Routes

See `references/routing.md` for parallel-routes and intercepting-routes (modal pattern) examples.

---

## 3. Data Fetching Patterns

### Fetch in Server Components

```tsx
// Static (cached at build time -- default)
const data = await fetch(url)

// ISR (revalidate after N seconds)
const data = await fetch(url, { next: { revalidate: 3600 } })

// Dynamic (every request, no cache)
const data = await fetch(url, { cache: 'no-store' })

// Tag-based (invalidate via revalidateTag)
const data = await fetch(url, { next: { tags: ['products'] } })
```

### Eliminate Waterfalls -- CRITICAL

```tsx
// WRONG: Sequential fetches (3 round trips)
const user = await fetchUser()
const posts = await fetchPosts()
const comments = await fetchComments()

// CORRECT: Parallel fetches (1 round trip)
const [user, posts, comments] = await Promise.all([
  fetchUser(),
  fetchPosts(),
  fetchComments(),
])
```

For dependent fetches, start independent work early:

```tsx
export async function GET(request: Request) {
  const sessionPromise = auth()
  const configPromise = fetchConfig()
  const session = await sessionPromise
  const [config, data] = await Promise.all([
    configPromise,
    fetchData(session.user.id),
  ])
  return Response.json({ data, config })
}
```

### Per-Request Deduplication

```tsx
import { cache } from 'react'

export const getCurrentUser = cache(async () => {
  const session = await auth()
  if (!session?.user?.id) return null
  return db.user.findUnique({ where: { id: session.user.id } })
})
// Multiple calls within one request execute query only once
```

### Streaming with Suspense

```tsx
export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const product = await getProduct(id) // Blocking: critical data

  return (
    <div>
      <ProductHeader product={product} />
      <Suspense fallback={<ReviewsSkeleton />}>
        <Reviews productId={id} />  {/* Streams in independently */}
      </Suspense>
      <Suspense fallback={<RecommendationsSkeleton />}>
        <Recommendations productId={id} />  {/* Streams in independently */}
      </Suspense>
    </div>
  )
}
```

Use Suspense boundaries to stream slow data. Each boundary loads independently. Key the Suspense boundary on searchParams to reset on filter changes:

```tsx
<Suspense key={JSON.stringify(params)} fallback={<Skeleton />}>
  <ProductList filters={params} />
</Suspense>
```

---

## 4. Server Actions

```tsx
// app/actions/cart.ts
'use server'

import { revalidateTag } from 'next/cache'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { z } from 'zod'

const AddToCartSchema = z.object({
  productId: z.string().uuid(),
})

export async function addToCart(productId: string) {
  const parsed = AddToCartSchema.safeParse({ productId })
  if (!parsed.success) return { error: 'Invalid product ID' }

  const cookieStore = await cookies()
  const sessionId = cookieStore.get('session')?.value
  if (!sessionId) redirect('/login')

  try {
    await db.cart.upsert({
      where: { sessionId_productId: { sessionId, productId } },
      update: { quantity: { increment: 1 } },
      create: { sessionId, productId, quantity: 1 },
    })
    revalidateTag('cart')
    return { success: true }
  } catch {
    return { error: 'Failed to add item to cart' }
  }
}
```

### Rules for Server Actions

- Always mark with `'use server'` at top of file or inline in function.
- Always validate inputs with Zod or similar.
- Always return typed response objects `{ success, error }`.
- Use `revalidateTag()` or `revalidatePath()` after mutations.
- Use `redirect()` for post-mutation navigation.
- Call from Client Components via `useTransition` for pending states.

### Client-Side Usage with useTransition

```tsx
'use client'

import { useTransition } from 'react'
import { addToCart } from '@/app/actions/cart'

export function AddToCartButton({ productId }: { productId: string }) {
  const [isPending, startTransition] = useTransition()

  return (
    <button
      disabled={isPending}
      onClick={() => startTransition(() => addToCart(productId))}
    >
      {isPending ? 'Adding...' : 'Add to Cart'}
    </button>
  )
}
```

---

## 5. Route Handlers (API Routes)

```tsx
// app/api/products/route.ts
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const category = request.nextUrl.searchParams.get('category')
  const products = await db.product.findMany({
    where: category ? { category } : undefined,
    take: 20,
  })
  return NextResponse.json(products)
}

export async function POST(request: NextRequest) {
  const body = await request.json()
  // Validate with Zod
  const parsed = CreateProductSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 })
  }
  const product = await db.product.create({ data: parsed.data })
  return NextResponse.json(product, { status: 201 })
}
```

### Route Handler Rules

- Validate all inputs with Zod.
- Return proper HTTP status codes (200, 201, 400, 401, 404, 500).
- Handle errors gracefully with try/catch.
- Use Edge runtime for latency-sensitive endpoints.
- Prefer Server Actions over Route Handlers for form mutations.

---

## 6. Caching Strategies

### Cache Layers

| Layer | Mechanism | Scope |
|-------|-----------|-------|
| Request dedup | `React.cache()` | Single request |
| Data cache | `fetch()` options | Across requests |
| Full route cache | Static/dynamic config | Build or request time |
| Cross-request | LRU cache in memory | Server instance lifetime |

### Revalidation

```tsx
// Time-based ISR
fetch(url, { next: { revalidate: 60 } })

// Tag-based invalidation in Server Action
'use server'
import { revalidateTag, revalidatePath } from 'next/cache'

export async function updateProduct(id: string, data: ProductData) {
  await db.product.update({ where: { id }, data })
  revalidateTag('products')     // Invalidate all fetches tagged 'products'
  revalidatePath('/products')   // Revalidate specific path
}
```

See `references/caching.md` for cross-request LRU caching and non-blocking post-response work with `after()`.

---

## 7. Metadata and SEO

### Static Metadata

```tsx
// app/layout.tsx
export const metadata = {
  title: { default: 'My App', template: '%s | My App' },
  description: 'Built with Next.js App Router',
}
```

### Dynamic Metadata

```tsx
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const product = await getProduct(slug)
  if (!product) return {}

  return {
    title: product.name,
    description: product.description,  // 150-160 chars
    openGraph: {
      title: product.name,
      description: product.description,
      images: [{ url: product.image, width: 1200, height: 630 }],
    },
    twitter: { card: 'summary_large_image' },
  }
}
```

### Static Generation

```tsx
export async function generateStaticParams() {
  const products = await db.product.findMany({ select: { slug: true } })
  return products.map((p) => ({ slug: p.slug }))
}
```

---

## 8. Middleware

```tsx
// middleware.ts (root of project)
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Auth check
  const session = request.cookies.get('session')?.value
  if (!session && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Add headers
  const response = NextResponse.next()
  response.headers.set('x-pathname', request.nextUrl.pathname)
  return response
}

export const config = {
  matcher: ['/dashboard/:path*', '/api/:path*'],
}
```

### Middleware Rules

- Keep middleware lightweight. It runs on every matched request.
- Use `matcher` config to limit scope.
- Do not perform heavy computation or database queries.
- Use for: auth redirects, locale detection, A/B testing headers, rate limiting.

---

## 9. Authentication Patterns

### Cookie-Based Session Flow (Supabase/NextAuth)

- Use `@supabase/ssr` or `next-auth` for App Router integration.
- Refresh sessions in middleware to protect routes.
- Never expose auth tokens to the client unnecessarily.
- Use Server Actions for login/logout operations.
- Use `React.cache()` to deduplicate auth checks within a request.

```tsx
// lib/auth.ts
import { cache } from 'react'

export const getSession = cache(async () => {
  const cookieStore = await cookies()
  const token = cookieStore.get('session')?.value
  if (!token) return null
  return verifyToken(token)
})
```

### Anti-Patterns

- Do not call `getSession()` in Server Components without `cache()` -- causes duplicate DB queries.
- Do not check auth state in Client Components without a listener for changes.

---

## 10. TypeScript Patterns

### Strict Configuration

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

### Next.js-Specific Types

```tsx
// Page props (Next.js 15+ -- params and searchParams are Promises)
type PageProps = {
  params: Promise<{ slug: string }>
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}

// Layout props
type LayoutProps = {
  children: React.ReactNode
  params: Promise<{ slug: string }>
}

// Route Handler
import type { NextRequest } from 'next/server'
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) { /* ... */ }

// Server Action return type
type ActionResult = { success: true } | { error: string }
```

### General TypeScript Rules

- Prefer type inference over explicit annotations when the type is obvious.
- Use `interface` for objects that may be extended; `type` for unions, intersections, and utility types.
- Use generics with constraints: `<T extends Record<string, unknown>>`.
- Validate external data at runtime with Zod; infer TypeScript types from schemas.
- Never use `any`. Use `unknown` and narrow with type guards.
- Use discriminated unions for state: `{ status: 'loading' } | { status: 'success'; data: T } | { status: 'error'; error: string }`.

---

## 11. Performance Optimization

### Bundle Size -- CRITICAL

- **Avoid barrel file imports.** Import from direct paths, not index files. Or use `optimizePackageImports` in next.config.
- **Dynamic imports** for heavy components: `const Editor = dynamic(() => import('./Editor'), { ssr: false })`.
- **Defer third-party scripts** (analytics, logging) with `next/dynamic` and `{ ssr: false }`.
- **Preload on intent**: trigger `import()` on hover/focus before user clicks.

### Rendering Performance

- Use `content-visibility: auto` with `contain-intrinsic-size` for long lists.
- Hoist static JSX outside components to avoid re-creation.
- Use `startTransition` for non-urgent state updates (search filters, scroll tracking).
- Use ternary `condition ? <A /> : null` instead of `&&` to avoid rendering `0` or `NaN`.

### Re-render Optimization

- Use functional `setState`: `setItems(curr => [...curr, newItem])` for stable callbacks.
- Use lazy state initialization: `useState(() => expensiveComputation())`.
- Narrow effect dependencies to primitives: `[user.id]` not `[user]`.
- Subscribe to derived booleans (`useMediaQuery`) instead of continuous values (`useWindowWidth`).
- Extract expensive subtrees into `memo()` components (unless React Compiler is enabled).

### Image Optimization

- Always use `next/image`. Set `priority` for above-fold images.
- Provide `width`/`height` or use `fill` with `sizes` attribute.
- Use `placeholder="blur"` with `blurDataURL` for perceived performance.

### Core Web Vitals Targets

| Metric | Target | Key Levers |
|--------|--------|------------|
| LCP | < 2.5s | Image priority, streaming, font optimization |
| FID/INP | < 200ms | Code splitting, transitions, minimal client JS |
| CLS | < 0.1 | Image dimensions, font `display: swap`, skeleton layouts |

---

## 12. Project Structure

```
app/
  (marketing)/          # Public pages route group
    page.tsx
    about/page.tsx
  (dashboard)/          # Authenticated pages route group
    layout.tsx          # Dashboard layout with auth check
    page.tsx
    settings/page.tsx
  api/
    [resource]/
      route.ts
  actions/              # Server Actions
    cart.ts
    auth.ts
  layout.tsx            # Root layout
  loading.tsx
  error.tsx
  not-found.tsx

components/
  ui/                   # Primitive UI components (Button, Input, Card)
  features/             # Feature-specific components
  layouts/              # Layout components

lib/
  db.ts                 # Database client
  auth.ts               # Auth utilities with React.cache()
  utils.ts              # General utilities
  validations/          # Zod schemas

types/
  index.ts              # Shared TypeScript types

public/                 # Static assets
```

### Rules

- Colocate components with their route when feature-specific.
- Share components via `components/` at project root.
- Keep Server Actions in `app/actions/` or colocated with their route.
- Keep Zod schemas in `lib/validations/` and share between client and server.

---

## 13. Forms and Validation

```tsx
// lib/validations/contact.ts
import { z } from 'zod'

export const ContactSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  message: z.string().min(10).max(1000),
})

export type ContactFormData = z.infer<typeof ContactSchema>
```

```tsx
// app/actions/contact.ts
'use server'
import { ContactSchema } from '@/lib/validations/contact'

export async function submitContact(formData: FormData) {
  const raw = Object.fromEntries(formData)
  const parsed = ContactSchema.safeParse(raw)

  if (!parsed.success) {
    return { error: parsed.error.flatten().fieldErrors }
  }

  await sendEmail(parsed.data)
  return { success: true }
}
```

Use React Hook Form for complex client-side forms. Use native `<form action={serverAction}>` for progressive enhancement.

---

## 14. Error Handling

### Error Boundaries

```tsx
// app/error.tsx -- Must be 'use client'
'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div role="alert">
      <h2>Something went wrong</h2>
      <p>{error.message}</p>
      <button onClick={reset}>Try again</button>
    </div>
  )
}
```

### Not Found

```tsx
// In any Server Component
import { notFound } from 'next/navigation'

export default async function ProductPage({ params }: Props) {
  const product = await getProduct((await params).slug)
  if (!product) notFound()  // Renders closest not-found.tsx
  return <ProductDetail product={product} />
}
```

### Server Action Error Handling

Always return structured errors. Never throw from Server Actions -- catch and return:

```tsx
export async function createPost(data: FormData) {
  try {
    const parsed = PostSchema.safeParse(Object.fromEntries(data))
    if (!parsed.success) return { error: 'Validation failed', fields: parsed.error.flatten() }
    const post = await db.post.create({ data: parsed.data })
    revalidatePath('/posts')
    return { success: true, postId: post.id }
  } catch {
    return { error: 'Failed to create post' }
  }
}
```

---

## 15. Testing

Unit/Integration with Vitest + React Testing Library; E2E with Playwright.

### Testing Rules

- Test behavior, not implementation.
- Use `screen.getByRole` over `getByTestId` for accessibility alignment.
- Mock external APIs and database calls.
- Test Server Components by testing their rendered output.
- Test Server Actions by calling them directly with mock data.

See `testing-guidelines.md` for Server Component/Action testing, module mocking, Suspense boundaries, error/not-found tests, and E2E examples.

---

## 16. Security

- **CSRF**: Server Actions include CSRF protection automatically. For Route Handlers, verify `Origin` header.
- **XSS**: React escapes output by default. Never use `dangerouslySetInnerHTML` with user input.
- **Environment variables**: Only `NEXT_PUBLIC_*` vars are exposed to the client. Keep secrets server-side.
- **Auth tokens**: Use HTTP-only, Secure, SameSite cookies. Never store in localStorage.
- **Headers**: Configure CSP, HSTS, X-Frame-Options in `next.config.js` or middleware.

---

## 17. Accessibility

- Use semantic HTML elements (`nav`, `main`, `article`, `section`, `button`, `a`).
- All images require meaningful `alt` text (or `alt=""` for decorative).
- Interactive elements must be keyboard accessible with visible focus indicators.
- Use ARIA attributes only when semantic HTML is insufficient.
- Implement skip navigation links.
- Ensure color contrast meets WCAG 2.1 AA (4.5:1 for text).
- Forms: associate labels with inputs, provide error messages linked via `aria-describedby`.
- Test with axe-core and screen reader.

---

## 18. Deployment

### Vercel

- Push to Git. Vercel deploys automatically.
- Set environment variables in Vercel dashboard.
- Use preview deployments for PR review.
- Configure `vercel.json` for redirects, rewrites, headers.

### Docker

See `references/deployment.md` for the standalone Dockerfile and the required `output: 'standalone'` config.

---

## 19. Anti-Patterns Reference

| Anti-Pattern | Correct Approach |
|---|---|
| `'use client'` on everything | Server Components by default |
| Fetching data in Client Components | Fetch in Server Components or use SWR/React Query |
| No loading.tsx or Suspense boundaries | Always provide loading states |
| No error.tsx error boundaries | Add error boundaries at route and feature level |
| Barrel file imports from large libraries | Direct imports or `optimizePackageImports` |
| Passing entire objects across Server/Client boundary | Pass only the fields the client needs |
| `any` types | Use `unknown` with type narrowing |
| Skipping input validation on server | Always validate with Zod on server |
| Mutating arrays/objects in state | Use immutable methods: `toSorted()`, spread, `with()` |
| `&&` for conditional rendering with numbers | Use ternary: `count > 0 ? <Badge /> : null` |
| Awaiting before early return is possible | Defer await into the branch that needs it |
| Large client bundles | Dynamic imports, code splitting |

---

## 20. next.config.js

See `references/deployment.md` for a `next.config.js` reference covering `optimizePackageImports`, standalone output, image optimization, and security headers.
