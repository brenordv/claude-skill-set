# Azure Event Hubs: Rust SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the Rust code.

## Installation

```sh
cargo add azure_messaging_eventhubs azure_identity
# Optional: cargo add azure_messaging_eventhubs_checkpointstore_blob
```

## Authentication

```rust
use azure_identity::DeveloperToolsCredential;
use azure_messaging_eventhubs::ProducerClient;

let credential = DeveloperToolsCredential::new(None)?;
let producer = ProducerClient::builder()
    .open("<namespace>.servicebus.windows.net", "eventhub-name", credential.clone())
    .await?;
```

## Producer: Batch Send

```rust
let batch = producer.create_batch(None).await?;
batch.try_add_event_data(b"event data".to_vec(), None)?;
producer.send_batch(batch, None).await?;
```

## Consumer: Production with Checkpointing

```rust
let consumer = ConsumerClient::builder()
    .open("<namespace>.servicebus.windows.net", "hub", credential.clone()).await?;
let receiver = consumer.open_partition_receiver("0", None).await?;
let events = receiver.receive_events(100, None).await?;
for event in events {
    println!("Event: {:?}", event.body());
}
```
