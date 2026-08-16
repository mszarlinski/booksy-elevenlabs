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

* [x] Learn ElevenLabs tool definitions
* [x] Define JSON schemas for tool parameters
* [x] Create FastAPI endpoints usable by ElevenLabs
* [x] Connect `search_available_slots`
* [x] Log incoming tool requests
* [x] Log tool responses
* [x] Handle malformed arguments
* [x] Handle backend errors
* [x] Handle empty search results
* [x] Ensure tool responses contain concise structured data
* [ ] Experiment with tool descriptions to see how they affect agent behavior — pending, requires a live agent (see below)

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

**Status note:** the FastAPI side (the actual scope of this story, per
[ADR 0001](../adr/0001-elevenlabs-tool-layer-architecture.md)) is complete and
tested. The acceptance criteria above requires a live ElevenLabs agent, which
has not been created yet — no API key was available while implementing this
story. Moved to `docs/done` because the coding scope is finished and reviewed;
the live-agent verification is tracked as manual follow-up in
`docs/superpowers/specs/2026-08-16-vbook-09-elevenlabs-tools-design.md` and
`docs/superpowers/plans/2026-08-16-vbook-09-elevenlabs-tools.md`.
