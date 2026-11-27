# React Testing Guidelines

Framework-specific testing patterns for React applications. These complement the general testing principles in `brain/knowledge/testing.md`.

## Framework Stack

- **Vitest** + **React Testing Library** for component tests
- **Storybook** + **Chromatic** for visual regression testing
- **axe-core** for accessibility testing
- **Playwright** for E2E critical user journeys

## Core Philosophy

- Test **user behavior**, not implementation details
- Never test internal state or lifecycle methods
- Mock external APIs, not React internals
- Tests should resemble how users interact with the app

## Querying Elements

Prefer queries in this priority order:

1. `getByRole` -- accessible role (button, heading, textbox)
2. `getByLabelText` -- form inputs
3. `getByText` -- visible text content
4. `getByPlaceholderText` -- placeholder text
5. **Avoid** `getByTestId` and CSS class selectors

```typescript
// Good
screen.getByRole('button', { name: /submit/i });
screen.getByLabelText('Email address');
screen.getByText('Welcome back');

// Avoid
screen.getByTestId('submit-btn');
container.querySelector('.btn-primary');
```

## User Interactions

Prefer `userEvent` over `fireEvent`:

```typescript
import userEvent from '@testing-library/user-event';

it('should submit the form when clicking submit', async () => {
  const user = userEvent.setup();
  render(<LoginForm onSubmit={mockSubmit} />);

  await user.type(screen.getByLabelText('Email'), 'user@example.com');
  await user.type(screen.getByLabelText('Password'), 'password123');
  await user.click(screen.getByRole('button', { name: /sign in/i }));

  expect(mockSubmit).toHaveBeenCalledWith({
    email: 'user@example.com',
    password: 'password123',
  });
});
```

## Testing States

Always test error, loading, and empty states:

```typescript
it('should show loading spinner while fetching', () => {
  render(<UserList />);
  expect(screen.getByRole('progressbar')).toBeInTheDocument();
});

it('should show error message on fetch failure', async () => {
  server.use(http.get('/api/users', () => HttpResponse.error()));
  render(<UserList />);
  expect(await screen.findByRole('alert')).toHaveTextContent(/failed to load/i);
});

it('should show empty state when no users exist', async () => {
  server.use(http.get('/api/users', () => HttpResponse.json([])));
  render(<UserList />);
  expect(await screen.findByText(/no users found/i)).toBeInTheDocument();
});
```

## Accessibility Testing

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

it('should have no accessibility violations', async () => {
  const { container } = render(<Navigation />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

## E2E with Playwright

```typescript
test('user can complete checkout flow', async ({ page }) => {
  await page.goto('/products');
  await page.getByRole('button', { name: /add to cart/i }).first().click();
  await page.getByRole('link', { name: /cart/i }).click();
  await page.getByRole('button', { name: /checkout/i }).click();
  await expect(page.getByRole('heading', { name: /order confirmed/i })).toBeVisible();
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

Each is a ledger entry with a disposition and a ground, or it doesn't happen. Reference: Vitest's
[test API](https://vitest.dev/api/), [describe API](https://vitest.dev/api/describe),
[exclude config](https://vitest.dev/config/exclude), [CLI](https://vitest.dev/guide/cli),
[snapshot guide](https://vitest.dev/guide/snapshot), and
[coverage config](https://vitest.dev/config/coverage); Playwright's
[annotations](https://playwright.dev/docs/test-annotations),
[CLI](https://playwright.dev/docs/test-cli), and
[TestConfig](https://playwright.dev/docs/api/class-testconfig).

## Key Principles

- Never test internal state (`component.state`) or lifecycle methods
- Mock at the network boundary (MSW), not at the component/hook level
- Use `screen` from RTL -- avoid destructuring render result
- Use `findBy*` for async content, `getBy*` for synchronous
- Wrap state updates in `act()` only when RTL doesn't do it automatically
