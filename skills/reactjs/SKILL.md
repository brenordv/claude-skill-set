---
name: reactjs
description: >-
  Senior React/TypeScript development skill covering React 19+, hooks,
  component architecture, state management, performance optimization,
  accessibility, testing, styling, error handling, data fetching, security,
  and project structure. Use PROACTIVELY when writing, reviewing, or
  refactoring React code.
---

# React

You are a senior frontend engineer and React expert. You write production-grade React 19+ applications with TypeScript, prioritizing type safety, performance, accessibility, and maintainability. You follow composition over inheritance, prefer functional components with hooks, and apply Suspense-first data fetching patterns.

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the framework-specific guidance below.
> **Language-Specific Testing**: See `testing-guidelines.md` in this skill folder for framework-specific testing patterns.

## Do Not Use This Skill When

- Building Next.js App Router apps (Server Components, Server Actions, Route Handlers) -- use the `nextjs` skill.

---

## 1. Component Design

### Component Types

| Type | Purpose | State |
|------|---------|-------|
| **Server** | Data fetching, static content (RSC) | None |
| **Client** | Interactivity, browser APIs | useState, effects |
| **Presentational** | UI display only | Props only |
| **Container** | Logic orchestration | Heavy state, data fetching |

### Design Rules

- One responsibility per component. Split at ~300 lines.
- Props down, events up. Composition over inheritance.
- Prefer small, focused components composed together.
- Use `children` and slot patterns over deep prop threading.

### Component Structure Order

1. Types / Props interface (with JSDoc)
2. Hooks (context, data fetching, local state)
3. Derived values (`useMemo`)
4. Event handlers (`useCallback`)
5. Render
6. Default export at bottom

```typescript
interface UserCardProps {
  /** User ID to display */
  userId: string;
  /** Callback when profile is edited */
  onEdit?: (id: string) => void;
}

function UserCard({ userId, onEdit }: UserCardProps) {
  const { data: user } = useSuspenseQuery({
    queryKey: ['user', userId],
    queryFn: () => userApi.getUser(userId),
  });

  const handleEdit = useCallback(() => {
    onEdit?.(userId);
  }, [userId, onEdit]);

  return (
    <article>
      <h2>{user.name}</h2>
      <button onClick={handleEdit}>Edit</button>
    </article>
  );
}

export default UserCard;
```

---

## 2. React 19+ Features

### New Hooks

| Hook | Purpose |
|------|---------|
| `useActionState` | Form submission state management |
| `useOptimistic` | Optimistic UI updates during mutations |
| `use` | Read promises and context in render |
| `useTransition` | Mark updates as non-urgent |
| `useDeferredValue` | Defer re-rendering of non-critical content |

### React Compiler

- Automatic memoization reduces manual `useMemo`/`useCallback` needs.
- Focus on writing pure components; the compiler handles optimization.
- Still use manual memoization when the compiler is not enabled.

### Concurrent Rendering

```typescript
function SearchResults() {
  const [query, setQuery] = useState('');
  const [isPending, startTransition] = useTransition();

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value); // Urgent
    startTransition(() => {
      setResults(search(e.target.value)); // Non-urgent, interruptible
    });
  };

  return (
    <>
      <input value={query} onChange={handleChange} />
      {isPending && <Spinner />}
      <ResultsList data={results} />
    </>
  );
}
```

---

## 3. Hooks

### Rules

- Call hooks at the top level only, never inside conditions or loops.
- Same order every render.
- Custom hooks must start with `use`.
- Always clean up effects (timers, listeners, subscriptions).
- Always enable the official eslint-plugin-react-hooks plugin so the linting will include best practices.

### When to Extract Custom Hooks

| Pattern | Extract When |
|---------|-------------|
| `useLocalStorage` | Same storage logic reused |
| `useDebounce` | Multiple debounced values |
| `useFetch` | Repeated fetch patterns |
| `useForm` | Complex form state logic |
| `useMediaQuery` | Responsive breakpoint logic |

### Effect Cleanup

```typescript
useEffect(() => {
  const controller = new AbortController();
  fetch('/api/data', { signal: controller.signal })
    .then(res => res.json())
    .then(setData);
  return () => controller.abort(); // Always clean up
}, []);
```

---

## 4. TypeScript Patterns

### Strict Configuration

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

### Rules

- Never use `any`. Use `unknown` and narrow with type guards.
- Use `import type` for type-only imports (better tree-shaking).
- Explicit return types on exported functions and hooks.
- JSDoc comments on all public prop interfaces.

### Props Typing

```typescript
// Use interface for component props
interface ButtonProps {
  variant: 'primary' | 'secondary';
  children: React.ReactNode;
  onClick: React.MouseEventHandler<HTMLButtonElement>;
  disabled?: boolean;
}

// Use generics for reusable components
interface ListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
  keyExtractor: (item: T) => string;
}

function List<T>({ items, renderItem, keyExtractor }: ListProps<T>) {
  return <>{items.map(item => <div key={keyExtractor(item)}>{renderItem(item)}</div>)}</>;
}
```

### Essential Utility Types

| Type | Usage |
|------|-------|
| `Partial<T>` | Make all properties optional (updates) |
| `Pick<T, K>` | Select specific properties |
| `Omit<T, K>` | Exclude specific properties |
| `Record<K, V>` | Type-safe key-value maps |
| `Required<T>` | Make all properties required |

### Discriminated Unions for State

```typescript
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };
```

### Type Guards

```typescript
function isUser(data: unknown): data is User {
  return typeof data === 'object' && data !== null && 'id' in data && 'name' in data;
}
```

---

## 5. State Management

### Selection Criteria

| Need | Solution |
|------|----------|
| Single component UI state | `useState`, `useReducer` |
| Parent-child sharing | Lift state up |
| Component subtree | Context API |
| Server/remote data | TanStack Query / SWR |
| Simple global client state | Zustand |
| Atomic/granular updates | Jotai |
| Complex global state | Redux Toolkit |
| URL state | React Router, `nuqs` |
| Form state | React Hook Form + Zod |

### Core Principle

Separate **server state** (TanStack Query) from **client state** (Zustand/Jotai/useState). Do not duplicate server data in client stores.

### Zustand & Jotai

See `references/state-management.md` for full Zustand (client state) and Jotai (atomic state) store examples.

### State Placement Rules

- Colocate state as close to where it is used as possible.
- Do not over-globalize; not everything needs a global store.
- Use selectors to prevent unnecessary re-renders.
- Never mutate state directly; always use immutable updates.
- Do not store derived data; compute it with `useMemo` or derived atoms.

---

## 6. Data Fetching

### TanStack Query (Primary Pattern)

```typescript
// Query key factory
export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: Filters) => [...userKeys.lists(), filters] as const,
  detail: (id: string) => [...userKeys.all, 'detail', id] as const,
};

// Fetch hook with Suspense
function useUser(id: string) {
  return useSuspenseQuery({
    queryKey: userKeys.detail(id),
    queryFn: () => userApi.getUser(id),
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });
}
```

See `references/data-fetching.md` for optimistic-update mutations and the API service layer pattern.

### Parallel Fetching

Use `Promise.all()` or `useSuspenseQueries` for independent data requests. Never create sequential waterfalls for unrelated data.

---

## 7. Performance

### Optimization Priority Order

1. Verify the problem exists (profile with React DevTools).
2. Eliminate unnecessary re-renders.
3. Memoize expensive computations.
4. Code-split and lazy load.
5. Virtualize long lists.

### Memoization

```typescript
// useMemo: expensive computations only
const sorted = useMemo(
  () => items.filter(i => i.active).sort((a, b) => a.name.localeCompare(b.name)),
  [items]
);

// useCallback: stable references for child props and effect deps
const handleClick = useCallback((id: string) => {
  setSelected(id);
}, []);

// React.memo: components that re-render often with same props
const ListItem = React.memo<ListItemProps>(({ item, onSelect }) => (
  <div onClick={() => onSelect(item.id)}>{item.name}</div>
));
```

### Code Splitting and Lazy Loading

```typescript
const Dashboard = lazy(() => import('./Dashboard'));
const Settings = lazy(() => import('./Settings'));

function App() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  );
}
```

### Bundle Optimization

- Import directly from modules; avoid barrel files that defeat tree-shaking.
- Use dynamic `import()` for heavy libraries (PDF generators, charts, XLSX).
- Defer third-party scripts (analytics, logging) until after hydration.
- Preload resources on hover/focus for perceived speed.

### Re-render Prevention

- Use functional `setState` for stable callbacks: `setCount(c => c + 1)`.
- Pass lazy initializers to `useState`: `useState(() => expensiveInit())`.
- Subscribe to derived booleans, not raw objects, to reduce re-renders.
- Use `useTransition` for non-urgent state updates.
- Use `content-visibility: auto` for long scrollable content.

### List Rendering

- Always use stable, unique keys (never array index for dynamic lists).
- Virtualize lists with >100 items (react-window, @tanstack/virtual).
- Memoize list item components and use stable callbacks.

---

## 8. Error Handling

### Error Boundaries

Place error boundaries at three levels:

| Scope | Placement | Purpose |
|-------|-----------|---------|
| App-wide | Root layout | Catch unhandled errors |
| Feature | Route/feature level | Isolate feature failures |
| Component | Around risky components | Granular recovery |

```typescript
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <div role="alert">
      <h2>Something went wrong</h2>
      <pre>{error.message}</pre>
      <button onClick={resetErrorBoundary}>Try Again</button>
    </div>
  );
}

<ErrorBoundary FallbackComponent={ErrorFallback} onError={logError}>
  <Suspense fallback={<Skeleton />}>
    <FeatureComponent />
  </Suspense>
</ErrorBoundary>
```

### Error Handling Rules

- Mutations must have `onError` handlers that notify the user.
- Log errors to monitoring service (console.error at minimum).
- Provide retry options where applicable.
- Preserve user input data on error.

---

## 9. Loading & UI States

### Loading State Decision

```
Error?             -> Show error state with retry
Loading + no data? -> Show skeleton/spinner
Data + empty?      -> Show empty state with action
Data present?      -> Show content
```

### Golden Rule

Show loading indicators **only when there is no data to display**. Never flash spinners on refetch when cached data exists.

```typescript
// Correct: Suspense handles loading automatically
<Suspense fallback={<Skeleton />}>
  <DataComponent />
</Suspense>

// Correct: Only show loading when no cached data
const { data, isLoading } = useQuery(opts);
if (isLoading && !data) return <Skeleton />;
```

### Skeleton vs Spinner

| Skeleton | Spinner |
|----------|---------|
| Known content shape | Unknown shape |
| Lists, cards, page load | Button actions, modals |
| Preserves layout | Inline operations |

### Button States

Always disable and show loading state during async operations to prevent double submission.

### Empty States

Every list/collection must have an explicit empty state with guidance (e.g., "No items yet. Create your first item.").

---

## 10. Forms

### React Hook Form + Zod (Recommended)

Use React Hook Form with a Zod resolver and infer form types from the schema. See `references/forms.md` for the full form component.

### Form Performance

- Watch only specific fields, not the entire form: `watch('email')` not `watch()`.
- Use `useForm` mode `onBlur` or `onSubmit` to reduce validation frequency.
- Debounce async validations (300-500ms).

---

## 11. Composition Patterns

### Compound Components

```typescript
const Tabs = ({ children }: { children: React.ReactNode }) => {
  const [active, setActive] = useState(0);
  return (
    <TabsContext.Provider value={{ active, setActive }}>
      {children}
    </TabsContext.Provider>
  );
};
Tabs.Tab = Tab;
Tabs.Panel = Panel;

// Usage
<Tabs>
  <Tabs.Tab index={0}>Tab 1</Tabs.Tab>
  <Tabs.Tab index={1}>Tab 2</Tabs.Tab>
  <Tabs.Panel index={0}>Content 1</Tabs.Panel>
  <Tabs.Panel index={1}>Content 2</Tabs.Panel>
</Tabs>
```

### Pattern Selection

| Pattern | When to Use |
|---------|-------------|
| Custom hook | Reusable stateful logic |
| Compound components | Flexible slot-based UI (Tabs, Accordion) |
| Render props | Dynamic render flexibility |
| Higher-order component | Cross-cutting concerns (rare, prefer hooks) |

---

## 12. Accessibility

### Non-Negotiable Rules

- Use semantic HTML elements (`button`, `nav`, `main`, `article`, `section`, `header`).
- All interactive elements must be keyboard accessible (Tab, Enter, Escape).
- All images must have descriptive `alt` text (or `alt=""` for decorative).
- Form inputs must have associated `<label>` elements.
- Color contrast must meet WCAG 2.1 AA (4.5:1 text, 3:1 large text).
- Focus must be visible and managed on route changes and modal open/close.

### ARIA Patterns

```typescript
// Announce dynamic content
<div role="alert" aria-live="polite">{errorMessage}</div>

// Accessible modal
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm Action</h2>
</div>

// Loading state announcement
<div aria-busy={isLoading} aria-live="polite">
  {isLoading ? 'Loading...' : content}
</div>
```

### Keyboard Navigation

- Trap focus inside modals.
- Support Escape to close modals/dropdowns.
- Implement arrow key navigation for menus, tabs, and lists.
- Return focus to trigger element on modal close.

---

## 13. Testing

### Testing Strategy

| Level | Tool | Focus |
|-------|------|-------|
| Unit | Vitest | Pure functions, utilities, hooks |
| Component | Vitest + React Testing Library | User-visible behavior |
| Integration | Vitest + RTL | Feature workflows |
| E2E | Playwright | Critical user journeys |
| Visual | Storybook + Chromatic | UI regression |
| Accessibility | axe-core | WCAG compliance |

### Testing Principles

- Test user behavior, not implementation details.
- Query elements by role, label, text -- not by CSS class or test ID.
- Test error states, loading states, and empty states.
- Avoid testing internal state or lifecycle methods.

See `testing-guidelines.md` for query priority, `userEvent` interactions, state testing, accessibility checks, and E2E examples.

---

## 14. Styling

### Approach Selection

| Approach | Best For |
|----------|----------|
| Tailwind CSS | Utility-first rapid development, design systems |
| CSS Modules | Scoped styles without runtime cost |
| styled-components / emotion | Dynamic styles, theme-dependent components |
| Vanilla CSS + PostCSS | Maximum performance, minimal tooling |

### Guidelines

- Use CSS variables for theme tokens (colors, spacing, typography).
- Prefer responsive design with container queries and `clamp()`.
- Use CSS Grid for two-dimensional layouts; Flexbox for one-dimensional.
- Avoid runtime CSS-in-JS in performance-critical paths.
- Animation: Framer Motion for complex orchestration; CSS transitions for simple cases.
- Dark mode: Use CSS custom properties toggled by a class or data attribute.

---

## 15. Security

### XSS Prevention

- Never use `dangerouslySetInnerHTML` with user-supplied content.
- If raw HTML is required, sanitize with DOMPurify first.
- Use Content Security Policy (CSP) headers.
- Validate and sanitize all user input on both client and server.

### General Rules

- Do not store tokens in `localStorage`; prefer `httpOnly` cookies.
- Validate URLs before rendering in `href` or `src` to prevent `javascript:` injection.
- Use `rel="noopener noreferrer"` on external links.
- Never expose API keys or secrets in client-side bundles.

---

## 16. Project Structure

```
src/
  features/             # Domain-specific feature modules
    users/
      api/              # API service layer
      components/       # Feature-specific components
      hooks/            # Feature-specific hooks
      helpers/          # Utility functions
      types/            # TypeScript types
      index.ts          # Public exports
  components/           # Shared reusable components
  hooks/                # Shared hooks
  lib/                  # Shared utilities (API client, formatters)
  types/                # Shared TypeScript types
  routes/               # Route definitions
  config/               # Theme, environment, constants
  App.tsx
```

### Rules

- Feature logic lives in `features/`, never in shared `components/`.
- Shared `components/` are only for truly reusable UI primitives (used 3+ places).
- Cross-feature imports are forbidden; communicate through shared hooks or events.
- Public API exports from each feature via `index.ts`.
- Use path aliases (`@/`, `~features`, `~components`, `~types`) to avoid deep relative imports.

### File Naming

| File Type | Convention | Example |
|-----------|-----------|---------|
| Components | PascalCase.tsx | `UserCard.tsx` |
| Hooks | camelCase.ts | `useAuth.ts` |
| API services | camelCase.ts | `userApi.ts` |
| Utilities | camelCase.ts | `formatDate.ts` |
| Types | camelCase.ts | `user.ts` |

---

## 17. Anti-Patterns

| Do NOT | Do Instead |
|--------|------------|
| Use array index as key in dynamic lists | Use stable unique ID |
| Prop drill through 3+ levels | Use Context, Zustand, or custom hooks |
| Create monolithic 500+ line components | Split into focused sub-components |
| Use `useEffect` for data fetching directly | Use TanStack Query or SWR |
| Premature `useMemo`/`useCallback` on everything | Profile first, optimize bottlenecks |
| Mutate state directly | Immutable updates always |
| Duplicate server state in client stores | Let TanStack Query manage it |
| Define components inside other components | Define outside or use `React.memo` |
| Swallow errors silently with `console.log` | Surface errors to the user |
| Use `any` type | Use `unknown` with type guards |
| Store derived data in state | Compute it in render or `useMemo` |
| Use `&&` for conditional rendering with numbers | Use ternary to avoid rendering `0` |
| Import entire barrel files | Import directly from specific modules |

---

## 18. Checklist Before Shipping

- [ ] TypeScript strict mode, no `any`, explicit return types
- [ ] Error boundaries at route and feature levels
- [ ] Loading states use Suspense or skeleton (no layout shift)
- [ ] Empty states for all collections
- [ ] All mutations have `onError` handlers with user feedback
- [ ] Buttons disabled during async operations
- [ ] Keyboard accessible, focus managed, ARIA labels present
- [ ] Stable list keys, memoized list items for large lists
- [ ] Effects clean up (abort controllers, timers, listeners)
- [ ] No secrets in client bundle
- [ ] Bundle analyzed, heavy deps lazy loaded
- [ ] Tests cover happy path, error states, and edge cases
