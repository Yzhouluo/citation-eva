# Citation Evaluation System — Design Spec

**Date**: 2026-04-26
**Status**: Confirmed

---

## 1. Background & Goals

### Primary Goal
Build a systematic, scientific citation evaluation system (`citation-eva`) that, given a GROBID-processed academic paper, evaluates every citation along multiple semantic and structural dimensions.

### Secondary Goal
The per-citation evaluation scores can serve as edge weights in the JournalRank citation network, enabling weighted SpringRank computation (replacing raw citation counts with quality-adjusted counts).

### Existing Assets to Reuse
- **GROBID pipeline** (`pdf2json/`): produces `paper.json` with `body_text[].refs` (inline citation markers with character offsets and section labels) and `references[]` (bibliographic metadata).
- **Large citation database**: the same database underpinning JournalRank; provides citation network data.
- **JournalRank results** (`R2-期刊排名结果/FMS期刊排名及等级.xlsx`): journal-level SpringRank grades (A/B/C/D) usable as a lookup feature.
- **SpringRank implementation** (`JournalRank/1-代码/Springrank代码/py/`): reusable for future paper-level network work.

---

## 2. Architecture Overview

```
Input Layer
├── Track 1 — CLI (argparse, thin wrapper, prototype & reports)
└── Track 2 — API Program (primary implementation, portable, no CLI-tool dependency)
         ↓
Context Builder          [pure Python, no LLM]
├── GROBID JSON parser
├── Citation context extractor
├── Non-academic signal detector
└── Feature attacher + token budget controller
         ↓
LLM Abstraction Layer    [provider-agnostic]
├── AnthropicProvider
├── OpenAIProvider
└── Cost/token tracker
         ↓
Multi-Agent Evaluation Pipeline
├── L1 Rule router
├── L2 Lightweight batch intent pre-classifier
├── L3 Evaluator Agent
├── Critic Agent
└── Gate (accept / feedback-loop / low-confidence fallback)
         ↓
Output Layer
├── citation_eval.json  (always)
└── report.md           (Track 1 optional)
```

**Technology constraints**:
- No LangChain / LangGraph / AutoGen — direct Anthropic/OpenAI SDK calls only.
- Structured outputs via Pydantic + provider-native JSON schema (tool use / structured outputs).
- Track 1 and Track 2 share 100% of the core implementation; CLI is a thin `argparse` wrapper over `pipeline/evaluate.py`.

---

## 3. Context Builder

**Input**: `paper.json` (single GROBID-processed paper)
**Output**: `List[CitationContext]`

### CitationContext Schema

```python
CitationContext:
  # Location
  citation_id: str            # "{paragraph_id}__{ref_target}"
  citing_paper_hash: str
  cited_ref_id: str           # matches references[].id

  # Semantic context (token-budget controlled)
  citation_sentence: str      # the sentence containing the inline citation
  context_window: str         # ±2 surrounding sentences, hard cap 400 tokens
  section: str                # e.g. "Introduction", "Method", "Conclusion"

  # Cited paper metadata
  cited_title: str
  cited_authors: List[str]
  cited_year: int
  cited_journal: str
  cited_journal_grade: Optional[str]  # A/B/C/D from JournalRank; null if unavailable

  # Structural features
  citation_frequency: int     # how many times this ref appears in the paper
  is_first_occurrence: bool

  # Non-academic signals (rule-based, no LLM)
  non_academic_flags: List[str]
  # values: "self_cite" | "retracted" | "dangling" | "same_institution"
```

### Token Budget Rules
- `context_window` hard cap: **400 tokens**. Priority on retention: citation sentence → preceding sentence → following sentence → further context.
- `cited_title` truncated at 200 chars if longer.
- Full structure serialized token count estimated before batching.

### Non-Academic Signal Detection (rules only)
| Signal | Detection method |
|--------|-----------------|
| `self_cite` | Citing ∩ cited author lists non-empty |
| `dangling` | Citation sentence (stripped of marker) < 15 words |
| `retracted` | Local retraction cache lookup (synced from Retraction Watch / CrossRef) |
| `same_institution` | Institution field comparison where available |

---

## 4. LLM Abstraction Layer

### Interface

```python
class LLMProvider(Protocol):
    def complete(
        self,
        messages: List[Message],
        model: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.2
    ) -> BaseModel: ...

    def batch_complete(
        self,
        requests: List[BatchRequest]
    ) -> List[BaseModel]: ...
```

`AnthropicProvider` uses tool-use to enforce structured output.
`OpenAIProvider` uses `response_format` structured outputs.
Active provider selected via `config.yaml`; business logic imports only the Protocol.

### Model Tiers (overridable in config)

| Tier | Default | Used for |
|------|---------|----------|
| `FAST` | `claude-haiku-4-5` | L2 batch intent pre-classification |
| `STANDARD` | `claude-sonnet-4-6` | L3 Evaluator Agent |
| `REVIEW` | `claude-sonnet-4-6` | Critic Agent |

### Built-in cross-cutting concerns
- Exponential backoff retry (max 3 attempts).
- Per-call input/output token logging; cumulative cost tracking.
- Structured output parse failure → one re-parse attempt before raising.

---

## 5. Multi-Agent Evaluation Pipeline

### Flow

```
CitationContext
      │
      ▼
[L1 Rule Router]
  retracted / extremely low quality ──→ emit flagged result (skip LLM)
      │ normal
      ▼
[L2 Batch Intent Pre-classifier]   FAST model
  Citations from one paper batched per call (max batch size configurable, default 20).
  Papers with more citations split into multiple L2 calls.
  Input: citation_sentence + section
  Output: preliminary_intent per citation
      │
      ▼
[L3 Evaluator Agent]               STANDARD model, one citation per call
  Input: full CitationContext + preliminary_intent
  Output: EvaluationDraft (see schema below)
      │
      ▼
[Critic Agent]                     REVIEW model
  Input: CitationContext + EvaluationDraft
  Output: CritiqueResult { passed: bool, issues: List[str] }
      │
      ▼
[Gate]
  passed ──────────────────────────→ finalise and emit
  failed, retry_count < 2 ────────→ inject critique into Evaluator, retry
                                     (max 2 retries = 3 total Evaluator calls per citation)
  failed, retry_count == 2 ───────→ emit with low_confidence = true
```

### EvaluationDraft Schema

```python
class EvaluationDraft(BaseModel):
    intent_primary: Literal[
        "Background", "Method", "Result", "Motivation", "Future", "Other"
    ]
    intent_secondary: Optional[str]
    intent_reasoning: str          # must cite specific text evidence

    importance: Literal["High", "Medium", "Low"]
    importance_reasoning: str

    quality: Literal["Adequate", "Marginal", "Questionable"]
    quality_reasoning: str

    adequacy: Literal["High", "Medium", "Low"]
    adequacy_reasoning: str        # relevance of cited content to citing claim

    uniqueness: Literal["Unique", "Common", "Unclear"]
    uniqueness_reasoning: str      # replaces "replaceability"; assesses contribution uniqueness

    non_academic_assessment: Optional[str]  # populated only when flags present

    confidence: float              # 0.0–1.0
```

### Critic Agent Checklist
1. Does each `_reasoning` field cite concrete textual evidence?
2. Is intent consistent with the section label?
3. Are there logical contradictions between dimensions?
4. Is `confidence` calibrated to the depth of reasoning?

### Efficiency Mechanisms
| Mechanism | Details |
|-----------|---------|
| L1 skip | Retracted / dangling citations bypass LLM entirely |
| L2 batching | All citations in one paper → one FAST-model call |
| Shared paper context | Paper-level metadata loaded once per paper |
| Token budget | Context Builder caps every context at 400 tokens |
| Result caching | Evaluations keyed by `sha256(citation_sentence + cited_title)`; identical citations not re-evaluated |
| Tiered models | Routine cases use FAST, full evaluation uses STANDARD |

---

## 6. Output Schema

### `citation_eval.json` (per paper)

```json
{
  "paper": {
    "hash": "<MD5>",
    "title": "...",
    "authors": ["..."],
    "year": 2018,
    "journal": "..."
  },
  "citations": [
    {
      "citation_id": "p_7ab8e3f8__#b25",
      "cited_paper": {
        "ref_id": "b25",
        "title": "...",
        "authors": ["..."],
        "year": 2014,
        "journal": "...",
        "journal_grade": "A"
      },
      "context": {
        "sentence": "...",
        "section": "Introduction",
        "frequency_in_paper": 2,
        "is_first_occurrence": true
      },
      "non_academic_flags": ["self_cite"],
      "evaluation": {
        "intent":      { "primary": "Background", "secondary": null, "reasoning": "..." },
        "importance":  { "level": "Medium",  "reasoning": "..." },
        "quality":     { "level": "Adequate", "reasoning": "..." },
        "adequacy":    { "level": "High",    "reasoning": "..." },
        "uniqueness":  { "level": "Common",  "reasoning": "..." },
        "non_academic_assessment": "...",
        "confidence": 0.88
      },
      "processing": {
        "model": "claude-sonnet-4-6",
        "iterations": 1,
        "input_tokens": 412,
        "output_tokens": 298,
        "low_confidence": false
      }
    }
  ],
  "summary": {
    "total_citations": 27,
    "by_intent":     { "Background": 15, "Method": 8, "Result": 3, "Other": 1 },
    "by_importance": { "High": 5, "Medium": 17, "Low": 5 },
    "by_quality":    { "Adequate": 22, "Marginal": 4, "Questionable": 1 },
    "flagged":       { "count": 3, "types": ["self_cite", "retracted"] },
    "processing":    {
      "total_input_tokens": 11200,
      "total_output_tokens": 8100,
      "estimated_cost_usd": 0.031
    }
  }
}
```

### Integration with JournalRank
The `evaluation.importance.level` and `evaluation.quality.level` fields from each citation can be mapped to a numeric weight and applied as edge weights in the JournalRank citation network, replacing raw citation count `A[i,j]` with a quality-adjusted sum.

---

## 7. Project Directory Structure

```
citation-eva/
├── pdf2json/                         # existing GROBID pipeline
├── scripts/                          # existing utilities
├── docs/superpowers/specs/           # this file
│
└── citation_eval/                    # new: citation evaluation system
    ├── config.yaml                   # model tiers, token budget, provider, retraction cache path
    │
    ├── context_builder/
    │   ├── parser.py                 # GROBID JSON → raw citation list
    │   ├── extractor.py              # context window extraction + token budget
    │   ├── feature.py                # section / frequency / journal grade lookup
    │   └── detector.py              # non-academic signal rules
    │
    ├── llm/
    │   ├── base.py                   # LLMProvider Protocol, Message, BatchRequest types
    │   ├── anthropic_provider.py
    │   ├── openai_provider.py
    │   └── tracker.py                # token + cost tracking
    │
    ├── agents/
    │   ├── schemas.py                # EvaluationDraft, CritiqueResult Pydantic models
    │   ├── prompts/
    │   │   ├── l2_intent.txt
    │   │   ├── evaluator.txt
    │   │   └── critic.txt
    │   ├── l2_classifier.py          # batch intent pre-classification
    │   ├── evaluator.py              # L3 Evaluator Agent
    │   ├── critic.py                 # Critic Agent
    │   └── gate.py                   # Gate + retry logic
    │
    ├── pipeline/
    │   └── evaluate.py               # main entry: single paper or batch
    │
    ├── output/
    │   ├── formatter.py              # assemble final JSON
    │   └── report.py                 # Markdown report (Track 1 optional)
    │
    └── cli.py                        # Track 1: thin argparse wrapper over pipeline/evaluate.py
```

---

## 8. Open Questions / Future Work

- **Paper-level SpringRank**: If paper-level network computation is desired in a later iteration, the existing `JournalRank/py/SpringRank.py` can be reused with paper nodes instead of journal nodes. The large citation database already contains the necessary paper-to-paper citation data.
- **Retraction cache**: Needs a scheduled sync mechanism from Retraction Watch / CrossRef retraction data.
- **Intent taxonomy extension**: Current taxonomy (Background / Method / Result / Motivation / Future / Other) can be expanded or mapped to ACL-ARC if needed.
- **Adequacy via full-text RAG**: When the cited paper is also in the GROBID corpus, adequacy reasoning can be grounded in the actual cited content rather than just title/metadata.
