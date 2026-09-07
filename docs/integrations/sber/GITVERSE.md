# GitVerse — NAS_HOME mirror

## Target

- Canonical code: GitHub `AlexeyBorovskoy/NAS_Jetson_Nano`
- Mirror: https://gitverse.ru/Alexey_Borovskoy/NAS_HOME  
- Remote name: **`gitverse`** (never pushurl on `origin`)
- Remote URL (no credentials): `https://gitverse.ru/Alexey_Borovskoy/NAS_HOME.git`

## Auth (2026-09-07)

| Method | Status |
|---|---|
| HTTPS `oauth2:<TOKEN>` one-shot | ✅ works (token from local store, not git) |
| SSH `gitverse_ed25519` | ❌ pubkey not registered on account |
| REST API Bearer | ✅ user/repos OK |

### HTTPS push (token never in `.git/config`)

```powershell
# TOKEN only in memory — e.g. from password manager / local git.md (not committed)
git -c credential.helper= push "https://oauth2:${TOKEN}@gitverse.ru/Alexey_Borovskoy/NAS_HOME.git" HEAD:main
git -c credential.helper= push "https://oauth2:${TOKEN}@gitverse.ru/Alexey_Borovskoy/NAS_HOME.git" HEAD:master
```

```bash
git remote add gitverse https://gitverse.ru/Alexey_Borovskoy/NAS_HOME.git   # once
```

## Remote state

- After 2026-09-07 align: **`main`**, **`master`**, and default **HEAD** point to the same tip as GitHub `main` (force-align of `master` authorized by owner).
- Prefer developing on **`main`**; keep `master` = `main` on mirror.

## Do not

- Secrets / tokens in git history or remote URL in config.
- Use GitVerse Issues as family task SoR.
- Force-push without owner OK (except explicit align requests).
