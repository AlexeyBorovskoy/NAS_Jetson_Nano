# Migration to NAS_Jetson_Nano

> Repository rename status: completed in source. Live runtime migration: pending a separate controlled deployment window.

## What changed

- Product and repository name: `NAS_Jetson_Nano`.
- Machine-safe identifiers: `nas_jetson_nano`.
- Environment-variable prefix: `NAS_JETSON_NANO_`.
- API service, Compose file, scripts, logs, systemd unit source files, documentation, and publication artifacts were renamed consistently.

## What did not change in this step

- The running Jetson was not redeployed or restarted.
- Installed units under `/etc/systemd/system` were not replaced.
- Runtime directories under `/home/admin` and `/opt` were not moved.
- Docker containers and volumes were not renamed or recreated.
- The reverse SSH tunnel, router, firewall, and family VPN were not changed.

This separation is intentional: renaming source code is reversible, while renaming live units, containers, paths, and monitoring targets can interrupt the working home cloud.

## Required follow-up

Perform the live migration as a separate small-step operation:

1. Create and verify a clean Git checkpoint.
2. Inventory installed legacy units, runtime paths, containers, logs, and timers read-only.
3. Prepare compatibility links or parallel units where required.
4. Deploy one technical block at a time.
5. Verify storage preflight, databases, all containers, monitoring, backup, and reverse access after every block.
6. Remove legacy runtime names only after a full reboot/autorecovery acceptance test and an explicit user confirmation.

## Rollback

Until the live migration is completed, the installed runtime continues using its existing names. Repository rollback is performed through the Git commit preceding the rename; live rollback must restore the previously installed unit files and paths without touching data volumes.
