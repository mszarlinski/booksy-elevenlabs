# VBOOK-12 — Learn asyncio through parallel availability search

**Priority:** P1
**Goal:** Deliberately practice Python asynchronous programming rather than merely using `async` syntax.

## Description

Simulate multiple providers and search their availability concurrently.

## TODO

* [ ] Create 3 simulated provider integrations
* [ ] Add artificial network latency
* [ ] Call them sequentially and measure latency
* [ ] Replace sequential execution with `asyncio.gather`
* [ ] Repeat using `asyncio.TaskGroup`
* [ ] Add per-provider timeouts
* [ ] Handle partial failures
* [ ] Handle cancellation
* [ ] Learn `asyncio.to_thread`
* [ ] Experiment with blocking code inside an async handler
* [ ] Observe its impact on application throughput
* [ ] Document when thread pools are necessary

## Learning objectives

Understand:

```text
coroutine
task
event loop
await
TaskGroup
timeout
cancellation
thread pool
```

## Acceptance criteria

Availability is aggregated concurrently and one slow provider doesn't block the entire request.
