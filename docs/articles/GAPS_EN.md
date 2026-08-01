# GAPS — blockers, risks & open items (v3 audit, 2026-08-01)

Severity: 🔴 high · 🟠 medium · 🟡 low. Effort is a rough estimate.

## Security
| # | Finding | Sev | Effort | Note |
|---|---|---|---|---|
| S1 | **`nas-api` (admin API) publicly exposed** on VPS `:8099` (`0.0.0.0`) | 🔴 | S–M | Add auth or move behind VPN/Tailscale; do not publish the admin API |
| S2 | **LLM Gateway `:8090/:9443` publicly exposed** | 🔴 | S | Same — restrict to VPN/LAN |
| S3 | Nextcloud/Immich public with **self-signed TLS**, no ACME | 🟠 | M | Login exists, but browser warnings + no cert trust; ACME needs a domain |
| S4 | Immich images use the **moving `:release` tag** (unpinned) | 🟠 | S | Pin to a digest/version for reproducibility + supply-chain safety |
| S5 | Secrets in git history | 🟢 done | — | Already `filter-repo`'d + passwords rotated (per CLAUDE.md) — verify once more with gitleaks |

> Net: the article's **rule #4 ("services not exposed directly to the internet") is currently violated**. The
> reader criticism about open ports is correct. This is the top item to fix before promoting the project.

## Operational (found in this audit)
| # | Finding | Sev | Effort | Note |
|---|---|---|---|---|
| O1 | **Backups stale since 2026-07-24 (~8 days)** | 🔴 | S | Timer active but no new dumps; investigate write/mount failure. **Restore never tested.** |
| O2 | **Memory overcommit**: limits ≈ 94% of RAM + `homecloud_samba` has no limit | 🟠 | S | Set a real samba `mem_limit`; re-balance |
| O3 | Immich runs the **legacy two-container topology** (server + separate microservices, same image) | 🟡 | S | Modern Immich 2.x folds microservices into the server; simplify compose |

## Reproducibility (can a stranger deploy from the README?)
| # | Finding | Sev | Effort | Note |
|---|---|---|---|---|
| R1 | **git ↔ device naming divergence**: README uses `nas_jetson_nano-*`; the live device runs `~/nasa`, `homecloud_*`, `nasa-*` | 🟠 | M | Follow-the-README will hit mismatched names; the rename was never rolled out |
| R2 | **EOL platform**: JetPack 4.6 / Ubuntu 18.04 / Docker 20.10 / CUDA 10.2 | 🟡 | — | Documented and accepted for a home lab; flag honestly in the article |
| R3 | Some runbooks are RU-only | 🟡 | M | For an English audience, translate the key setup/runbook docs |

## Measurements still open
| Item | Status | To get it |
|---|---|---|
| Disk `fio` (`/mnt/storage`) | pending | Run in a low-traffic window (authorized); compare to historical ~250 MB/s |
| Tunnel throughput (100 MB up/down, LAN vs tunnel) | pending | Needs a test file + WebDAV run |
| Contacts / calendars count | pending | `oc_cards` / `oc_calendarobjects` count |
| Backup restore test | pending | Restore a dump into a throwaway DB and verify |
| SSD temperature | 🔴 blocked | JMS583 SAT passthrough exposes no temp attribute; smartmontools 6.6 too old |

## Verified strengths (for balance)
- **0 OOM events and 0 container restarts in 30 days** on 4 GB — strong stability story.
- **Board power 2.30 W idle / 4.17 W load** — a genuinely low-power always-on server.
- **21 API endpoints**, **7,098 Immich assets**, all 13 containers healthy, 23-day uptime.
