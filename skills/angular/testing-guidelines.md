# Angular Testing Guidelines

Framework-specific testing patterns for Angular applications. These complement the general testing principles in `brain/knowledge/testing.md`.

## Unit Testing (Jasmine + Karma or Jest)

### TestBed Configuration

```typescript
beforeEach(async () => {
  await TestBed.configureTestingModule({
    imports: [MyStandaloneComponent], // standalone components go in imports
  }).compileComponents();
});
```

### ComponentFixture and detectChanges

```typescript
let fixture: ComponentFixture<MyComponent>;
let component: MyComponent;

beforeEach(() => {
  fixture = TestBed.createComponent(MyComponent);
  component = fixture.componentInstance;
  fixture.detectChanges(); // triggers ngOnInit
});
```

### Testing Signal Components

```typescript
// Signal inputs via componentRef.setInput
it('should render the title from signal input', () => {
  fixture.componentRef.setInput('title', 'Hello World');
  fixture.detectChanges();
  expect(fixture.nativeElement.textContent).toContain('Hello World');
});

// Testing signal values
it('should increment the counter', () => {
  component.increment();
  expect(component.count()).toBe(1);
});
```

### Testing services with HttpClient

```typescript
beforeEach(() => {
  TestBed.configureTestingModule({
    providers: [DataService, provideHttpClient(), provideHttpClientTesting()],
  });
  service = TestBed.inject(DataService);
  httpMock = TestBed.inject(HttpTestingController);
});

afterEach(() => {
  httpMock.verify();
});
```

`provideHttpClient()` goes before `provideHttpClientTesting()`, which overwrites parts of it, and the reverse order can break the tests ([HTTP testing guide](https://angular.dev/guide/http/testing)). `verify()` fails the test when a request is still outstanding.

### Testing Reactive Forms

```typescript
it('should validate required fields', () => {
  component.form.controls['email'].setValue('');
  expect(component.form.valid).toBeFalse();
  
  component.form.controls['email'].setValue('user@example.com');
  expect(component.form.controls['email'].valid).toBeTrue();
});
```

## E2E Testing

- **Playwright** (preferred) or Cypress for end-to-end tests
- Use `data-testid` attributes for stable selectors that survive refactoring
- Test loading, error, and empty states explicitly

```typescript
// Playwright example
test('should display items after loading', async ({ page }) => {
  await page.goto('/items');
  await expect(page.getByTestId('loading-spinner')).toBeVisible();
  await expect(page.getByTestId('item-list')).toBeVisible();
  await expect(page.getByTestId('loading-spinner')).not.toBeVisible();
});

test('should show empty state when no items', async ({ page }) => {
  await page.goto('/items?empty=true');
  await expect(page.getByTestId('empty-state')).toBeVisible();
});
```

## Test-weakening tells

`brain/knowledge/testing.md` ⛔ Hard Rules 2 and 3 govern any change to an existing test, and
`brain/knowledge/review-heuristics.md` §Testing ("Test integrity") lists the moves. In this stack
they look like this, on a line the diff adds or changes:

- Jasmine: `xit` or `xdescribe` (reported pending, never executed), or `pending()` called in a
  spec, which makes its expectation results ignored.
- Jasmine: `fit` or `fdescribe` left in. When anything is focused, only the focused specs run.
- Jest: `test.skip` / `it.skip` / `xit` / `xtest`, `describe.skip` / `xdescribe`, `test.only` /
  `fit`, `describe.only` / `fdescribe`, `test.todo` replacing a test that had a body, or
  `test.failing`.
- Jest command or config: `-t` / `--testNamePattern`, `testPathIgnorePatterns`,
  `--passWithNoTests`, `-u` / `--updateSnapshot`, `jest.retryTimes`, a lower `coverageThreshold`,
  or a new `coveragePathIgnorePatterns` entry.
- Playwright: `test.skip`, `test.fixme`, `test.fail` (the test passes only if it fails),
  `test.slow` (triples the timeout), `test.only`, and the `test.describe.skip` / `.fixme` /
  `.only` forms.
- Playwright command or config: `--grep` / `grep`, `--grep-invert` / `grepInvert`,
  `testIgnore`, `--retries` / `retries`, `-u` / `--update-snapshots`, `--pass-with-no-tests`, or
  `forbidOnly` turned off.

Each is a ledger entry with a disposition and a ground, or it doesn't happen. Reference:
Jasmine's [global API](https://jasmine.github.io/api/edge/global); Jest's
[globals](https://jestjs.io/docs/api), [CLI](https://jestjs.io/docs/cli),
[configuration](https://jestjs.io/docs/configuration), and
[`jest.retryTimes`](https://jestjs.io/docs/jest-object); Playwright's
[annotations](https://playwright.dev/docs/test-annotations),
[CLI](https://playwright.dev/docs/test-cli), and
[TestConfig](https://playwright.dev/docs/api/class-testconfig).

## Key Principles

- Always call `fixture.detectChanges()` after setting inputs or triggering changes
- Use `fakeAsync` + `tick` for testing async operations within Angular's zone
- Test component behavior through the template (rendered output), not just class methods
- Test loading, error, and empty states explicitly for every async component
- Prefer `data-testid` for selectors over CSS classes or DOM structure
