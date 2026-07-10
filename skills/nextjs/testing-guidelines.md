# Next.js Testing Guidelines

Framework-specific testing patterns for Next.js applications. These complement the general testing principles in `brain/knowledge/testing.md`.

## Framework Stack

- **Vitest** + **React Testing Library** for unit/integration tests
- **Playwright** for E2E tests

## Testing Server Components

Test Server Components by testing their rendered output:

```typescript
import { render, screen } from '@testing-library/react';
import { UserProfile } from './UserProfile';

// Mock the data fetching
vi.mock('@/lib/db', () => ({
  getUser: vi.fn().mockResolvedValue({ id: '1', name: 'Alice', email: 'alice@example.com' }),
}));

it('should render user profile with fetched data', async () => {
  const Component = await UserProfile({ params: { id: '1' } });
  render(Component);
  expect(screen.getByText('Alice')).toBeInTheDocument();
});
```

## Testing Server Actions

Call Server Actions directly with mock data:

```typescript
import { createUser } from './actions';

vi.mock('@/lib/db', () => ({
  insertUser: vi.fn().mockResolvedValue({ id: '1' }),
}));

it('should create a user and return success', async () => {
  const formData = new FormData();
  formData.set('name', 'Alice');
  formData.set('email', 'alice@example.com');

  const result = await createUser(formData);

  expect(result.success).toBe(true);
  expect(db.insertUser).toHaveBeenCalledWith({
    name: 'Alice',
    email: 'alice@example.com',
  });
});
```

## Mocking External Dependencies

Mock external APIs and database calls at the module boundary:

```typescript
vi.mock('@/lib/api', () => ({
  fetchProducts: vi.fn().mockResolvedValue([
    { id: '1', name: 'Widget', price: 9.99 },
  ]),
}));

vi.mock('@/lib/db', () => ({
  prisma: {
    user: {
      findUnique: vi.fn(),
      create: vi.fn(),
    },
  },
}));
```

## Querying Elements

Prefer accessible queries (same as React Testing Library best practices):

```typescript
// Good -- accessibility-aligned
screen.getByRole('button', { name: /save/i });
screen.getByRole('heading', { level: 1 });
screen.getByLabelText('Email');

// Avoid unless no accessible alternative exists
screen.getByTestId('save-button');
```

## Testing with Suspense Boundaries

```typescript
import { Suspense } from 'react';
import { render, screen } from '@testing-library/react';

it('should show fallback then content', async () => {
  render(
    <Suspense fallback={<div>Loading...</div>}>
      <AsyncComponent />
    </Suspense>
  );

  expect(screen.getByText('Loading...')).toBeInTheDocument();
  expect(await screen.findByText('Loaded content')).toBeInTheDocument();
});
```

## Testing error.tsx and not-found.tsx

```typescript
import ErrorBoundary from './error';
import NotFound from './not-found';

it('should render error UI with reset button', () => {
  const mockReset = vi.fn();
  render(<ErrorBoundary error={new Error('Something failed')} reset={mockReset} />);

  expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /try again/i }));
  expect(mockReset).toHaveBeenCalled();
});

it('should render not-found page', () => {
  render(<NotFound />);
  expect(screen.getByRole('heading', { name: /not found/i })).toBeInTheDocument();
});
```

## E2E with Playwright

```typescript
test('user can navigate and submit form', async ({ page }) => {
  await page.goto('/dashboard');
  await page.getByRole('link', { name: /settings/i }).click();
  await page.getByLabel('Display name').fill('New Name');
  await page.getByRole('button', { name: /save/i }).click();
  await expect(page.getByText('Settings saved')).toBeVisible();
});
```

## Key Principles

- Mock at the data layer (database, API), not at React level
- Test Server Components as async functions that return JSX
- Test Server Actions as regular async functions
- Use `screen.getByRole` over `getByTestId` for accessibility alignment
- Always test error and not-found boundaries
- Test with proper Suspense boundaries to catch loading states
