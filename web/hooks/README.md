# Stream hooks — client obligations

Per `contracts/websocket.md`:

1. **Never treat a frame as confirmation of a write.** The log in PostgreSQL is the record; a
   WebSocket frame is a notification that the log changed, nothing more. No hook here ever
   short-circuits a mutation's own request/response cycle based on a frame arriving.
2. **A reconnect can deliver `snapshot` after `event` frames.** `useRunStream` tracks the highest
   applied `seq` and discards any event at or below it before applying.
3. **Staleness is surfaced, never hidden.** Both stream hooks and the polling fallback expose a
   `stale` flag once no frame/poll has landed within the threshold; components must render it
   rather than silently keep showing the last-known state as if it were live.
4. **Reconnect with backoff and jitter**, and backfill via `after_seq` — never refetch the whole
   log. `useRunStream`'s `bye` handling with `reason: "slow_consumer"` is the concrete case: it
   calls `GET /api/runs/{id}/events?after_seq=N`, not a full timeline refetch.
