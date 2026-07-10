# React Forms Example

Full React Hook Form + Zod form referenced from SKILL.md §10.

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
});

type FormData = z.infer<typeof schema>;

function ContactForm() {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    await submitApi(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name')} aria-invalid={!!errors.name} />
      {errors.name && <span role="alert">{errors.name.message}</span>}
      <input {...register('email')} type="email" aria-invalid={!!errors.email} />
      {errors.email && <span role="alert">{errors.email.message}</span>}
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : 'Submit'}
      </button>
    </form>
  );
}
```
