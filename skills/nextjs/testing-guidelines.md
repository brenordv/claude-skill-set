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

## Test-weakening tells

`brain/knowledge/testing.md` ⛔ Hard Rules 2 and 3 govern any change to an existing test, and
`brain/knowledge/review-heuristics.md` §Testing ("Test integrity") lists the moves. In this stack
they look like this, on a line the diff adds or changes:

- Vitest: `test.skip` / `it.skip`, `describe.skip`, `test.skipIf`, `test.runIf`, or `skip()`
  called on the test context.
- Vitest: `test.only` or `describe.only` left in, so only the marked tests run. Vitest throws on
  `only` when it detects CI, and `--allowOnly` turns that off.
- Vitest: `test.todo` replacing a test that had a body, or `test.fails`, which passes when the
  assertion fails.
- Vitest command or config: `-t` / `--testNamePattern`, `--exclude` or `test.exclude`,
  `--passWithNoTests`, `--retry.count` or a `retry` option, `-u` / `--update` rewriting
  snapshots, or lower `coverage.thresholds`.
- Playwright: `test.skip`, `test.fixme`, `test.fail` (the test passes only if it fails),
  `test.slow` (triples the timeout), `test.only`, and the `test.describe.skip` / `.fixme` /
  `.only` forms.
- Playwright command or config: `--grep` / `grep`, `--grep-invert` / `grepInvert`,
  `testIgnore`, `--retries` / `retries`, `-u` / `--update-snapshots`, `--pass-with-no-tests`, or
  `forbidOnly` turned off.

Each is a ledger entry with a disposition and a ground, or it doesn't happen. One move has no
legitimate form, whatever the ledger says: a `vi.mock` of the module under test, or one whose
return value was changed to what the assertion expects (`brain/knowledge/testing.md` ⛔ Hard
Rule 3). Reference: Vitest's
[test API](https://vitest.dev/api/), [describe API](https://vitest.dev/api/describe),
[exclude config](https://vitest.dev/config/exclude), [CLI](https://vitest.dev/guide/cli),
[snapshot guide](https://vitest.dev/guide/snapshot), and
[coverage config](https://vitest.dev/config/coverage); Playwright's
[annotations](https://playwright.dev/docs/test-annotations),
[CLI](https://playwright.dev/docs/test-cli), and
[TestConfig](https://playwright.dev/docs/api/class-testconfig).

## Key Principles

- Mock at the data layer (database, API), not at React level
- Test Server Components as async functions that return JSX
- Test Server Actions as regular async functions
- Use `screen.getByRole` over `getByTestId` for accessibility alignment
- Always test error and not-found boundaries
- Test with proper Suspense boundaries to catch loading states
