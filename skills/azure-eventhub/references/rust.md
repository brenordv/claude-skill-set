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
if !batch.try_add_event_data(b"event data".to_vec(), None)? {
    anyhow::bail!("event exceeds the maximum batch size");
}
producer.send_batch(batch, None).await?;
```

`try_add_event_data` returns `Ok(false)` when the event doesn't fit, so the bool needs checking;
`?` alone drops it
([EventDataBatch](https://docs.rs/azure_messaging_eventhubs/latest/azure_messaging_eventhubs/struct.EventDataBatch.html)).

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
