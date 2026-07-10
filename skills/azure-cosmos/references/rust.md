# Azure Cosmos DB: Rust SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the Rust code.

## Installation

```sh
cargo add azure_data_cosmos azure_identity
```
Enable key auth with `--features key_auth` if needed.

## Authentication

```rust
use azure_identity::DeveloperToolsCredential;
use azure_data_cosmos::CosmosClient;

let credential = DeveloperToolsCredential::new(None)?;
let client = CosmosClient::new(endpoint, credential.clone(), None)?;
```

## CRUD Operations

### Create
```rust
// Rust
container.create_item("partition_value", item, None).await?;
```

### Read (Point Read - most efficient, 1 RU for 1KB)
```rust
// Rust
let item: Item = container.read_item("A", "1", None).await?.into_model()?;
```

### Patch (Partial Update - lower RU than full replace)
```rust
// Rust
let patch = PatchDocument::default()
    .with_add("/newField", "value")?
    .with_remove("/oldField")?;
container.patch_item("A", "1", patch, None).await?;
```
