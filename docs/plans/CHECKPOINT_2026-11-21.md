# Checkpoint 2026-11-21: Codex on the VPS — working contours

[Русская версия](CHECKPOINT_2026-11-21.ru.md), [previous checkpoint](CHECKPOINT_2026-11-20_CODEX_VPS_PILOT.md)

The 2026-11-20 pilot ended in NO-GO because the sandbox would not start. The cause was traced to the end, the blocker was removed narrowly, and three working Codex CLI contours are now deployed on the same host. Logins are done, tasks really edit files, and VS Code connects to the server from both working contours.

## What was done

**Users and isolation.** `dev-personal` (personal), `dev-work` (work), `nil` (guest). Homes are `700`, each with its own `~/projects`, `CODEX_HOME` and `auth.json` (`600`). None of them has `sudo` or Docker access: `sudo -n true` asks for a password and `/var/run/docker.sock` does not exist. Verified that another user's home, another `auth.json` and `/root` are unreadable.

**Sandbox.** The pilot blocker was `kernel.apparmor_restrict_unprivileged_userns=1` plus bwrap without an attached profile. It was removed with a targeted AppArmor profile `/etc/apparmor.d/codex-dev-bwrap` for the exact binary path; no global relaxation, `danger-full-access` not allowed. The synthetic pilot profile is unchanged; `dev-personal-ws`, `dev-work-ws` and `nil-ws` were added — writes only inside `~/projects`, network enabled, other users' `.ssh` and `auth.json` denied.

**Two failures that cost time.** `codex sandbox` returned "Permission denied (os error 13)" because Codex inherited the working directory `/root` and tried to `chdir` there; it must be started from the project directory. And `default_permissions` in `/etc/codex/requirements.toml` must be listed in `allowed_permission_profiles`, otherwise startup fails before the command runs.

**Login.** OpenAI does not serve Russian addresses (`unsupported_country_region_territory`), so the browser signs in through the VPS itself (SOCKS), and the callback returns to `127.0.0.1:1455` over `ssh -L`, bypassing the proxy. `codex login` must run as a detached `systemd-run` unit — inside an SSH session it dies with the channel (two failed attempts). Both working contours report `Logged in using ChatGPT`.

**Verified by tasks, not by status lines.** In `dev-personal` and `dev-work`, `codex exec` modified `main.py` (sha256 `a55c14…` → `0f6c16…`); in `nil` it appended a line to `NOTES.md`, `git status` → `M NOTES.md`, 28 847 tokens.

**VS Code.** Remote-SSH was installed from a VSIX (the marketplace is unreachable over DNS) and needs two settings: `remote.SSH.path` pointing at the Git ssh client and `remote.SSH.remotePlatform = linux` for each profile. Without the second, VS Code asks for the platform, and choosing "Windows" yields `bash: line 1: powershell: command not found`. Windows `demo [SSH: VPS-Personal-socks]` and `demo [SSH: VPS-Work-socks]` are open.

**Git.** Everything under the owner's account: private repositories `codex-vps-test-personal`, `codex-vps-test-work`, `codex-vps-test-son`. Access is by deploy keys scoped to a single repository (`read-write`); no account-wide key was placed on the server. Identities are separate; commits `c232cd93`, `87b4525f`, `0ceb397`, `82bb18b` reached GitHub.

**Guest contour.** The key and the documentation are handed over in the `nil/` folder at the project root — it is in `.gitignore` (`/nil/`), so the private key never reaches git. A separate Codex login is not required: the contour holds a copy of an already completed login in `~/.codex/auth.json`; the limitation is that token rotation may require signing in again.

## Network caveat

New SSH connections from the home network are cut during banner exchange (the same defect as in the D2 report), while an already established tunnel keeps working. The working route is the `VPS-*-socks` profiles with `ProxyCommand connect -S 127.0.0.1:1080`, which require a live `ssh -N -D 1080 aeza-sweden`. The same route carried the deployment when the direct channel failed nine attempts in a row.

## Remaining

1. First run by the recipient following the document — a VS Code window with their folder and a modified file after a Codex task.
2. Owner decision on the family VPN DNS record: `VPN_DOMAIN` has been missing since 2026-11-21 08:48 UTC, clients cannot connect by name (`CS-D2-1`, awaiting decision).
3. End-to-end check from the second (Linux) laptop — only possible from the corporate network.

## Scope boundaries

Unchanged: `sshd_config`, firewall, sing-box, nginx, AmneziaWG, server-side DNS and existing users. No bulk Ubuntu upgrades. The deployment documents (`STATUS.md`, `OPERATIONS.md`, `CODEX_VPS_MACOS_SETUP.md`) live in `artifacts/deploy/codex-vps-2026-11-21/` and deliberately stay out of git: the `/artifacts/` path is excluded by the hygiene policy.
