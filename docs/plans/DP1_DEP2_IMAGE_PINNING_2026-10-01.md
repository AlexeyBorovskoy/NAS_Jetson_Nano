# DP-1 / DEP-2 — immutable container images

Date: 2026-10-01 (Europe/Moscow).  Scope: external images referenced by the
Jetson and project VPS Compose files.  Local `build:` services are outside this
registry-image control.

## Outcome

All 22 `image:` references under `docker/compose/` and `docker/vps/` are pinned
as `tag@sha256:<manifest-digest>`.  The tag remains readable for operators; the
digest is the deploy identity.  `scripts/quality/preflight.sh --images-only` is
now a blocking gate for an absent or malformed digest and scans both locations.

No container, database, volume, network, or VPN configuration was changed while
collecting the evidence.  The chosen Jetson and VPS digests are the content
already running, so applying the Compose files does not imply an application or
schema upgrade.

## Evidence and selected identities

The running identity was read with `docker inspect`; application versions were
read from container metadata or read-only version/status commands.  Coturn and
the optional ROG Immich ML worker were not running and their multi-platform
manifest-list digests were resolved from the registry with
`docker buildx imagetools inspect`.

| Image | Operator tag / observed version | Pinned digest | Evidence source |
|---|---|---|---|
| Immich server | `v2.7.5` | `c15bff75068effb03f4355997d03dc7e0fc58720c2b54ad6f7f10d1bc57efaa5` | Jetson running RepoDigest and image version label |
| Immich ML CUDA | `v2.7.5-cuda` | `304142175e345f0155d7642f637cfdceae60e89075ff03938cb2886d52c65a62` | GHCR manifest index, amd64 payload present |
| pgvecto-rs | `pg16-v0.3.0` | `b89f8ddbb28400d428d3c5e3e860f578cde85ad8e78544a8b687b97937cfc50b` | Jetson running RepoDigest |
| Redis | `7-alpine`; observed `7.4.9` | `6ab0b6e7381779332f97b8ca76193e45b0756f38d4c0dcda72dbb3c32061ab99` | Jetson running RepoDigest and `redis-server --version` |
| PostgreSQL (Nextcloud) | `16-alpine`; observed `16.14` | `16bc17c64a573ef34162af9298258d1aec548232985b33ed7b1eac33ba35c229` | Jetson running RepoDigest and `postgres --version` |
| Nextcloud | `33.0.4-apache` | `caa40b8beaf0057ac213d8dfc515c36ce64f7a8f0825b6a287e6f7cf2f4a095d` | Jetson running RepoDigest and `occ status` (`needsDbUpgrade=false`) |
| Netdata | observed `v2.10.0-480-nightly` | `0c2d00b4ceb8d247251986ae05d08c92c65abff18bf081929f853de310aa5918` | Jetson running RepoDigest and `netdata -W buildinfo` |
| Uptime Kuma | deployed major tag `1` | `3d632903e6af34139a37f18055c4f1bfd9b7205ae1138f1e5e8940ddc1d176f9` | Jetson running RepoDigest |
| Portainer CE | deployed `latest`, revision `e1de8b4` | `d27f76194b719bfe2a34779d51798a7adf02510cfba69ebcb538267f75aa4f47` | Jetson running RepoDigest and OCI labels |
| Samba | observed `4.22.8` | `40591f9a30df6b0106948d81d89204c632894387639914ec2808b536e307074b` | Jetson running RepoDigest and `smbd --version` |
| Nginx | observed `1.31.2` | `20316569d8f81a160065d7d2a5eeffc7ca97d79022462ee255fd23fa103a6b5c` | VPS running RepoDigest and `nginx -v` |
| Beszel Hub | `0.18.7` | `a849ad80814b6a1a3be665304dcace5d4854b3bed7bde4dd1227e8ce1b82d477` | VPS running RepoDigest and OCI version label |
| Coturn | `alpine` | `c29135c08565810d37053f384584392b7c24b69570fc81a721b878d6fe63e04e` | Docker Hub multi-platform manifest list |

The Immich database uses a different PostgreSQL build (`16.8`, Debian base)
inside the pgvecto-rs image.  It was not replaced by the Nextcloud PostgreSQL
image; each existing service retains its measured image identity.

## Verification

Commands (no secret values are printed):

```text
python tests/unit/test_immich_pinned_version.py
bash scripts/quality/preflight.sh --images-only
docker compose -f <each compose file> --env-file config/.env.example config --quiet
docker buildx imagetools inspect <each unique tag@digest reference>
bash scripts/quality/preflight.sh
```

Expected results:

- repository static test finds 22 pinned references;
- seven positive/negative gate tests pass;
- all 13 unique registry references resolve by digest;
- all Compose files render with validation-only placeholders for required
  secrets; no rendered configuration is stored;
- the full local quality gate passes before deployment.

## Deployment and rollback

The safe deployment updates only version-controlled Compose text.  It does not
run `pull`, `up`, `restart`, or recreate a container.  Current running content
already matches the selected digests.  The next planned maintenance operation
will therefore resolve the same content instead of following a moving tag.

Rollback is `git revert <DP-1/DEP-2 commit>`.  Do not roll an application image
back after a future stateful upgrade unless its database/volume backup from the
same point in time is also restored.
