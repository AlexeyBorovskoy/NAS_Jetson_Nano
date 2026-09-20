# DEV Community article brief: the Jetson Nano family cloud

**Status:** planned, not published. Updated 2026-09-20. This brief is an editorial entry point, not a claim that every feature below is live.

## Reader and promise

Primary reader: a self-hosting or infrastructure engineer considering old ARM hardware for a useful home service. Secondary reader: an edge AI engineer interested in which tasks fit on a 4 GB device and which require an external resource.

The article should answer: **How did a family cloud on a Jetson Nano grow without pretending that free cloud services or 4 GB of RAM have no limits?** Readers should leave with a small set of decisions they can test on their own hardware.

## Working title and through-line

“A Family Cloud on a 4 GB Jetson Nano: Free Resources, New Features, and the Failures We Had to Fix”

Repeated question: **Where do the data live, where does the work run, and what fails if a free service disappears?** Choose a final title only after the article's strongest result is measured.

## Proposed structure

1. **The problem and the baseline.** A short family use case; a link to the original Habr article for background, with enough context for readers who do not read Russian.
2. **The machine and the boundary.** Jetson Nano 4 GB, storage and network edge. One diagram showing data flows and third-party dependencies.
3. **Growth that users could see.** The Telegram assistant and one concrete command/download workflow. Show what was demonstrated and when.
4. **Where the free resources fit.** GigaChat for allowed text requests, GitVerse as a mirror, Kaggle as a preparation lab on public data. State that the VPS, drives and electricity are paid. Cloud.ru features must be labeled live, probed or proposed individually.
5. **Reliability work caused by growth.** Choose two or three failures from the audit. For each: symptom, diagnosis, fix, proof and remaining limitation.
6. **Voice commands if the end-to-end test passes.** Telegram voice input → local speech recognition on Jetson → command safety check → Bot reply. If the test is unfinished, move it to “Next experiment”. Voice reply is a separate capability.
7. **Numbers and limits.** Dated RAM, latency, restore and cost measurements. Distinguish a Kaggle benchmark from a Jetson measurement.
8. **What readers can reuse.** A small reproducible check, links to implementation and decisions, and a precise remaining question.

## Fact gates before drafting

| Claim | Current evidence | Publication rule |
|---|---|---|
| Services and Telegram bot run on the Jetson | [README](../../README.md) and deployment records dated 2026-09-19 | Recheck live status and date the observation |
| GigaChat and GitVerse are in use | [Sber integration index](../integrations/sber/README.md) | Verify current quota and mirror behavior |
| Kaggle helps select a speech model | [Kaggle note](../integrations/kaggle/README.md) records account/API access | Do not claim GPU benefit until a completed experiment and Jetson recheck |
| Local voice commands work | [Research only](../research/VOICE_MESSAGES_RESEARCH_2026-09-20.md) | Require a demonstrated end-to-end command, memory and latency results, and error handling |
| Reliability improved | [Evidence log](HABR_PART2_MATERIALS.md) and audit/runbooks | Link symptom to dated post-fix verification; keep open risks visible |
| The approach is inexpensive | Current service quotas and real hardware/VPS/electricity costs | Publish date, currency, billing period and assumptions |

## Public assets to prepare

- Architecture and data-boundary diagram without personal identifiers or live addresses.
- One table comparing free-software, free-tier and paid components.
- One failure timeline or before/after measurement, with the measurement method.
- A short sanitized command or configuration excerpt that actually runs in the documented environment.

Do not upload family voice, photos, private conversations, raw logs or backup manifests to article services, demos or external LLMs. Do not add an Ollama/local-LLM demo to explain the current system; it would misstate the architecture.

## DEV-specific final pass

Use no more than four accurate tags, check the Markdown preview, and disclose substantial AI assistance according to [DEV's guidelines](https://dev.to/guidelines-for-ai-assisted-articles-on-dev). The [editor guide](https://dev.to/p/editor_guide) supports `canonical_url` for a genuine cross-post. A distinct English article need not inherit a canonical URL from a Russian article with different content.
