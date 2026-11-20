# Failure Modes agent-fill Targets

1. **Temporal confabulation** — confident numbers/dates for data that
   cannot exist yet. Fixed by the Step 2 gate.
2. **Temporal deflection** — answering a broader/older question instead
   of the one asked, without saying so. Fixed by Step 5 provenance
   (flags granularity/period mismatch).
3. **RAG recency illusion** — retrieving the most semantically similar
   doc regardless of age; conflating access date with data date. Fixed
   by Step 3 (three distinct dates) and Step 4 (staleness score).
4. **Agentic temporal drift** — multi-step pipelines mixing data of
   different vintage with no reconciliation. Fixed by Step 5 (per-claim
   dating + conflict flagging).
5. **Block-time mismatch** — treating on-chain state as calendar-current.
   Fixed by stamping all on-chain data with block number (Step 3/4).
