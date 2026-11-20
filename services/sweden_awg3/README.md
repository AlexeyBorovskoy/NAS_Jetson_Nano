# AmneziaWG 3.1 — standalone Linux service template (public)

Public description of a service template for a separate Linux host running the
userspace AmneziaWG 3.1 daemon.

> **Status:** template published for review and reuse. This document describes the
> template itself, not a live host inventory. It makes no claim of external
> acceptance and no claim of production readiness. It contains no credentials,
> keys or host identity.

## Contents

| File | Purpose |
|---|---|
| `awg_material.py` | profile generation and provisioning |
| `awg_control.py` | daemon configuration over UAPI and status output |
| two systemd units | the daemon and a separate exact-scoped NAT |

### `awg_material.py`

- `generate(count, endpoint, port=7843, subnet="10.73.3.0/24")` returns secret
  material **in memory only**.
- `provision(root, endpoint)` writes **23** profiles with mode `0600` and refuses
  to run when credentials already exist.
- The `root` directory is supplied by the caller from outside this repository;
  nothing secret enters git.

### `awg_control.py`

- Configures the UAPI and requires `errno 0` from every call.
- Validates the readback: **23** peers, header protection enabled, random
  trailers enabled, cookies enabled.
- `status` prints only aggregate counters, the listen port and protection flags — never key material.

### systemd units

The two units are deliberately separate: one runs the daemon, the other applies
the exact-scoped NAT. Stopping the service therefore removes exactly those NAT
rules and nothing else.

## Fixed template parameters

These are constants of the template, not a description of any particular
deployment:

- AmneziaWG **3.1**, standalone userspace service;
- **23** peers (fixed);
- UDP port **7843**;
- interface **awgse0**;
- server address **10.73.3.1/24** (subnet **10.73.3.0/24**);
- WAN interface **enp0s3**;
- root-owned working directory **/opt/amnezia-awg3-sweden**.

## Build provenance

- Static official `amneziawg-go` built from tag **3.1.20261116** — upstream:
  <https://github.com/amnezia-vpn/amneziawg-go/tree/v3.1.20261116>
- amd64 image: digest
  `sha256:90f2b73334ea4e5baa5e318f5797f06bfb1dd7e8627ef50ad50cdf06a381e9c9`
- binary: SHA256
  `4e2993bab96f521f8a04a1a312da732db97b8f1dca10fdd78d524fa891283258`
- Known cosmetic discrepancy: `--version` of the binary prints a stale
  `0.0.20250522` even though it is built from tag `3.1`. This is documented
  upstream in `version.go`, not a build error on our side.

No binaries and no credentials are committed to this repository.

## Prerequisites

- `python3` with the `cryptography` package;
- `iproute2`, `iptables`, `systemd`, TUN support;
- `curl` — only for the optional manual acceptance check;
- Python requirements file: `services/sweden_awg3/requirements.txt`.

## Installation — manual only

There is no automated installer, and this document deliberately contains no
single command that modifies a host. A deployment requires, in advance:

1. a prior audit of the target host;
2. conflict checks on the UDP port (7843), the subnet (10.73.3.0/24) and the
   interface names;
3. explicit network approval;
4. a secure backup of the generated profiles.

## Running the service

Starting the main service also adds the exact-scoped NAT rules; the separate NAT
unit removes exactly those rules on stop.

The following remain separate, explicit approvals and are **not** installed
automatically:

- the inbound UDP rule in UFW;
- the egress route;
- a persistent `ip_forward` setting.

## Tests

```bash
python -m unittest discover -s tests/sweden_awg3 -v
```

`accept_clients.py` is an **optional** root integration test. It requires:

- an explicit `AWG_ENDPOINT` environment variable containing an IPv4 address;
- the fixed 23-config directory;
- a temporary `awgst` network namespace, a `veth` pair on `10.203.31.0/30` and
  local VPN clients, DNS `1.1.1.1`, and HTTPS `api.ipify.org`.

It makes no firewall changes, but it **does** create temporary routes and
interfaces on the host, so it requires an approved maintenance window and must
never run in CI.

## Limits of the evidence

The synthetic same-host test does **not** prove:

- reachability from mobile carrier networks;
- IPv6 leak prevention;
- behaviour across a reboot;
- operation under simultaneous load of all 23 clients.

These are open items for a future acceptance, not claims made by this template.

## Rollback (manual)

1. `systemctl disable --now amnezia-awg3-sweden.service` — the NAT unit removes
   its exact rule on stop.
2. Remove only the newly added UFW rules and the new sysctl file, after checking
   what depends on them.

Never flush the whole firewall and never disable forwarding blindly. Preserve
the private profile backup and the previous VPN until the new service has been
verified.
