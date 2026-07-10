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

### Testing Services with HttpClientTestingModule

```typescript
beforeEach(() => {
  TestBed.configureTestingModule({
    imports: [HttpClientTestingModule],
    providers: [DataService],
  });
  service = TestBed.inject(DataService);
  httpMock = TestBed.inject(HttpTestingController);
});

afterEach(() => {
  httpMock.verify(); // ensure no outstanding requests
});
```

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

## Key Principles

- Always call `fixture.detectChanges()` after setting inputs or triggering changes
- Use `fakeAsync` + `tick` for testing async operations within Angular's zone
- Test component behavior through the template (rendered output), not just class methods
- Test loading, error, and empty states explicitly for every async component
- Prefer `data-testid` for selectors over CSS classes or DOM structure
