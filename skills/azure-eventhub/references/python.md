# Azure Event Hubs: Python SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the Python code.

## Installation

```bash
pip install azure-eventhub azure-identity azure-eventhub-checkpointstoreblob
```

## Authentication

```python
from azure.identity import DefaultAzureCredential
from azure.eventhub import EventHubProducerClient

producer = EventHubProducerClient(
    fully_qualified_namespace="<namespace>.servicebus.windows.net",
    eventhub_name="my-eventhub",
    credential=DefaultAzureCredential()
)
```

## Producer: Batch Send

```python
with producer:
    batch = producer.create_batch()
    for msg in messages:
        try:
            batch.add(EventData(msg))
        except ValueError:
            producer.send_batch(batch)
            batch = producer.create_batch()
            batch.add(EventData(msg))
    producer.send_batch(batch)
```

## Consumer: Production with Checkpointing

`EventHubConsumerClient` + `BlobCheckpointStore`:
```python
import logging
import threading

from azure.eventhub import EventData, EventHubConsumerClient, PartitionContext
from azure.eventhub.extensions.checkpointstoreblob import BlobCheckpointStore

logger = logging.getLogger(__name__)
stop_requested = threading.Event()

checkpoint_store = BlobCheckpointStore(
    blob_account_url="https://<account>.blob.core.windows.net",
    container_name="checkpoints", credential=DefaultAzureCredential())

consumer = EventHubConsumerClient(
    fully_qualified_namespace=ns, eventhub_name=hub,
    consumer_group="$Default", credential=DefaultAzureCredential(),
    checkpoint_store=checkpoint_store)


def on_event(partition_context: PartitionContext, event: EventData | None) -> None:
    """Handle one event; park it on failure, then checkpoint."""
    if event is None or stop_requested.is_set():
        return

    try:
        handle_event(event)
    except Exception:
        park_error: Exception | None = None
        try:
            parked = dead_letter_store.try_park(event)
        except Exception as error:
            park_error = error
            parked = False
        if not parked:
            logger.critical(
                "Parking failed, stopping. Partition: [%s], SequenceNumber: [%s]",
                partition_context.partition_id, event.sequence_number,
                exc_info=park_error or True)
            stop_requested.set()
            return

        logger.exception(
            "Parked event. Partition: [%s], SequenceNumber: [%s]",
            partition_context.partition_id, event.sequence_number)

    partition_context.update_checkpoint(event)


def on_error(partition_context: PartitionContext | None, error: Exception) -> None:
    """Log an error the consumer reports, one raised from on_event included."""
    partition_id = (
        partition_context.partition_id if partition_context is not None else "")
    logger.error("Receive error. Partition: [%s]", partition_id, exc_info=error)


worker = threading.Thread(
    target=consumer.receive, kwargs={"on_event": on_event, "on_error": on_error})
worker.start()
try:
    while not stop_requested.wait(timeout=1.0):
        pass
finally:
    consumer.close()
    worker.join()
```

An exception from `on_event` isn't retried; the consumer passes it to `on_error`, closes the
partition and releases it, and a later load-balancing pass (default 30 s) resumes it from the last
checkpoint, so a poison event loops; the handler catches its own. `receive` blocks, so it runs on a
worker thread and the main thread calls `close()`, as the SDK's own example does; the host's
shutdown sets the same `stop_requested`, and `try`/`finally` closes the consumer on Ctrl+C too,
since a non-daemon worker keeps the process alive. The main thread waits in one-second steps
because lock waits on Windows can't be interrupted by a signal before Python 3.14
([threading](https://docs.python.org/3/library/threading.html)), so a plain `wait()` there would
never see Ctrl+C. A park that raises counts as a failed park: the critical line carries its
traceback, chained to the handler's, so the failure is logged once. `on_error` also receives an
exception raised from `on_event`, such as a failed `update_checkpoint`, and logs at error, since an
error that persists (a missing role, a revoked identity) means nothing is consumed.
