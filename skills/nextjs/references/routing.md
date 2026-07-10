# Next.js Advanced Routing Examples

Full examples referenced from SKILL.md §2. The route-pattern table stays in the skill body.

## Parallel Routes

```tsx
// app/dashboard/layout.tsx
export default function DashboardLayout({
  children,
  analytics,
  team,
}: {
  children: React.ReactNode
  analytics: React.ReactNode
  team: React.ReactNode
}) {
  return (
    <div className="dashboard-grid">
      <main>{children}</main>
      <aside>{analytics}</aside>
      <aside>{team}</aside>
    </div>
  )
}
// Each @slot loads independently with its own loading.tsx and error.tsx
```

## Intercepting Routes (Modal Pattern)

```
app/
  @modal/(.)photos/[id]/page.tsx   # Intercept: shows as modal
  @modal/default.tsx               # No modal by default
  photos/[id]/page.tsx             # Full page on direct navigation
  layout.tsx                       # Renders {children} + {modal}
```
