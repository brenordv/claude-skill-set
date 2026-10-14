# Azure Cosmos DB: Python SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the Python code.

## Installation

```bash
pip install azure-cosmos azure-identity
```

## Authentication

```python
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

# Production (AAD/RBAC)
client = CosmosClient(url=os.environ["COSMOS_ENDPOINT"], credential=DefaultAzureCredential())

# Emulator (local dev only)
client = CosmosClient(url="https://localhost:8081", credential=EMULATOR_KEY, connection_verify=False)
```

### Python Async
```python
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

async with CosmosClient(endpoint, credential=DefaultAzureCredential()) as client:
    database = client.get_database_client("mydb")
    container = database.get_container_client("mycontainer")
```

## Client Configuration

Keep one `CosmosClient` per application lifetime; initialization is heavy and a shared instance
reuses connections. The Python SDK is gateway-only (`connection_mode` supports only `'Gateway'`).
Configure through constructor keyword arguments; never build an
`azure.cosmos.documents.ConnectionPolicy` by hand (legacy v3 surface).
([CosmosClient API](https://learn.microsoft.com/python/api/azure-cosmos/azure.cosmos.cosmosclient))

```python
client = CosmosClient(
    url,
    credential=DefaultAzureCredential(),
    connection_timeout=10,                      # seconds
    retry_total=9,
    retry_backoff_max=30,
    preferred_locations=["West US 2", "East US 2"],
    enable_diagnostics_logging=True,            # pair with logger=
    logger=logger,
)
```

`connection_verify=False` is for the local emulator's self-signed certificate only; never disable
TLS verification against a real account.

The async client (`azure.cosmos.aio`) takes the same kwargs. Prefer `async with CosmosClient(...)`;
outside a context manager you must call `await client.close()` yourself. The async client has no
`enable_cross_partition_query` flag; queries without a partition key fan out by default.

### Throttling and RU Visibility

The SDK retries 429s internally up to `retry_total`, and those retries are silent: a
`CosmosHttpResponseError` with status 429 means retries were already exhausted. When raising retry
limits, also watch the 429 rate in Azure Monitor, or slowdowns become invisible. Responses carry
their RU cost in the `x-ms-request-charge` header (per page for queries, so sum across pages); log
it together with the status code when handling errors.

## CRUD Operations

### Create
```python
# Python
created = container.create_item(body={"id": "1", "pk": "A", "name": "Item"})
```

### Read (Point Read - most efficient, 1 RU for 1KB)
```python
# Python - requires id AND partition key
item = container.read_item(item="1", partition_key="A")
```

### Upsert (Idempotent - prefer over create for retry safety)
```python
# Python
result = container.upsert_item(body=item)
```

### Delete
```python
container.delete_item(item="1", partition_key="A")
```

## Queries

### Parameterized Queries (ALWAYS use parameters - never string concatenation)
```python
# Python
query = "SELECT * FROM c WHERE c.category = @category AND c.price < @max"
items = container.query_items(
    query=query,
    parameters=[
        {"name": "@category", "value": "electronics"},
        {"name": "@max", "value": 500}
    ],
    partition_key="electronics"  # Single-partition query (efficient)
)
```

### Cross-Partition Queries
```python
# Python
items = container.query_items(query=query, parameters=params, enable_cross_partition_query=True)
```

## Error Handling

```python
# Python
from azure.cosmos.exceptions import CosmosHttpResponseError
try:
    item = container.read_item(item="x", partition_key="pk")
except CosmosHttpResponseError as e:
    if e.status_code == 404:
        return None
    elif e.status_code == 429:
        retry_after = e.headers.get("x-ms-retry-after-ms")
    raise
```

## Service Layer Pattern (FastAPI)

```python
class ItemService:
    def __init__(self):
        self._container = None

    async def _get_container(self):
        if self._container is None:
            self._container = await get_container()
        return self._container

    async def get_by_id(self, item_id: str, partition_key: str) -> Item | None:
        container = await self._get_container()
        if container is None:
            return None  # Graceful degradation
        try:
            doc = container.read_item(item=item_id, partition_key=partition_key)
            return self._doc_to_model(doc)
        except CosmosHttpResponseError as e:
            if e.status_code == 404:
                return None
            raise
```

## Pydantic Model Pattern

Five-tier model hierarchy for clean API design:
```python
class ItemBase(BaseModel):           # Shared fields
    name: str = Field(..., min_length=1, max_length=200)

class ItemCreate(ItemBase):          # Creation request
    partition_key: str = Field(..., alias="partitionKey")

class ItemUpdate(BaseModel):         # Partial updates (all Optional)
    name: Optional[str] = Field(None, min_length=1)

class Item(ItemBase):                # API response
    id: str
    created_at: datetime = Field(..., alias="createdAt")

class ItemInDB(Item):                # Internal with docType
    doc_type: str = "item"
```

## Testing (pytest)

```python
@pytest.fixture
def mock_cosmos_container(mocker):
    container = mocker.MagicMock()
    mocker.patch("app.db.cosmos.get_container", return_value=container)
    return container

@pytest.mark.asyncio
async def test_get_item_returns_none_when_not_found(mock_cosmos_container):
    mock_cosmos_container.read_item.side_effect = CosmosHttpResponseError(
        status_code=404, message="Not found"
    )
    result = await service.get_by_id("missing", "pk")
    assert result is None
```
