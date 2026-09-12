# Need-aware query rewrite

Query rewriting changes the request representation for one retrieval boundary;
it never changes what the user said or invents a fact.

## Two-step contract

1. Gemini receives the original question, the target type, and **names** of
   available context fields. It returns only a `QueryRewriteProposal`: which
   supplied fields may be useful. It cannot return query text or any value.
2. `QueryRewritePolicy` validates that each requested field is both available
   and allowed for that target, then builds the final query from the original
   text and server-owned values. The original and final forms are retained in
   `RewrittenQuery` for tracing.

The agent never receives a student number, major value, admission year, or
free-text previous conversation in this stage.

## Target rules

| Target | Allowed enrichment | Query text treatment |
| --- | --- | --- |
| Official knowledge RAG | major, admission year, target term | append labelled verified context |
| Academic records | target term only | preserve text; use context as structured metadata |
| Current schedule | current term only | preserve text; use context as structured metadata |
| nDRIMS menu | target service only | append labelled verified context |

An accepted follow-up turn is trace metadata only. Its free-text content is
never injected into a RAG, tool, or embedding query. Low-confidence or
ambiguous references therefore cannot silently broaden a search.

Any invalid target, missing field, unvalidated follow-up, or attempt to add the
authenticated student identity raises a policy error. The caller must use the
original question or issue clarification; it must not guess a replacement.
