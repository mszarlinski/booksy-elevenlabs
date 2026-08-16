# Booksy × ElevenLabs — Voice-First Booking

A voice-first appointment booking backend: a FastAPI service exposing search/booking
endpoints, wired up as tools for an [ElevenLabs](https://elevenlabs.io) Conversational AI
voice agent. This is a learning project, built story-by-story — see
[`docs/BACKLOG.md`](docs/BACKLOG.md) for the full roadmap and
[`docs/adr/`](docs/adr) for the architecture decisions behind it.

## Demo

[Voice-Controlled Bookings with ElevenLabs Integration](https://www.loom.com/share/c306b445140b4f6d956b28416ca0277d)

End-to-end walkthrough: a voice conversation with the ElevenLabs agent, its tool calls
hitting the local FastAPI server through an ngrok tunnel, and the resulting requests
showing up in the Docker container logs in real time.

## How it works

```text
ElevenLabs Agent (voice conversation)
      │  webhook tool calls, over the public internet via ngrok
      ▼
FastAPI (this repo, running in Docker)
      │
      ├─ app/routers/*.py       — HTTP endpoints (services, employees, availability, bookings, businesses)
      ├─ app/repositories/*.py  — in-memory data stores (no database yet — see VBOOK-04)
      └─ app/slots.py           — pure availability/slot-generation logic
```

The agent currently has five **read-only** tools registered (`search_services`,
`search_employees`, `search_available_slots`, `get_booking`, `get_customer_bookings`) —
see [`docs/adr/0001-elevenlabs-tool-layer-architecture.md`](docs/adr/0001-elevenlabs-tool-layer-architecture.md)
for why. Voice-driven booking *creation* is a later story (VBOOK-10).

## Tech stack

- **Python 3.12+**
- **[FastAPI](https://fastapi.tiangolo.com/)** + **Uvicorn** — the web framework and ASGI server serving both the REST API and the ElevenLabs webhook tools
- **[uv](https://docs.astral.sh/uv/)** — dependency management and virtual environments (`pyproject.toml` + `uv.lock`)
- **pytest** + FastAPI's `TestClient` (httpx) — the automated test suite
- **[Docker](https://www.docker.com/) & Docker Compose** — how the app actually runs (`Dockerfile`, `docker-compose.yml`); the image only bundles `app/`, not `tests/` or `scripts/`
- **[ElevenLabs Conversational AI](https://elevenlabs.io/docs/conversational-ai) (Python SDK)** — the voice agent itself; `scripts/create_elevenlabs_agent.py` registers this service's endpoints as its webhook tools
- **[ngrok](https://ngrok.com/)** — tunnels the local Dockerized FastAPI server to a public HTTPS URL, since ElevenLabs' hosted agent calls tools over the public internet and can't reach `localhost`
- **python-dotenv** — loads local secrets/config (`ELEVENLABS_API_KEY`, `API_BASE_URL`) from a gitignored `.env`

## Project structure

```text
app/
  main.py                — FastAPI app, router registration, logging setup
  routers/                — HTTP endpoints: businesses, bookings, services, employees, availability
  repositories/           — in-memory data stores (seeded sample data, no persistence yet)
  slots.py                — pure slot-generation logic (fixed working hours, duration, booking exclusion)
  idempotency.py          — idempotency-key handling shared by booking mutations
scripts/
  create_elevenlabs_agent.py — registers the FastAPI endpoints as ElevenLabs webhook tools
tests/                    — pytest suite (run with `uv run pytest`)
docs/
  BACKLOG.md              — the story-by-story roadmap
  adr/                    — architecture decision records
  backlog/, done/         — individual story files, moved to done/ as they're completed
```

## Getting started

### Run locally

```bash
uv sync
uv run uvicorn app.main:app --reload
```

### Run via Docker (how it's normally run)

```bash
docker compose up --build -d
docker logs -f booksy-elevenlabs-api-1   # tail the running container's logs
```

### Run the tests

```bash
uv run pytest -q
```

## Connecting a voice agent (ElevenLabs)

1. Create an ElevenLabs account and an API key with **Agents** read/write permission
   (shown as "Conversational AI" in older docs/error messages — ElevenLabs renamed the
   product but kept the old name in some API responses).
2. Start the app (`docker compose up --build -d` or `uv run uvicorn ...`).
3. Expose it publicly: `ngrok http 8000`.
4. Copy `.env.example` to `.env` and fill in `ELEVENLABS_API_KEY` and `API_BASE_URL`
   (your ngrok HTTPS URL — `localhost` will not work here).
5. Register the tools and create the agent: `uv run python -m scripts.create_elevenlabs_agent`.
6. Test it in the ElevenLabs dashboard — try the story's original acceptance criteria:
   *"Find me a haircut tomorrow after six."*

Note: the app has no notion of "today" baked in anywhere, and neither does the agent by
default — expect it to guess dates unless you give it that context.

## Project status

This is a learning project, built incrementally per [`docs/BACKLOG.md`](docs/BACKLOG.md).
As of now: FastAPI skeleton, in-memory booking domain, idempotent mutations, and
read-only ElevenLabs tool integration are done. Real persistence (PostgreSQL) and
voice-driven booking creation are upcoming stories — see the backlog for the full plan.

## License

[GNU GPLv3](LICENSE)
