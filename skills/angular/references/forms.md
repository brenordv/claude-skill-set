# Angular Reactive Forms Example

Full reactive form component referenced from SKILL.md §9.

```typescript
@Component({
  standalone: true,
  imports: [ReactiveFormsModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <div class="form-field">
        <label for="name">Name</label>
        <input id="name" formControlName="name" />
        @if (isFieldInvalid('name')) {
          <span class="error">{{ getFieldError('name') }}</span>
        }
      </div>
      <div class="form-field">
        <label for="email">Email</label>
        <input id="email" type="email" formControlName="email" />
        @if (isFieldInvalid('email')) {
          <span class="error">{{ getFieldError('email') }}</span>
        }
      </div>
      <button type="submit" [disabled]="form.invalid || submitting()">
        @if (submitting()) { Saving... } @else { Submit }
      </button>
    </form>
  `,
})
export class UserFormComponent {
  private fb = inject(FormBuilder);
  submitting = signal(false);

  form = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
  });

  isFieldInvalid(field: string): boolean {
    const c = this.form.get(field);
    return c ? c.invalid && c.touched : false;
  }

  getFieldError(field: string): string {
    const c = this.form.get(field);
    if (c?.hasError('required')) return 'Required';
    if (c?.hasError('email')) return 'Invalid email';
    if (c?.hasError('minlength')) return 'Too short';
    return '';
  }

  async onSubmit() {
    if (this.form.invalid) return;
    this.submitting.set(true);
    try {
      await this.service.submit(this.form.value);
    } catch {
      this.toast.error('Submission failed');
    } finally {
      this.submitting.set(false);
    }
  }
}
```
