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

## Key Principles

- Never test internal state (`component.state`) or lifecycle methods
- Mock at the network boundary (MSW), not at the component/hook level
- Use `screen` from RTL -- avoid destructuring render result
- Use `findBy*` for async content, `getBy*` for synchronous
- Wrap state updates in `act()` only when RTL doesn't do it automatically
