# React Data Fetching Examples

Full examples referenced from SKILL.md §6. The query-key factory and Suspense fetch hook stay in the skill body; the optimistic mutation and API service layer live here.

## Mutations with Optimistic Updates

```typescript
function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateUser,
    onMutate: async (newUser) => {
      await queryClient.cancelQueries({ queryKey: userKeys.detail(newUser.id) });
      const previous = queryClient.getQueryData(userKeys.detail(newUser.id));
      queryClient.setQueryData(userKeys.detail(newUser.id), newUser);
      return { previous };
    },
    onError: (_err, newUser, context) => {
      queryClient.setQueryData(userKeys.detail(newUser.id), context?.previous);
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: userKeys.detail(variables.id) });
    },
  });
}
```

## API Service Layer

```typescript
// features/users/api/userApi.ts
import apiClient from '@/lib/apiClient';
import type { User, CreateUserPayload } from '../types';

export const userApi = {
  getUser: async (id: string): Promise<User> => {
    const { data } = await apiClient.get(`/users/${id}`);
    return data;
  },
  createUser: async (payload: CreateUserPayload): Promise<User> => {
    const { data } = await apiClient.post('/users', payload);
    return data;
  },
};
```
