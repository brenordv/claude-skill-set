# Azure Event Hubs: Rust SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the Rust code.

## Installation

```sh
cargo add azure_messaging_eventhubs azure_identity
# Production consumer (below): the blob checkpoint store 0.9 requires azure_messaging_eventhubs ^0.15
cargo add azure_messaging_eventhubs@0.15 azure_messaging_eventhubs_checkpointstore_blob@0.9 azure_storage_blob azure_core futures tokio-util anyhow tracing tracing-subscriber
cargo add tokio --features macros,rt-multi-thread
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

`DeveloperToolsCredential` authenticates through developer tools such as the Azure CLI
([docs](https://docs.rs/azure_identity/1.0.0/azure_identity/struct.DeveloperToolsCredential.html)),
so it's for local development. A deployed app uses its own identity, as the production consumer
below does with `ManagedIdentityCredential`
([docs](https://docs.rs/azure_identity/1.0.0/azure_identity/struct.ManagedIdentityCredential.html)).

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

`EventProcessor` + `BlobCheckpointStore`:
```rust
use anyhow::Context;
use azure_core::http::Url;
use azure_identity::ManagedIdentityCredential;
use azure_messaging_eventhubs::{
    error::ErrorKind, processor::PartitionClient, ConsumerClient, EventProcessor,
};
use azure_messaging_eventhubs_checkpointstore_blob::BlobCheckpointStore;
use azure_storage_blob::BlobServiceClient;
use futures::StreamExt;
use tokio::task::JoinSet;
use tokio_util::sync::CancellationToken;
use tracing::error;

use std::{pin::pin, sync::Arc};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::try_init()
        .map_err(|err| anyhow::anyhow!(err).context("installing the tracing subscriber"))?;

    // `dead_letters` is an `Arc<DeadLetterStore>` that holds parked events.
    let credential = ManagedIdentityCredential::new(None)?;
    let blobs = BlobServiceClient::new(
        Url::parse("https://<account>.blob.core.windows.net/")?,
        Some(credential.clone()),
        None,
    )?;
    let checkpoint_store = BlobCheckpointStore::new(blobs.blob_container_client("checkpoints"));
    let consumer = ConsumerClient::builder()
        .open(
            "<namespace>.servicebus.windows.net",
            "<event-hub-name>".to_string(),
            credential.clone(),
        )
        .await?;
    let processor = EventProcessor::builder()
        .build(consumer, checkpoint_store)
        .await
        .context("building the processor")?;

    let stop = CancellationToken::new();
    let mut partitions = JoinSet::new();
    let mut run = pin!(processor.run());
    let run_result = loop {
        tokio::select! {
            biased;
            result = &mut run => break result,
            () = stop.cancelled() => {
                processor.shutdown().await.context("shutting down the processor")?;
                break run.await;
            }
            next = processor.next_partition_client() => {
                let partition = next.context("acquiring a partition")?;
                let (dead_letters, stop) = (Arc::clone(&dead_letters), stop.clone());
                partitions.spawn(async move {
                    let result = process_partition(&partition, &dead_letters, &stop).await;
                    if result.is_err() {
                        stop.cancel();
                    }
                    result
                });
            }
        }
    };
    stop.cancel();
    while let Some(finished) = partitions.join_next().await {
        finished.context("joining a partition task")??;
    }
    run_result.context("running the processor")?;
    Ok(())
}

async fn process_partition(
    partition: &PartitionClient,
    dead_letters: &DeadLetterStore,
    stop: &CancellationToken,
) -> anyhow::Result<()> {
    let partition_id = partition.get_partition_id();
    let mut events = pin!(partition.stream_events().take_until(stop.cancelled()));
    while let Some(received) = events.next().await {
        let event = match received {
            Ok(event) => event,
            Err(err) if matches!(err.kind, ErrorKind::ConsumerDisconnected(_)) => return Ok(()),
            Err(err) => {
                return Err(err)
                    .with_context(|| format!("receiving an event on partition {partition_id}"))
            }
        };
        let sequence_number = event.sequence_number();
        if let Err(err) = handle_event(&event).await {
            if let Err(park_err) = dead_letters.park(&event).await {
                error!(partition_id, ?sequence_number, park_failed = true, error = ?err,
                    "parking failed, stopping");
                return Err(park_err).with_context(|| {
                    format!("parking event {sequence_number:?} on partition {partition_id}")
                });
            }
            error!(partition_id, ?sequence_number, error = ?err, "parked event");
        }
        partition.update_checkpoint(&event).await.with_context(|| {
            format!("checkpointing event {sequence_number:?} on partition {partition_id}")
        })?;
    }
    Ok(())
}
```

The processor is pull-based: `run` balances partitions against the store, `next_partition_client`
hands out each claimed one, and the loop reading `stream_events()` decides when `update_checkpoint`
runs, so no SDK callback sees a handler failure. The host loop polls `run` too, so a processor that
stops on its own is reported when it stops. A failed event is parked, logged at error, and
checkpointed.

A park failure skips the checkpoint, logs once with `park_failed = true` (`tracing` has no level
above `ERROR`, so that field is what an alert keys on), and returns the park error, which the spawn
wrapper turns into a stop: `take_until` ends every stream at the next event boundary and the host
returns the first failure, so the process exits non-zero. Any receive or checkpoint error stops the
host the same way, which is the safe choice. `ConsumerDisconnected` means the partition was
reassigned or the broker disconnected the receiver, so that task ends cleanly and the processor
hands the partition out again through `next_partition_client`. The host stops by cancelling `stop`,
and its own shutdown signal cancels the same token; `shutdown()` alone leaves the partition streams
open. `shutdown()` only clears the flag `run` sets when it starts, and `run` reads it after each
load-balancing sleep (30 seconds by default), so the stop can take that long to land
([processor source](https://docs.rs/azure_messaging_eventhubs/0.15.0/src/azure_messaging_eventhubs/event_processor/processor.rs.html)).
`biased;` polls `run` before the stop branch, so a stop that arrives before `run`'s first poll
can't have its flag set back afterward. The subscriber goes in first, since `tracing` drops every
event, the `park_failed` one included, until a subscriber is installed.

The 0.15 pin is there because the store 0.9.0 requires `^0.15.0`
([crate page](https://docs.rs/crate/azure_messaging_eventhubs_checkpointstore_blob/0.9.0)), and the
construction follows the store's
[0.9.0 example](https://docs.rs/azure_messaging_eventhubs_checkpointstore_blob/0.9.0/azure_messaging_eventhubs_checkpointstore_blob/).
