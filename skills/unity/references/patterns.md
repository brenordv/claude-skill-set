# Unity Reference Patterns

Full implementations referenced from `SKILL.md`. These are load-on-demand; the SKILL body keeps the one-line rules and links here for the long snippets.

## Performance-Critical Coding Rules

Code demonstrations for the five rules stated inline in SKILL.md §2.

```csharp
// RULE 1: Cache component references; never GetComponent in Update
public class PlayerController : MonoBehaviour
{
    // Cache in Awake, not Start (Awake runs before Start)
    private Rigidbody _rb;
    private Animator _animator;

    private void Awake()
    {
        _rb = GetComponent<Rigidbody>();
        _animator = GetComponent<Animator>();
    }
}

// RULE 2: Avoid allocations in hot paths
public class BulletSpawner : MonoBehaviour
{
    // BAD: allocates every frame
    void Update()
    {
        var enemies = FindObjectsOfType<Enemy>(); // GC nightmare
        var msg = $"Enemies: {enemies.Length}";    // string alloc
        var list = new List<int>();                // list alloc
    }

    // GOOD: pre-allocate, reuse, cache
    private readonly List<Enemy> _enemyCache = new(64);
    private readonly StringBuilder _sb = new(128);

    void Update()
    {
        // Use cached collections, clear instead of reallocate
        _enemyCache.Clear();
        FindActiveEnemies(_enemyCache);
    }
}

// RULE 3: Use struct over class for small, short-lived data
public readonly struct DamageEvent
{
    public readonly int Damage;
    public readonly Vector3 HitPoint;
    public readonly DamageType Type;

    public DamageEvent(int damage, Vector3 hitPoint, DamageType type)
    {
        Damage = damage;
        HitPoint = hitPoint;
        Type = type;
    }
}

// RULE 4: Prefer CompareTag over string comparison
if (other.CompareTag("Player")) { } // Fast: no GC
// if (other.tag == "Player") { }   // Slow: allocates string

// RULE 5: Use NonAlloc physics queries
private readonly RaycastHit[] _hitBuffer = new RaycastHit[16];

void CheckHits()
{
    int count = Physics.RaycastNonAlloc(transform.position, transform.forward, _hitBuffer, 100f);
    for (int i = 0; i < count; i++)
    {
        ProcessHit(_hitBuffer[i]);
    }
}
```

## Event Channels (ScriptableObject)

One event-channel class per payload type: drag-and-drop in the inspector, no hard references. Below is the void (no-payload) channel; **repeat the same class per payload type** (e.g. `IntEventSO` with `Raise(int value)` and `System.Action<int>` listeners, `FloatEventSO`, etc.).

```csharp
// Event channel: drag-and-drop in inspector, no hard references
[CreateAssetMenu(menuName = "Events/Void Event")]
public class VoidEventSO : ScriptableObject
{
    private readonly List<System.Action> _listeners = new();

    public void Raise()
    {
        for (int i = _listeners.Count - 1; i >= 0; i--)
            _listeners[i]?.Invoke();
    }

    public void Register(System.Action listener) => _listeners.Add(listener);
    public void Unregister(System.Action listener) => _listeners.Remove(listener);
}
```

Usage in components:

```csharp
public class Health : MonoBehaviour
{
    [SerializeField] private IntEventSO _onHealthChanged;
    [SerializeField] private VoidEventSO _onDeath;

    private int _current;

    public void Subtract(int amount)
    {
        _current = Mathf.Max(0, _current - amount);
        _onHealthChanged?.Raise(_current);
        if (_current <= 0) _onDeath?.Raise();
    }
}
```

## Object Pool

Full pool implementation (SKILL.md §4). Pool reusable objects instead of Instantiate/Destroy in gameplay.

```csharp
public class ObjectPool : MonoBehaviour
{
    [SerializeField] private GameObject _prefab;
    [SerializeField] private int _initialSize = 20;

    private readonly Queue<GameObject> _pool = new();

    private void Awake()
    {
        for (int i = 0; i < _initialSize; i++)
            AddToPool(CreateInstance());
    }

    public GameObject Get(Vector3 position, Quaternion rotation)
    {
        var obj = _pool.Count > 0 ? _pool.Dequeue() : CreateInstance();
        obj.transform.SetPositionAndRotation(position, rotation);
        obj.SetActive(true);
        return obj;
    }

    public void Return(GameObject obj)
    {
        obj.SetActive(false);
        _pool.Enqueue(obj);
    }

    private GameObject CreateInstance()
    {
        var obj = Instantiate(_prefab, transform);
        obj.SetActive(false);
        return obj;
    }
}
```

## UI Toolkit: Runtime UI (UXML / USS)

Full listings for SKILL.md §7. Runtime UI with USS (like CSS) and UXML (like HTML).

```csharp
// UI Toolkit: runtime UI with USS (like CSS) and UXML (like HTML)
public class HealthBarController : MonoBehaviour
{
    [SerializeField] private UIDocument _uiDocument;

    private ProgressBar _healthBar;
    private Label _healthLabel;

    private void OnEnable()
    {
        var root = _uiDocument.rootVisualElement;
        _healthBar = root.Q<ProgressBar>("health-bar");
        _healthLabel = root.Q<Label>("health-label");
    }

    public void UpdateHealth(int current, int max)
    {
        float pct = (float)current / max * 100f;
        _healthBar.value = pct;
        _healthLabel.text = $"{current}/{max}";
    }
}
```

```xml
<!-- HealthBar.uxml -->
<ui:UXML xmlns:ui="UnityEngine.UIElements">
    <ui:VisualElement class="health-container">
        <ui:ProgressBar name="health-bar" />
        <ui:Label name="health-label" text="100/100" />
    </ui:VisualElement>
</ui:UXML>
```

```css
/* HealthBar.uss */
.health-container {
    flex-direction: row;
    align-items: center;
}

#health-bar {
    width: 200px;
    height: 20px;
}

#health-bar .unity-progress-bar__progress {
    background-color: rgb(0, 200, 0);
}
```

## Input System (New Input System)

Full boilerplate for SKILL.md §12. Subscribe in `OnEnable`, unsubscribe in `OnDisable`.

```csharp
using UnityEngine.InputSystem;

public class PlayerInput : MonoBehaviour
{
    private GameInputActions _input;

    private void Awake()
    {
        _input = new GameInputActions();
    }

    private void OnEnable()
    {
        _input.Player.Enable();
        _input.Player.Jump.performed += OnJump;
        _input.Player.Fire.performed += OnFire;
    }

    private void OnDisable()
    {
        _input.Player.Jump.performed -= OnJump;
        _input.Player.Fire.performed -= OnFire;
        _input.Player.Disable();
    }

    private void Update()
    {
        Vector2 move = _input.Player.Move.ReadValue<Vector2>();
        _controller.Move(new Vector3(move.x, 0, move.y) * _speed * Time.deltaTime);
    }

    private void OnJump(InputAction.CallbackContext ctx) => _controller.Jump();
    private void OnFire(InputAction.CallbackContext ctx) => _weaponSystem.Fire();
}
```
