# Angular State Management Examples

Full examples for the patterns summarized in SKILL.md §8. See the selection criteria there to choose a pattern.

## Pattern 1: Signal Service

```typescript
@Injectable({ providedIn: 'root' })
export class UserStore {
  private _user = signal<User | null>(null);
  private _loading = signal(false);
  private _error = signal<string | null>(null);

  readonly user = this._user.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly error = this._error.asReadonly();
  readonly isAuthenticated = computed(() => this._user() !== null);

  async loadUser(id: string) {
    this._loading.set(true);
    this._error.set(null);
    try {
      const user = await fetch(`/api/users/${id}`).then(r => r.json());
      this._user.set(user);
    } catch {
      this._error.set('Failed to load user');
    } finally {
      this._loading.set(false);
    }
  }
}
```

## Pattern 2: NgRx SignalStore

```typescript
import { signalStore, withState, withMethods, withComputed, patchState } from '@ngrx/signals';

export const ProductStore = signalStore(
  { providedIn: 'root' },
  withState({ products: [] as Product[], loading: false, filter: '' }),
  withComputed(store => ({
    filteredProducts: computed(() => {
      const f = store.filter().toLowerCase();
      return store.products().filter(p => p.name.toLowerCase().includes(f));
    }),
  })),
  withMethods((store, productService = inject(ProductService)) => ({
    async loadProducts() {
      patchState(store, { loading: true });
      try {
        const products = await productService.getAll();
        patchState(store, { products, loading: false });
      } catch {
        patchState(store, { loading: false });
      }
    },
    setFilter(filter: string) { patchState(store, { filter }); },
  })),
);
```

## Pattern 3: NgRx Store (Global)

```typescript
// Actions
export const UserActions = createActionGroup({
  source: 'User',
  events: {
    'Load User': props<{ userId: string }>(),
    'Load User Success': props<{ user: User }>(),
    'Load User Failure': props<{ error: string }>(),
    'Logout': emptyProps(),
  },
});

// Reducer
export const userReducer = createReducer(
  initialState,
  on(UserActions.loadUser, state => ({ ...state, loading: true, error: null })),
  on(UserActions.loadUserSuccess, (state, { user }) => ({ ...state, user, loading: false })),
  on(UserActions.loadUserFailure, (state, { error }) => ({ ...state, loading: false, error })),
  on(UserActions.logout, () => initialState),
);

// Effects
@Injectable()
export class UserEffects {
  private actions$ = inject(Actions);
  private userService = inject(UserService);

  loadUser$ = createEffect(() =>
    this.actions$.pipe(
      ofType(UserActions.loadUser),
      switchMap(({ userId }) =>
        this.userService.getUser(userId).pipe(
          map(user => UserActions.loadUserSuccess({ user })),
          catchError(error => of(UserActions.loadUserFailure({ error: error.message }))),
        ),
      ),
    ),
  );
}

// Component usage with selectSignal
export class HeaderComponent {
  private store = inject(Store);
  user = this.store.selectSignal(selectUser);
}
```

## Bridging Signals and RxJS

```typescript
import { toSignal, toObservable } from '@angular/core/rxjs-interop';

// Observable -> Signal
userId = toSignal(this.route.params.pipe(map(p => p['id'])), { initialValue: '' });

// Signal -> Observable
filter$ = toObservable(this.filter);
filteredData$ = this.filter$.pipe(
  debounceTime(300),
  switchMap(f => this.http.get(`/api/data?q=${f}`)),
);
```
