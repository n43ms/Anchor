# Compose topology

`docker-compose.yml`: PostgreSQL 16, Redis 7, a one-shot `migrate` service,
the API, three worker replicas, and the console. `ANCHOR_AUTHORING_EXECUTE=true`
is set **only** here (research.md §31) — every other deployment leaves it
unset and is therefore demonstration mode by default.
