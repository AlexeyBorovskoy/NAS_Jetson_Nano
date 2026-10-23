# Checkpoint — 2026-10-23

[Русский](CHECKPOINT_2026-10-23.ru.md) · [Previous checkpoint](CHECKPOINT_2026-10-20.md)

## Project status

The base for this checkpoint is `main` at `b298a70fce10974e45116dad3d4995590b6854f0`: OBS was integrated linearly and bounded synthetic Cloud tests were added on October 22. Local remote-tracking refs `origin/main`, `gitverse/main`, and `gitverse/master` match this base; remote servers and CI were not rechecked on October 23. The worktree contains a separate owner change to `ds_worker.toml`; this checkpoint does not touch it. The local documentation commit follows this base; it was not pushed.

October 22 evidence: SMART uses a shared stable by-id; incomplete ATA Status was localized to USB/SAT, with direct SG_IO returning empty sense as well. This does not establish full HDD health; no new SMART self-test was started. The Cloud VM passed the separate Linux OBS suite, 323/323, synthetic local Restic recovery, and TIFF/PSD scenarios; valid PSD remains unsupported by the tested libvips build. These are not production DR, Jetson ARM acceptance, or proof of grant payment. The owner deferred family copying until home LAN; faces and family heavy-format trials also remain LAN-only pilot work.

OBS-1 is installed on the Jetson. The one-hour and two-hour acceptances passed, but the target write rate of ≤60 MB/day has not been established. The 24-hour observer was expected to finish around 11:48 MSK on October 23: **its result was not checked today** and must not be treated as successful or accepted. Tomorrow, read only its final report and verify duration, UTC date rollover, counters, and acceptance criteria. Earlier OBS, SMART, Immich, and backup results are in the [October 20 checkpoint with October 21–22 updates](CHECKPOINT_2026-10-20.md).

## Home network and AmneziaWG — October 23

Router, Deco, Jetson, VPN, and peer settings were not changed. The owner-authorized EC220 login ended another administrative web session; Wi-Fi and services were not restarted. Credentials were not saved in the project.

| Check | Result | Limit |
|---|---|---|
| Home Jetson | Ethernet and Internet work; the Jetson is upstream of Deco | Does not test a phone's path through the mesh |
| EC220, UI viewed only | WAN connected behind CGNAT; SPI enabled; DoS, service filter, ACL, parental/URL, and bandwidth rules disabled or empty; UPnP enabled with no entries; no port forwards | No explicit block was found in the reviewed sections; this was not a full audit |
| EC220 log | First and last of 53 pages reviewed; DHCP/IGMP warnings | The full log was not reviewed; no confirmed AWG error was seen |
| Clients | Deco is wired; one phone is listed directly on EC220 Wi-Fi | Does not establish which access point the earlier failed attempt used |
| VPS/AWG, read only, 09:44 MSK | 23 peers, 3 with handshakes within 3 minutes and rising counters; containers had no restarts/OOMKilled | Confirms service for some clients at that time, not the specific home phone |
| Synthetic UDP without handshake | First probe: 3 sent / 0 captured. Controlled repeat in one window: all 3/3 Cloud VM and 3/3 home packets reached the VPS interface | A persistent block of ordinary UDP on the tested port is not confirmed. The first probe remains unexplained; handshake, return path, and Deco were not tested |

The original report remains: according to the owner, phones fail at home and work on cellular. The phone is currently unavailable. **The cause is unknown; no fix has been identified.** Diagnostic material and temporary results remain in the ignored `.agent-work/tmp/home-vpn-20261023/` directory.

At 10:23 MSK, one peer endpoint matched the home's current egress IPv4; its last handshake was 58767 seconds old, with none within three minutes. A shared CGNAT IPv4 does not identify a phone; cumulative RX/TX does not establish current transfer.

## Cloud.ru Foundation Models

According to the owner's email, Cloud.ru Foundation Models will disable `GigaChat-2-Max` on November 2, 2026. The Jetson's family default is the direct GigaChat API; the separate optional Cloud.ru backend is configured for the retiring model. The public catalog confirmed IDs `GigaChat/GigaChat-3-Pro` and `ai-sage/GigaChat3.5-432B-A28B-Reasoning`; no inference requests to these candidates or migration were made. The Cloud.ru branch has no automatic DeepSeek fallback. **The primary routing and production configuration were not changed.**

Before the deadline: synthetically test one selected ID, response/usage format, and timeout; assess cost separately. Foundation Models are excluded from the “Evolution Test” grant; the November 6 grant deadline is a separate issue and does not authorize paid requests. After verification, propose updating `CLOUDRU_FM_MODEL`, related defaults, and instructions; do not call the migration complete until separately deployed and verified. References: [Cloud.ru notes](../integrations/sber/CLOUD_RU.md), [catalog and email review](../../.agent-work/tmp/home-vpn-20261023/cloudru_model_notice.ru.md).

## Plan for October 24

1. Prepare `.agent-work/tmp/home-vpn-20261024/` with only the required diagnostic scripts; preserve October 23 evidence without overwriting it. Repeat home Jetson route/gateway, DNS and HTTPS checks, EC220 WAN/DHCP and reviewed filters, and VPS status under the bounded scope. Record measurement times and the phone's actual access point.
2. Repeat the synthetic UDP test with the 3+3 positive control and retain both results. Do not substitute it for a phone connection or call a single loss a block.
3. Read the final 24-hour OBS observer result without auto-accepting it; if it failed or has incomplete data, leave daily acceptance open.
4. Ask the owner to test one available phone over home Wi-Fi, first with VPN off (ordinary website), then with the existing VPN profile on for 30–60 seconds; record exact times and outcomes. Compare direct EC220 Wi-Fi with Deco, then use cellular as a control. Do not change the profile.
5. During the same window, perform only bounded read-only VPS observation: handshake and RX/TX deltas for the corresponding peer. Do not expose keys or change Amnezia.
6. For the router UI, use the owner's local session or ask the owner to sign in directly; do not request or save the password again. Deco UI remains unchecked and needs its LAN side or the official app, without adding routes or remote management.
7. If the synchronized attempt provides no distinguishing evidence, leave the cause open and record which segment remains untested. Do not invent a fix.

Network testing is complete when ordinary Internet and AWG outcomes on the same phone are recorded for both home access points and cellular, with synchronized handshake/RX/TX evidence and an evidence-based conclusion or explicitly bounded diagnosis. If the phone or Deco is unavailable, testing remains incomplete. Completing it on October 24 is the owner's intent, not a guaranteed result.

## Local handoff and repeat commands

- Detailed notes without secrets: [RESULT.ru.md](../../.agent-work/tmp/home-vpn-20261023/RESULT.ru.md). Available only in this worktree; do not automatically publish ignored artifacts.
- Run local gates with `.venv/Scripts` first in PATH: the existing Python 3.11 has the dependencies. System Python 3.13 lacks `openai`, causing collection of `test_provider_timeouts.py` to fail; do not alter service code for this environment issue.
- The commands below identify today's scripts. Repeat using copies in the October 24 directory to preserve October 23 logs.
- VPS check: `python .agent-work/tmp/home-vpn-20261023/vps_readonly.py .agent-work/tmp/home-vpn-20261023/vps_health.py`. Lead only, strictly read only in the authorized scope with `MemoryMax=256M` and `MemorySwapMax=0`; stop if limits cannot be verified. This does not authorize ordinary SSH commands or Amnezia changes.
- Controlled UDP probe: `python .agent-work/tmp/home-vpn-20261023/udp_path_probe.py`. Three home plus three control packets; `tcpdump -p` with a unique BPF filter, up to 35 seconds. The Jetson's old `ip` requires text `ip route`, not JSON. This synthetic probe does not replace the real phone handshake test.
- EC220 local access was prepared at `http://127.0.0.1:18082/`, using `router_local_view.py` and the loopback SSH forward on port 18081. Tomorrow, first check that the processes and authentication still exist; do not assume the session survives overnight. These listeners are configured for loopback only. Keep credentials out of the checkpoint.
- No configuration rollback is needed: only local diagnostics changed. To stop local access, terminate only the identified `router_local_view.py` process and its SSH forward, not all Python/SSH processes. Preserve diagnostic evidence and other tunnels.

The article and project plan must not present current observations as a VPN fix, Cloud.ru migration, or accepted OBS daily run. The lead performed host diagnostics and final verification; the inexpensive built-in gpt-6-luna agent performed safety reviews and drafted the RU/EN checkpoint. Its cost is not exposed by the tool. DeepSeek was not used for proprietary network data; DeepSeek cost for this block: **$0**.

## Documentation checks and known local gate failure

The 22 added Markdown links, staged diff, secrets, and index hygiene were checked; independent review found no blocking issue in the eight documents. The owner change to `ds_worker.toml` was not staged and its SHA-256 remained unchanged.

Full `preflight --quick` ran but is not green: system Python 3.13 lacked `openai`; with existing Python 3.11 all seven service suites passed (LLM 56, NAS API 283, watchdog 44, backup 24/1 skipped, STT 17, VPN monitor 101, blackbox 317/6 skipped). The unit stage reported failures in different runs: `test_smart_monitor_target.py`, then `test_repo_hygiene.py` and `test_settings_compose.py`; the SMART test passed 4/4 in isolation and in its final retained output. The differences remain unexplained; code was not changed and the failures must not be called fixed. The preflight unit-error filter hides standard unittest tracebacks, so retain full output before repeating all gates.

The `.githooks/pre-commit` hook explicitly permits deliberate `--no-verify` with a commit-message explanation. This exception was used only for the local eight-file Markdown commit after focused checks, with the reason in the commit message. It is not a green gate or deployment authorization. ShellCheck is unavailable locally; Compose validation was skipped by standard `--quick`. Local diagnostic scripts and the SMART test log remain in the October 23 directory.
