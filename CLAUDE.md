# Anchor

**Read `.specify/memory/constitution.md` before doing anything in this repository.** It governs
every task here — the eight durability invariants, the architecture and database rules, the fixed
toolchain, the build phases, the workflow, and the definition of done. It is the absorbed and
superseding version of the engineering standard formerly kept in `engineers/anchorengineer.md`.

`anchor-spec.md` is the source of truth for intent. The constitution is the source of truth for
conduct, and it states which spec sections govern when the spec disagrees with itself.

Three rules that apply before you have finished reading it:

1. **Correctness beats completeness** — never trade a guarantee for a feature.
2. **Failing loudly beats failing silently** — never keep running with corrupt state.
3. **Stop and raise** any change that could weaken an invariant, even if it was requested.
