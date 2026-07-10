# Angular SSR: TransferState Service

Full TransferState service referenced from SKILL.md §7. Use it to avoid refetching on the client data already fetched during server rendering.

```typescript
@Injectable({ providedIn: 'root' })
export class DataService {
  private http = inject(HttpClient);
  private transferState = inject(TransferState);
  private platformId = inject(PLATFORM_ID);

  getData(key: string): Observable<Data> {
    const stateKey = makeStateKey<Data>(key);
    if (isPlatformBrowser(this.platformId)) {
      const cached = this.transferState.get(stateKey, null);
      if (cached) {
        this.transferState.remove(stateKey);
        return of(cached);
      }
    }
    return this.http.get<Data>(`/api/${key}`).pipe(
      tap(data => {
        if (isPlatformServer(this.platformId)) {
          this.transferState.set(stateKey, data);
        }
      }),
    );
  }
}
```
