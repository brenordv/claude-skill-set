# React State Management Examples

Full store examples referenced from SKILL.md §5. See the selection criteria and state placement rules there.

## Zustand (Recommended for Client State)

```typescript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set) => ({
        sidebarOpen: true,
        theme: 'light',
        toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
        setTheme: (theme) => set({ theme }),
      }),
      { name: 'ui-storage' }
    )
  )
);

// Selective subscriptions prevent unnecessary re-renders
const theme = useUIStore((state) => state.theme);
```

## Jotai (Atomic State)

```typescript
import { atom } from 'jotai';
import { atomWithStorage } from 'jotai/utils';

export const userAtom = atom<User | null>(null);
export const isAuthenticatedAtom = atom((get) => get(userAtom) !== null); // Derived
export const themeAtom = atomWithStorage<'light' | 'dark'>('theme', 'light'); // Persisted
```
