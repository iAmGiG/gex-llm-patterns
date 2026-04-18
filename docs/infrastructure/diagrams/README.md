# Technical Diagrams

System-level diagrams for the gex-llm-patterns research pipeline. These document the actual implementation as of April 2026 (post-conclusion snapshot), not aspirational architecture.

Each diagram is authored in Mermaid for source control and GitHub rendering; rendered PNG siblings are included for presentation and dissertation use.

## Diagrams

| # | Diagram | Purpose | Source |
|---|---------|---------|--------|
| 1 | [DB Schema](db_schema.md) ([png](db_schema.png)) | Options chains, daily GEX summary, collection progress, research-cache tables, relationships | [src/cache/sqlite_options_manager.py](../../../src/cache/sqlite_options_manager.py), [src/cache/research_cache.py](../../../src/cache/research_cache.py) |
| 2 | [AutoGen Agent Flow](autogen_flow.md) ([png](autogen_flow.png)) | End-to-end sequence: validation script → agent → tools → LLM → persistence | [src/agents/market_mechanics_agent.py](../../../src/agents/market_mechanics_agent.py), [src/tools/autogen_tools.py](../../../src/tools/autogen_tools.py) |
| 3 | [LLM Integration](llm_integration.md) ([png](llm_integration.png)) | Obfuscation → prompt construction → OpenAI Batch API → structured JSON → validation | [src/llm/autogen_market_mechanics.py](../../../src/llm/autogen_market_mechanics.py), [src/llm/mechanics_prompt_builder.py](../../../src/llm/mechanics_prompt_builder.py) |
| 4 | [Cache Layer](cache_layer.md) ([png](cache_layer.png)) | Cache → API → sample-data fallback chain, quality-gated persistence, invalidation logic | [src/tools/autogen_tools.py](../../../src/tools/autogen_tools.py), [src/cache/research_cache.py](../../../src/cache/research_cache.py) |
| 5 | [Data Pipeline](data_pipeline.md) ([png](data_pipeline.png)) | 8-stage end-to-end: ingestion → storage → GEX → windowing → obfuscation → LLM → validation → paper outputs | All of `src/` + `scripts/validation/paper2/` |

## Audience mapping

| Audience | Primary diagrams |
|----------|------------------|
| Academic readers (reviewers, dissertation committee) | [LLM Integration](llm_integration.md), [Data Pipeline](data_pipeline.md) — these are the research-methodology diagrams |
| Engineering / reproducibility | [DB Schema](db_schema.md), [AutoGen Agent Flow](autogen_flow.md), [Cache Layer](cache_layer.md) — these are the implementation diagrams |
| Presentations | All five, with PNG siblings for slide embedding |

## Rendering

PNGs are generated via `@mermaid-js/mermaid-cli`:

```bash
npx @mermaid-js/mermaid-cli -i autogen_flow.md -o autogen_flow.png -t default -b white
```

Re-render all five in one pass:

```bash
cd docs/infrastructure/diagrams
for f in db_schema autogen_flow llm_integration cache_layer data_pipeline; do
  npx @mermaid-js/mermaid-cli -i "${f}.md" -o "${f}.png" -t default -b white
done
```

Mermaid source in the `.md` files is the authoritative version. If rendering produces different output, update the `.md` — not the `.png`.

---

**Last updated:** April 2026 — final sweep at project conclusion.
