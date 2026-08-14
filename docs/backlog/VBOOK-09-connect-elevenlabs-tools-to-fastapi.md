# VBOOK-09 — Connect ElevenLabs tools to FastAPI

**Priority:** P0
**Goal:** Learn ElevenLabs tool/function calling.

## Description

Allow the voice agent to query the booking backend.

Initially expose **read-only tools**.

## Tools

```text
search_services()
search_employees()
search_available_slots()
get_booking()
get_customer_bookings()
```

## TODO

* [ ] Learn ElevenLabs tool definitions
* [ ] Define JSON schemas for tool parameters
* [ ] Create FastAPI endpoints usable by ElevenLabs
* [ ] Connect `search_available_slots`
* [ ] Log incoming tool requests
* [ ] Log tool responses
* [ ] Handle malformed arguments
* [ ] Handle backend errors
* [ ] Handle empty search results
* [ ] Ensure tool responses contain concise structured data
* [ ] Experiment with tool descriptions to see how they affect agent behavior

## Learning objectives

Understand the boundary:

```text
LLM reasoning
      ↓
ElevenLabs tool invocation
      ↓
FastAPI
      ↓
domain logic
      ↓
PostgreSQL
```

## Acceptance criteria

You can say:

> Find me a haircut tomorrow after six.

and the agent queries your real FastAPI backend before responding.
