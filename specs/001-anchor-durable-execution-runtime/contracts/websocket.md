# WebSocket contract

**Channels**: `WS /ws/runs/{run_id}` and `WS /ws/fleet` (§8).
**Authority**: `anchor-spec.md` §8, §9 (slow-client row), §13.4; [research.md](../research.md) D-29.

The API holds **one** always-on subscription to a single `anchor:events` firehose (plus
`anchor:fleet`) and demultiplexes by `run_id` in process (research.md D-50). **Redis is a delivery
mechanism and nothing more** — if it is unavailable, these channels stop and the console falls back to
polling, while execution is entirely unaffected. No message on either channel is ever authoritative
about ownership.

**Why one channel rather than per-run.** Per-run channels put subscribe and unsubscribe on the request
path, which introduces a race with a name: a client connects, the API subscribes, and any event
published in between is lost — invisible unless someone notices a gap in `seq`. One always-on
subscription removes that race by construction, so the handshake below only has to handle reconnects.
It also stays correct if the web tier is ever scaled past one instance: every instance sees every event
and routes to its own clients.

## Framing

Every frame is a JSON object with an envelope:

```json
{ "channel": "run:47", "kind": "event", "seq": 128, "sent_at": "2026-07-31T14:02:17.412Z", "data": { } }
```

| Field | Meaning |
|---|---|
| `channel` | `run:{id}` or `fleet` |
| `kind` | `hello` · `event` · `snapshot` · `fleet` · `lag` · `bye` |
| `seq` | For `kind: event`, the run event's sequence number. **Required**, because it is what makes backfill exact rather than approximate — the client can detect its own gap and ask for precisely what it missed. |
| `sent_at` | Server send time, for staleness display |
| `data` | Payload, per `kind` below |

## `WS /ws/runs/{run_id}`

**On connect** the server sends `hello` then one `snapshot`, so a client never renders an empty
timeline while waiting for the next event:

```json
{ "kind": "hello", "data": { "run_id": 47, "last_seq": 126, "deployment_mode": "demonstration" } }
{ "kind": "snapshot", "data": { /* RunTimeline, per openapi.yaml */ } }
```

**Then** one `event` frame per appended event, in sequence order, with `data` being the `RunEvent`
shape. The client applies them to the snapshot; `STEP_SKIPPED_ON_REPLAY`, `WORKER_FENCED`, and
`RUN_CLAIMED` are the three that change the *structure* of the view rather than only its contents.

**Backpressure.** Each client has a bounded outbound queue. A client that exceeds it is closed with
code `1013` and `{"kind":"bye","data":{"reason":"slow_consumer","last_sent_seq":N}}`. The client
reconnects and calls `GET /api/runs/{id}/events?after_seq=N`. The interface states that it fell
behind and recovered — silently papering over a gap would be a dashboard that shows stale data as
live.

**Orphan transitions are pushed, not polled.** When a lease expires with no new claim yet, the server
emits `{"kind":"lag","data":{"orphaned":true,"lease_expired_at":"…"}}` so the interface can start the
countdown immediately. This is the most important two seconds in the product and it must not wait for
a poll interval.

## `WS /ws/fleet`

**On connect**: `hello`, then a `fleet` frame carrying the full worker list. Then a `fleet` frame on
every change — registration, heartbeat, run-count change, death.

```json
{ "kind": "fleet", "data": { "workers": [ /* Worker[] */ ], "degraded": false } }
```

Worker death is observable in two ways and both are sent: the absence of heartbeats (`stale: true`
after the threshold) and, when a kill was requested through the API, an immediate advisory frame so
the fleet card can grey out without waiting for staleness detection. The advisory is a *display*
optimisation; `last_seen_at` in PostgreSQL remains the only thing anyone reasons about.

## Client obligations

1. **Never treat a frame as confirmation of a write.** The log is the record; a frame is a
   notification that the log changed.
2. **Handle `snapshot` arriving after `event` frames** (a reconnect race) by discarding events with
   `seq <= snapshot.last_seq`.
3. **Show staleness.** If no frame and no successful poll has arrived within a threshold, say so on
   screen.
4. **Reconnect with backoff and jitter**, and backfill from `after_seq` rather than refetching the
   whole log.
