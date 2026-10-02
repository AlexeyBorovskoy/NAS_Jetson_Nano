# DEV.to publication plan — a family cloud on a Jetson Nano

> **Status:** editorial plan approved by the owner on 2026-10-02; article not written or published.
> Russian pair: [DEVTO_PUBLICATION_PLAN_2026-10.ru.md](DEVTO_PUBLICATION_PLAN_2026-10.ru.md).
> Task: ART-DEV-1 in [WORK_PLAN.md](../../WORK_PLAN.md).

## 1. Reader promise and audience

Explain which constraints and real failures shaped a family cloud on a 4GB Jetson Nano.
The audience is developers and home-server owners interested in operations,
data boundaries and recovery.

First article: architecture and three verifiable stories. Detailed backups,
the AI assistant and security auditing belong in follow-ups. This is a standalone
English article drawing on shared Habr evidence, with its own editorial structure.

## 2. Title, opening and length

Approved working title:

**From NAS to Family Cloud: Lessons from a 4GB Jetson Nano**

Open with the documented incident: the container was healthy, but the family's
Telegram bot was silent for six days. Ask what “the server works” actually means.
Then briefly return to the original NAS idea and the family's growing requirements.
Do not invent dialogue, the author's feelings, causes or incident consequences.

Target **2,000–2,500 English words**, seven main sections. This is an editorial
choice, not a DEV.to requirement. Keep the stack table short; installation
commands belong only where they explain a particular decision.

## 3. First-article structure

| # | Section | Reader takeaway |
|---|---|---|
| 1 | A healthy container, a silent bot | A real failure; process state differs from the user outcome |
| 2 | Why an old Jetson became a family cloud | Original need, available hardware and family use cases; 2–3 paragraphs |
| 3 | The architecture and its boundaries | One legible diagram showing data, nodes, access and component status |
| 4 | Constraints that shaped the design | RAM, compatibility, CGNAT, privacy and recovery → decisions and trade-offs |
| 5 | Three failures, three independent checks | Three stories in a consistent format with evidence that fixes worked |
| 6 | Measurements and unfinished work | A few dated measurements and honest current limitations |
| 7 | What I would design differently | Concrete practices applicable to another homelab |

Merge the original constraints, excluded Nano workloads and hardware-needs sections.
Integrate audit findings into failure stories instead of repeating a scanner list.
Move detailed RBAC and AI explanations to follow-ups.

## 4. Three stories and their evidence

Each story: **symptom → initial hypothesis → verification → fix → remaining risk**.
Include an initial hypothesis only when it is documented.

| Story | Sources to verify | Required evidence |
|---|---|---|
| Healthy container, unresponsive bot | [26 September checkpoint](../plans/CHECKPOINT_2026-09-26.ru.md), [evidence log](HABR_PART2_MATERIALS.md) | A live process does not prove a working poll loop; check an answer/loop heartbeat |
| Directory exists, disk is not mounted | [Habr Part 2 plan](HABR_PART2_ARTICLE_PLAN_2026-09.md), mount-check code and runbook | Find a specific incident and independent mount check; directory existence is insufficient |
| Backup job started, output missing | [1 August measurements](MEASUREMENTS_EN.md), [evidence log](HABR_PART2_MATERIALS.md) | Check copy freshness/content, then restoration of the relevant dataset |

Before writing each story, create a dated fact-table entry with primary evidence.
A guard in source code alone does not prove the claimed incident occurred.
If an incident cannot be verified, leave its slot pending and describe the
technical condition as a risk scenario, without inventing personal experience.

## 5. Required technical corrections

- **Bot:** two branches. Home command → local recognition/validation → allowed
  function → ready answer. General question → gateway → sensitive-data redaction
  → external provider. Do not draw `home.status → LLM formats answer`: current
  local tool replies return before a cloud call. Verify `gate_reply` and `ask` in
  [talk_bot.py](../../services/nas_jetson_nano-api/app/routers/talk_bot.py).
- **Privacy:** no arbitrary shell and redaction are specific restrictions,
  not proof of complete security or guaranteed removal of all personal data.
  Distinguish local family-data storage from external services for general questions.
- **Access:** reverse SSH supplies connectivity through CGNAT; describe restrictions
  on VPS service access separately. No home-router port forwarding does not prove
  there are no publicly reachable VPS services. Family VPN and NAS access are separate
  concerns; reconcile dated updates in [ADR-0005](../decisions/ADR-0005-vps-autossh-reverse-tunnel.md)
  and [ADR-0006](../decisions/ADR-0006-vps-nginx-https.md).
- **Backups:** `SSD → HDD → S3` is a target topology, not proof of protecting all data.
  Show “dataset / original / existing copy / restore verification / open risk”.
  Separate the Immich library, DB dumps, configuration and other archives.
  The [22 September checkpoint](../plans/CHECKPOINT_2026-09-22.md) verifies Immich L1,
  not a completed S3 photo copy. A configuration restore drill is not full disaster recovery.
- **ML and nodes:** mark workstation/cloud offload as an experiment or plan until
  current deployment evidence exists. Compose/runbooks do not prove production use.
  [ADR-0007](../decisions/ADR-0007-node-model-jetson-sor-cloud-edge.md) excludes
  workstation/Vostro as required NAS nodes;
  [ADR-0010](../decisions/ADR-0010-immich-ml-cloudru.md) describes proposed ML offload.
- **Git and recovery:** the repository stores the system description and procedures;
  recovery also needs separately backed-up data and secrets. Do not promise full
  recovery from a checkout without a verified end-to-end exercise.
- **Audit:** a concrete defect, fix and verification matter more than scanner names.
  Distinguish “in Git”, “deployed” and “verified on device”; stages 15/18 were
  implemented locally without deployment when this plan was approved.

## 6. Facts, measurements and diagram

The next step is a table: **claim → source → date → implementation status**.
Gather evidence before the final draft; the final fact reconciliation is shared with Habr.
Use August's [PROJECT_FACTS_EN.md](PROJECT_FACTS_EN.md) and
[MEASUREMENTS_EN.md](MEASUREMENTS_EN.md) as dated snapshots, not October's live state.

For RAM, tunnel latency, power and protected-data volume, state date, method and
conditions. Separate measurements from estimates, board power from full-system
power, and library size from actually protected data. Include operating costs
(VPS, storage, AI, electricity) only with verified evidence.

Statuses: **deployed and verified / implemented locally / experiment / deferred**.
Distinguish working and target links, storage and compute, access direction and
data boundaries in the diagram. Do not depict family photos being sent to an external LLM.

## 7. Follow-ups and DEV.to presentation

Candidates after article one: backup/restore; local commands and the AI gateway;
security auditing with fixes. Their order and dates are not scheduled yet.

Use a legible cover; put the detailed architecture diagram inside the article.
Up to four tags; working set: `selfhosted`, `homelab`, `docker`, `devops`.
Check applicability in the editor before publishing. A 1000 × 420 cover is
recommended by the [DEV Editor Guide](https://dev.to/p/editor_guide).
Images need alt text and redaction following
[IMAGE_REDACTION_CHECKLIST.md](IMAGE_REDACTION_CHECKLIST.md).

Editorial references checked during the plan review on 2026-10-02:
[Starting Over on My Home Server](https://dev.to/robinreinecke/starting-over-on-my-home-server-520a),
[Building a Sovereign Home Server](https://dev.to/henk_van_hoek/building-a-sovereign-home-server-lessons-learned-running-nextcloud-euro-office-and-frigate-on-a-1kbc),
[Running Immich on Proxmox With a Synology NAS](https://dev.to/3zzy/running-immich-on-proxmox-with-a-synology-nas-a-battle-tested-setup-1e42).
This sample does not establish topic rarity or predict publication reach.

## 8. Workflow and completion criteria

1. Fill the fact table; verify three incidents and the recovery scope.
2. Prepare a separate English draft using seven sections and a status-aware diagram.
3. Reconcile facts with the Habr evidence log and current checkpoints/ADRs, keeping caveats.
4. Check secrets/identifiers, links, images, alt text and DEV preview.
5. Final editing and publication belong to the owner; record the actual URL in
   [publication_status.md](publication_status.md) only after publication.

Ready means every factual claim traces to dated evidence; no confusion between live
state and plans, promotional guarantees, duplicated sections or private data;
length and diagram match this plan, and preview is checked. The existing Hackaday
text is not a ready DEV.to draft. Approval of the plan does not mean the article is published.

## 9. Verification and rollback of this change

Documentation only: new RU/EN plan and references from README, publication status
and WORK_PLAN. Check `git diff --check`, local link targets, RU/EN pairing and
consistent “plan approved, article unpublished” status. Rollback: reverse these
documentation changes, preserving independent stage 15/18 changes.
This step does not affect operational settings, data or secrets.
