# 20. Agent Operating Model / Операционная модель агентов

> 🇬🇧 This document describes how subagents are used in the NAS_Jetson_Nano project: roles, safety boundaries, and workflow.
>
> 🇷🇺 Документ описывает модель работы с субагентами в проекте NAS_Jetson_Nano: роли, границы безопасности и рабочий процесс.

## 1. Purpose / Назначение

🇬🇧 Subagents are the default way to work on risky or multi-domain changes in NAS_Jetson_Nano. The main agent remains the coordinator, but focused subagents are used to separate analysis, safety review, implementation, verification, and documentation.

🇷🇺 Субагенты — стандартный способ работы с рискованными или многодоменными изменениями в NAS_Jetson_Nano. Основной агент остаётся координатором, а субагенты используются для разделения анализа, проверки безопасности, реализации, верификации и документирования.

🇬🇧 The goal is to:

- reduce the chance of destructive infrastructure actions;
- keep each step small and verifiable;
- separate read-only inventory from write operations;
- keep `README.md`, `AGENTS.md`, ADRs, plans, and runtime evidence aligned;
- protect secrets and personal data from accidental publication.

🇷🇺 Цели:

- снизить риск деструктивных действий с инфраструктурой;
- делать каждый шаг маленьким и верифицируемым;
- разделять read-only инвентаризацию от write-операций;
- держать `README.md`, `AGENTS.md`, ADR, планы и runtime-свидетельства согласованными;
- защищать секреты и персональные данные от случайной публикации.

## 2. Base Rule

The coordinator owns the final decision and integrates all outputs. A subagent
does not expand the project's safety boundaries. If a subagent's recommendation
conflicts with `AGENTS.md`, ADRs, `docs/19_NETWORK_INVENTORY.md`, or
`docs/04_STORAGE_DESIGN.md`, the stricter rule wins.

By default, subagents work in read-only mode. They inspect docs, code, logs,
screenshots, command output, and runtime state, then return a report. A subagent
may edit files or change system state only when the coordinator explicitly gives
it an implementation role and a bounded write set.

## 3. When Subagents Are Required

Use a safety subagent before actions involving:

- router UI, DHCP, firewall, port forwarding, Wi-Fi, VPN, Tailscale, or SSH;
- HDD, `/mnt/storage`, `/mnt/hdd-check`, `fstab`, partitions, mounts, Docker
  volumes, backup, or restore;
- real secrets, `.env`, router labels, MAC addresses, serial numbers, Wi-Fi
  credentials, VPS access, SSH keys, or screenshots;
- direct or indirect exposure of Nextcloud, Immich, LLM Gateway, Samba, or SSH;
- database deletion, Docker volume cleanup, formatting, repartitioning, or other
  destructive operations.

For ordinary low-risk documentation or code edits, subagents are optional.

## 4. Standard Roles

### 4.1 Documentation Subagent

Use for:

- structure of new documents;
- README, AGENTS, ADR, plan, and runbook synchronization;
- checking that new instructions do not conflict with accepted decisions.

Does not:

- change network, storage, Docker, or secrets;
- recommend write commands without a safety gate.

### 4.2 Network Safety Subagent

Use before any action with:

- router UI;
- DHCP;
- firewall;
- port forwarding;
- VPN;
- Tailscale;
- SSH access to Jetson or VPS.

Required sources:

- `AGENTS.md`;
- `docs/19_NETWORK_INVENTORY.md`;
- `docs/decisions/ADR-0003-networking-lan-only.md`;
- `docs/decisions/ADR-0004-tailscale-external-access.md`.

### 4.3 Storage / HDD Safety Subagent

Use before any action with:

- `/mnt/storage`;
- `/mnt/hdd-check`;
- `lsblk`, `blkid`, `findmnt`, mount, or `/etc/fstab`;
- Docker volumes;
- backup/restore;
- `scripts/storage/setup_disk.sh`.

Required sources:

- `docs/04_STORAGE_DESIGN.md`;
- `docs/decisions/ADR-0002-storage-design.md`;
- `docs/12_BACKUP_RESTORE.md`;
- `docs/14_TEST_PLAN.md`.

### 4.4 Secrets / Privacy Subagent

Use before:

- GitHub publication;
- adding `.env`, config, inventory, screenshots, or router photos;
- working with router labels, MAC, serial, Wi-Fi, VPS, SSH keys, or API keys;
- sending any project data to an external LLM.

Checks:

- no raw secrets in tracked files;
- placeholders are used in public docs;
- reports do not expose personal filenames, photos, contacts, calendars,
  documents, or backup manifests.

### 4.5 Service Implementation Subagent

Use for bounded implementation work on:

- Nextcloud;
- Immich;
- Samba;
- LLM Gateway;
- monitoring;
- Backup API.

If a service change touches network, storage, backup, or secrets, run the
relevant safety subagent first.

### 4.6 Verification Subagent

Use after changes to:

- run focused checks;
- verify command output;
- detect documentation drift;
- confirm that public docs do not claim unverified facts;
- list residual risks and open items.

## 5. Safety Boundaries

### 5.1 Router / Network

Forbidden without explicit user confirmation:

- changing DHCP, firewall, port forwarding, VPN, Wi-Fi, or ISP settings;
- enabling router remote management;
- exposing Nextcloud, Immich, LLM Gateway, Samba, or SSH directly to the
  internet;
- touching the Amnezia server on the EU VPS through SSH or `wg set`;
- deleting or replacing Jetson's `nas_jetson_nano-lan` profile.

Allowed safe mode:

- read-only inventory;
- `ping`, `arp`, `Test-NetConnection`, route checks;
- viewing router UI pages without `Save` or `Apply`;
- Tailscale planning as the preferred external-access path.

### 5.2 HDD / Storage

Forbidden without explicit user confirmation:

- formatting disks;
- changing partition tables;
- running `scripts/storage/setup_disk.sh` on a disk with unknown or existing
  data;
- mounting an existing data HDD as working `/mnt/storage` before a migration
  plan exists;
- using `docker compose down -v`;
- clearing Docker volumes;
- forcing repair of dirty/hibernated NTFS on Jetson.

Allowed safe mode:

- `lsblk`, `blkid`, `findmnt`, `df -hT`;
- read-only mount at `/mnt/hdd-check`;
- metadata-only reports with sizes, filesystem type, labels, counts, and
  categories;
- no personal filenames in public reports.

### 5.3 Secrets / Personal Data

Forbidden:

- committing real passwords, tokens, API keys, serial numbers, MAC addresses,
  Wi-Fi credentials, or private keys;
- sending personal photos, videos, contacts, calendars, documents, or backup
  manifests to an external LLM;
- printing raw values from `config/.env` in reports.

Allowed:

- placeholder names such as `HOME_ROUTER_ADMIN_PASSWORD`, `VPS_HOST`, and
  `DEEPSEEK_API_KEY`;
- schema/count/category summaries;
- secret scanning before publication.

## 6. Report Format

Each subagent report should include:

1. Role.
2. Scope.
3. Sources.
4. Short conclusion.
5. Proposed changes.
6. What must not change.
7. Verification commands.
8. Risks.
9. Rollback.
10. Open questions.
11. Next safe step.

## 7. Project Workflow

Every technical block follows this pipeline:

1. Coordinator defines one small step.
2. Documentation subagent checks write set and documentation impact when needed.
3. Safety subagent checks boundaries if network, storage, secrets, backup,
   restore, or external access are involved.
4. Implementation agent performs only the approved write set.
5. Verification subagent checks commands, tests, and actual state when needed.
6. Documentation is updated if rules, architecture, or operational state changed.
7. Coordinator returns summary, changed files, commands, risks, rollback, and
   next step.

If the step concerns router, HDD, secrets, external access, backup, or restore,
the safety check is mandatory.

## 8. Current Standard Subagent Set

| Area | Default role | Typical output |
|---|---|---|
| Router / LAN / VPN | Network Safety Subagent | read-only facts, pending UI checks, risks |
| HDD / storage / backup | Storage Safety Subagent | sizes, mount status, migration risk, rollback |
| Secrets / screenshots | Secrets / Privacy Subagent | leak scan, placeholder plan, ignored paths |
| Documentation | Documentation Subagent | write set, doc links, consistency notes |
| Service work | Service Implementation Subagent | bounded patch and verification |
| Post-change checks | Verification Subagent | command results and residual risk |

## 9. Domain-Specific Role Agents (Prompt A model)

Five domain agents cover all project work. Each agent has a dedicated prompt file
with scope, hard rules, architecture facts, and report format.

| Agent | Prompt file | Primary zone |
|---|---|---|
| **Code Agent** | `docs/prompts/CODEX_CODE_AGENT.md` | `services/`, Dockerfiles, CI `.github/` |
| **Hardware Agent** | `docs/prompts/CODEX_HARDWARE_AGENT.md` | `scripts/diagnostics/`, `systemd/`, Jetson SSH |
| **Docs Agent** | `docs/prompts/CODEX_DOCS_AGENT.md` | `docs/`, `README.md`, `CHANGELOG.md`, ADR |
| **Network Agent** | `docs/prompts/CODEX_NETWORK_AGENT.md` | `scripts/network/`, `docker/vps/`, VPS nginx |
| **SysApps Agent** | `docs/prompts/CODEX_SYSAPPS_AGENT.md` | `docker/compose/`, `configs/`, `.env.example` |

### How to invoke

In a new session, tell the coordinator which agent role to apply:
```
Apply the Hardware Agent role (docs/prompts/CODEX_HARDWARE_AGENT.md).
Task: <one bounded task here>
```

The coordinator reads the prompt file, applies the scope and hard rules, and
operates within that domain only. For cross-domain tasks, run agents sequentially
and integrate outputs.

### Cross-agent boundaries

When a task touches multiple domains, the order is:
1. **Docs Agent** first — check existing documentation constraints.
2. **Network/Hardware Agent** — safety check if network or storage is involved.
3. **SysApps or Code Agent** — implementation within bounded write set.
4. **Docs Agent** again — update CHANGELOG, PROJECT_TREE, affected docs.
