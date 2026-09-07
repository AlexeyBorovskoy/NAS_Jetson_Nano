# GitVerse — NAS_HOME mirror

## Target

- Canonical code: GitHub `AlexeyBorovskoy/NAS_Jetson_Nano`
- Mirror: https://gitverse.ru/Alexey_Borovskoy/NAS_HOME  
- Remote name: **`gitverse`** (never pushurl on `origin`)
- Remote URL: `git@gitverse.ru:Alexey_Borovskoy/NAS_HOME.git` (SSH preferred)

## Auth (2026-09-07)

| Method | Status |
|---|---|
| HTTPS `oauth2:<TOKEN>` one-shot | ✅ works (token from local store, not git) |
| SSH `gitverse_ed25519` | ✅ OK (2026-09-07) — key `detecktor-belgorod@gitverse` |
| REST API Bearer | ✅ user/repos OK |

### SSH (verified 2026-09-07)

- Local key: `~/.ssh/gitverse_ed25519` (+ `.pub`, title `detecktor-belgorod@gitverse`).
- Owner registered pubkey in GitVerse UI: https://gitverse.ru/settings/keys
- `ssh -T -i … git@gitverse.ru` → authenticated as `Alexey_Borovskoy` (no shell).
- `git ls-remote git@gitverse.ru:Alexey_Borovskoy/NAS_HOME.git` → OK (`main`/`master`/`HEAD`).
- `~/.ssh/config` Host `gitverse.ru`: `IdentityFile ~/.ssh/gitverse_ed25519`, `IdentitiesOnly yes`.
- Remote: `git remote set-url gitverse git@gitverse.ru:Alexey_Borovskoy/NAS_HOME.git`

### HTTPS push fallback (token never in `.git/config`)

```powershell
# TOKEN only in memory — e.g. from password manager / local git.md (not committed)
git -c credential.helper= push "https://oauth2:${TOKEN}@gitverse.ru/Alexey_Borovskoy/NAS_HOME.git" HEAD:main
git -c credential.helper= push "https://oauth2:${TOKEN}@gitverse.ru/Alexey_Borovskoy/NAS_HOME.git" HEAD:master
```

```bash
git remote add gitverse git@gitverse.ru:Alexey_Borovskoy/NAS_HOME.git   # once (or HTTPS URL)
```

## Remote state

- After 2026-09-07 align: **`main`**, **`master`**, and default **HEAD** point to the same tip as GitHub `main` (force-align of `master` authorized by owner).
- Prefer developing on **`main`**; keep `master` = `main` on mirror.

## Do not

- Secrets / tokens in git history or remote URL in config.
- Use GitVerse Issues as family task SoR.
- Force-push without owner OK (except explicit align requests).
