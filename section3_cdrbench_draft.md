# Section 3 Draft: CDR-Bench

## Outline

- 3.1 Task definition and benchmark goal
- 3.2 Domains and operator space
- 3.3 Benchmark construction pipeline
- 3.4 Benchmark tracks and composition
- 3.5 Transition to experiments

## Draft Text

### 3.1 Task Definition and Benchmark Goal

To evaluate the gap identified in the previous section, we construct **CDR-Bench**, a benchmark for **direct execution of compositional data-refinement requests**. Each instance provides a model with a raw text sample and a user-facing refinement request expressed in natural language, and asks the model to return a structured output with a final keep/drop decision and the resulting refined text. In contrast to workflow-synthesis, code-generation, or tool-use benchmarks, CDR-Bench fixes the refinement policy and measures whether a model can **faithfully execute** that policy on the given instance. This design isolates execution fidelity from planning ability and makes the benchmark directly aligned with practical data-preparation settings in which users want cleaned outputs rather than pipeline code.

We standardize all tasks with a unified output interface, `{"status": "KEEP|DROP", "clean_text": "..."}`. This protocol allows us to compare models across domains, workflow types, and difficulty levels under the same evaluation contract. Importantly, the hidden ground truth is not produced by human paraphrasing, but by replaying deterministic Data-Juicer-based operators over the raw sample. As a result, benchmark errors can be attributed to failures in compositional execution rather than to ambiguous annotation or subjective target text choices.

### 3.2 Domains and Operator Space

CDR-Bench is organized by **application scenario rather than raw corpus source**. The current text-first version covers four domains: **web** for crawl cleanup and filtering, **arxiv** for scientific source cleanup, **knowledge\_base** for support and documentation refinement, and **pii** for privacy-oriented sanitization and redaction. Each domain combines domain-specific mappers with a shared set of quality filters, which lets the benchmark test both domain-specialized transformations and more general keep/drop decisions. In the current configuration, the benchmark uses nine shared filters and domain-specific operator inventories tailored to the target scenarios, such as HTML cleanup for web pages, TeX-specific normalization for arXiv source, repeated-sentence removal for support documents, and multi-type identifier redaction for PII-heavy text.

This scenario-centric design is a deliberate departure from source-centric dataset construction. A sample is assigned to a benchmark domain according to its **operator-activation profile**, not merely according to where it was collected from. This means that one raw corpus can contribute examples to multiple benchmark domains when its samples exhibit the corresponding refinement needs. Such a design better reflects real data curation, where the same underlying corpus may contain web-cleanup, knowledge-base, or privacy-sanitization cases, and it avoids turning domain labels into shallow proxies for data provenance.

### 3.3 Benchmark Construction Pipeline

We build CDR-Bench through a bottom-up, data-grounded pipeline. Starting from raw corpora, we first run the candidate operator inventory with a repo-local Data-Juicer stack and record, for each sample, which mappers are active and which filters are passed at different processing stages. These per-sample execution traces are then used for domain assignment and downstream workflow mining. After this stage, the retained samples cover all four benchmark domains, with the final domain-level composition to be reported once benchmark materialization is complete. This construction ensures that the benchmark is not dominated by a single editing pattern, but spans multiple realistic refinement scenarios with substantially different operator profiles.

After domain assignment, we mine frequent operator combinations from the retained samples and keep only workflow candidates that are supported by real data. Concretely, workflow discovery is bottom-up: we identify recurring clean-operation sets, group them into workflow families, and exclude unsupported fallback combinations from final materialization. The resulting workflow library spans multiple domains and multiple refinement patterns, and the exact number of workflow families and selected workflows can be filled in after the full benchmark run. We then impose a deterministic order on the mined operator sets, replay the resulting clean prefixes to obtain checkpoint states `S0, S1, ..., Sfinal`, and attach filter operations at meaningful positions in the sequence.

Two additional policies are important for benchmark quality. First, filter thresholds are **recalibrated during materialization** rather than copied directly from operator defaults, so that keep/drop tasks better match the intended evaluation difficulty and avoid degenerate thresholds. Second, prompt generation is separated from ground-truth construction: deterministic references are fixed first, and natural-language request variants are generated afterward. This separation allows us to vary prompt wording without changing the underlying benchmark answer, which is important for robust model comparison.

### 3.4 Benchmark Tracks and Composition

The final benchmark contains three complementary tracks. The **main track** is the headline evaluation and includes three workflow types: `clean-only`, `filter-then-clean`, and `clean-then-filter`. These settings capture whether a model can perform direct transformation, raw-input filtering followed by refinement, and refinement-conditioned filtering, respectively. During materialization, filter-oriented variants are calibrated toward a balanced keep/drop ratio, while instance selection is diversity-aware so that the benchmark is not overrun by a small number of highly frequent source records.

We additionally construct an **order-sensitivity track** as a diagnostic benchmark. For each order family, we instantiate multiple variants that share the same raw input, clean skeleton, and filter, but place the filter at different positions, corresponding to front, middle, and end execution patterns. A family is retained only when different orderings lead to different deterministic references. This design directly tests whether a model follows the requested operation order instead of collapsing to a generic “clean first” or “filter first” heuristic.

Finally, we include an **atomic track** that evaluates single operators in isolation. These atomic instances are grouped by operator globally rather than by domain-operator pairs, and they serve as a calibration layer for interpreting failures on the main benchmark. By comparing atomic performance against compositional performance, we can distinguish failures caused by intrinsically difficult operators from failures caused by composition, ordering, or interaction among otherwise manageable steps.

### 3.5 Transition to Experiments

Overall, CDR-Bench is designed to provide three properties that are not jointly emphasized in prior work: **realistic domain grounding**, **deterministic compositional references**, and **explicit diagnostics for order and atomic difficulty**. Because all tasks share the same `status + clean_text` interface while varying in domain, workflow type, and composition depth, the benchmark supports both aggregate comparison and fine-grained error analysis. We therefore use the next section to evaluate models not only on overall benchmark performance, but also on per-domain behavior, per-track behavior, and the gap between atomic competence and compositional execution.

## Notes for Integration

- If your paper uses a different section number for experiments, replace "the next section" with the exact section reference.
- When the benchmark finishes materializing, add concrete numbers for domain composition, workflow-library size, and final track sizes.
- If `data/benchmark/*.jsonl` is fully materialized later, replace the current placeholder distribution language with final benchmark-instance distributions.
