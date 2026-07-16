#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/external_docs"

mkdir -p \
  "${OUT_DIR}/jetson" \
  "${OUT_DIR}/docker" \
  "${OUT_DIR}/nextcloud/groupware" \
  "${OUT_DIR}/immich" \
  "${OUT_DIR}/deepseek" \
  "${OUT_DIR}/protocols" \
  "${OUT_DIR}/nas" \
  "${OUT_DIR}/backup" \
  "${OUT_DIR}/alternatives"

fetch() {
  local url="$1"
  local out="$2"

  if [ -s "$out" ]; then
    printf 'SKIP %s\n' "$out"
    return 0
  fi

  printf 'GET  %s\n' "$out"
  curl -fL --retry 2 --connect-timeout 20 --max-time 120 \
    -A 'NAS_Jetson_Nano-home-cloud-doc-cache/0.1' \
    "$url" \
    -o "$out"
}

cat > "${OUT_DIR}/jetson/README_JETSON_LINKS.md" <<'EOL'
# Jetson Nano reference links

- Get Started With Jetson Nano Developer Kit:
  https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit

- Jetson Nano Developer Kit SD Card Image:
  https://developer.nvidia.com/jetson-nano-sd-card-image

- Jetson Download Center:
  https://developer.nvidia.com/embedded/downloads

- Jetson Linux / L4T 32.7.6 Archive Docs:
  https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3276/index.html

- Jetson Linux Archive:
  https://developer.nvidia.com/embedded/jetson-linux-archive
EOL

cat > "${OUT_DIR}/docker/DOCKER_LINKS.md" <<'EOL'
# Docker reference links

- Docker Engine on Ubuntu: https://docs.docker.com/engine/install/ubuntu/
- Docker Compose plugin on Linux: https://docs.docker.com/compose/install/linux/
- Compose file reference: https://docs.docker.com/reference/compose-file/
- Docker Linux post-installation: https://docs.docker.com/engine/install/linux-postinstall/
EOL

cat > "${OUT_DIR}/nextcloud/NEXTCLOUD_LINKS.md" <<'EOL'
# Nextcloud reference links

- Administration Manual: https://docs.nextcloud.com/server/latest/admin_manual/
- User Manual: https://docs.nextcloud.com/server/latest/user_manual/en/
- System requirements: https://docs.nextcloud.com/server/latest/admin_manual/installation/system_requirements.html
- Installation on Linux: https://docs.nextcloud.com/server/latest/admin_manual/installation/source_installation.html
- WebDAV access: https://docs.nextcloud.com/server/latest/user_manual/en/files/access_webdav.html
- Docker repository: https://github.com/nextcloud/docker
- Documentation repository: https://github.com/nextcloud/documentation
EOL

cat > "${OUT_DIR}/nextcloud/groupware/NEXTCLOUD_GROUPWARE_LINKS.md" <<'EOL'
# Nextcloud Contacts / Calendar / DAVx5 links

- Nextcloud Contacts: https://apps.nextcloud.com/apps/contacts
- Nextcloud Calendar: https://apps.nextcloud.com/apps/calendar
- DAVx5: https://www.davx5.com/
- DAVx5 Manual: https://manual.davx5.com/
- DAVx5 tested with Nextcloud: https://www.davx5.com/tested-with/nextcloud
EOL

cat > "${OUT_DIR}/deepseek/DEEPSEEK_LINKS.md" <<'EOL'
# DeepSeek API reference links

- Quick Start: https://api-docs.deepseek.com/
- Models & Pricing: https://api-docs.deepseek.com/quick_start/pricing
- Chat Completion API: https://api-docs.deepseek.com/api/create-chat-completion
- Reasoning / Thinking mode: https://api-docs.deepseek.com/guides/reasoning_model
- JSON output: https://api-docs.deepseek.com/guides/json_mode
- Tool calls: https://api-docs.deepseek.com/guides/function_calling
- Context caching: https://api-docs.deepseek.com/guides/kv_cache
EOL

cat > "${OUT_DIR}/nas/NAS_LINKS.md" <<'EOL'
# NAS / Samba / SFTP reference links

- Samba smb.conf manual: https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html
- Samba documentation: https://www.samba.org/samba/docs/
- OpenSSH manual pages: https://www.openssh.org/manual.html
- sshd_config manual: https://man.openbsd.org/sshd_config
- OpenSSH project: https://www.openssh.com/
EOL

cat > "${OUT_DIR}/backup/RESTIC_LINKS.md" <<'EOL'
# restic reference links

- Documentation: https://restic.readthedocs.io/en/latest/
- Preparing a new repository: https://restic.readthedocs.io/en/latest/030_preparing_a_new_repo.html
- Backing up: https://restic.readthedocs.io/en/latest/040_backup.html
- Restoring from backup: https://restic.readthedocs.io/en/latest/050_restore.html
- Forget: https://restic.readthedocs.io/en/latest/060_forget.html
- GitHub: https://github.com/restic/restic
EOL

cat > "${OUT_DIR}/alternatives/ALTERNATIVES_LINKS.md" <<'EOL'
# Alternative self-hosted solutions

- Seafile: https://www.seafile.com/en/home/
- Seafile Manual: https://manual.seafile.com/
- Syncthing: https://syncthing.net/
- Syncthing Docs: https://docs.syncthing.net/
- PhotoPrism: https://www.photoprism.app/
- PhotoPrism Docs: https://docs.photoprism.app/
- OpenMediaVault: https://www.openmediavault.org/
- OpenMediaVault Docs: https://docs.openmediavault.org/en/latest/
- TrueNAS: https://www.truenas.com/
- TrueNAS Docs: https://www.truenas.com/docs/
- File Browser: https://filebrowser.org/
- Vaultwarden: https://github.com/dani-garcia/vaultwarden
EOL

fetch https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit "${OUT_DIR}/jetson/get-started-jetson-nano-devkit.html"
fetch https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3276/index.html "${OUT_DIR}/jetson/l4t-3276-index.html"

fetch https://docs.docker.com/engine/install/ubuntu/ "${OUT_DIR}/docker/docker-engine-ubuntu.html"
fetch https://docs.docker.com/compose/install/linux/ "${OUT_DIR}/docker/docker-compose-linux.html"
fetch https://docs.docker.com/reference/compose-file/ "${OUT_DIR}/docker/compose-file-reference.html"
fetch https://docs.docker.com/engine/install/linux-postinstall/ "${OUT_DIR}/docker/docker-linux-postinstall.html"

fetch https://docs.nextcloud.com/server/latest/admin_manual/ "${OUT_DIR}/nextcloud/admin-manual.html"
fetch https://docs.nextcloud.com/server/latest/admin_manual/installation/system_requirements.html "${OUT_DIR}/nextcloud/system-requirements.html"
fetch https://docs.nextcloud.com/server/latest/admin_manual/installation/source_installation.html "${OUT_DIR}/nextcloud/source-installation.html"
fetch https://docs.nextcloud.com/server/latest/user_manual/en/files/access_webdav.html "${OUT_DIR}/nextcloud/webdav-access.html"
fetch https://apps.nextcloud.com/apps/contacts "${OUT_DIR}/nextcloud/groupware/contacts-app.html"
fetch https://apps.nextcloud.com/apps/calendar "${OUT_DIR}/nextcloud/groupware/calendar-app.html"
fetch https://manual.davx5.com/ "${OUT_DIR}/nextcloud/groupware/davx5-manual.html"
fetch https://www.davx5.com/tested-with/nextcloud "${OUT_DIR}/nextcloud/groupware/davx5-nextcloud.html"

fetch https://docs.immich.app/install/requirements/ "${OUT_DIR}/immich/requirements.html"
fetch https://docs.immich.app/install/docker-compose/ "${OUT_DIR}/immich/docker-compose-install.html"
fetch https://docs.immich.app/administration/backup-and-restore/ "${OUT_DIR}/immich/backup-and-restore.html"
fetch https://docs.immich.app/features/mobile-backup/ "${OUT_DIR}/immich/mobile-backup.html"
fetch https://github.com/immich-app/immich/releases/latest/download/docker-compose.yml "${OUT_DIR}/immich/immich-docker-compose.yml"
fetch https://github.com/immich-app/immich/releases/latest/download/example.env "${OUT_DIR}/immich/immich-example.env"

fetch https://api-docs.deepseek.com/ "${OUT_DIR}/deepseek/quick-start.html"
fetch https://api-docs.deepseek.com/quick_start/pricing "${OUT_DIR}/deepseek/pricing.html"
fetch https://api-docs.deepseek.com/api/create-chat-completion "${OUT_DIR}/deepseek/create-chat-completion.html"
fetch https://api-docs.deepseek.com/guides/reasoning_model "${OUT_DIR}/deepseek/reasoning-model.html"
fetch https://api-docs.deepseek.com/guides/json_mode "${OUT_DIR}/deepseek/json-mode.html"
fetch https://api-docs.deepseek.com/guides/function_calling "${OUT_DIR}/deepseek/function-calling.html"
fetch https://api-docs.deepseek.com/guides/kv_cache "${OUT_DIR}/deepseek/context-caching.html"

fetch https://www.rfc-editor.org/rfc/rfc4918.txt "${OUT_DIR}/protocols/rfc4918-webdav.txt"
fetch https://www.rfc-editor.org/rfc/rfc4791.txt "${OUT_DIR}/protocols/rfc4791-caldav.txt"
fetch https://www.rfc-editor.org/rfc/rfc6352.txt "${OUT_DIR}/protocols/rfc6352-carddav.txt"
fetch https://www.rfc-editor.org/rfc/rfc5545.txt "${OUT_DIR}/protocols/rfc5545-icalendar.txt"
fetch https://www.rfc-editor.org/rfc/rfc6350.txt "${OUT_DIR}/protocols/rfc6350-vcard.txt"

fetch https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html "${OUT_DIR}/nas/samba-smbconf.html"
fetch https://www.openssh.org/manual.html "${OUT_DIR}/nas/openssh-manual.html"
fetch https://man.openbsd.org/sshd_config "${OUT_DIR}/nas/sshd_config.html"

fetch https://restic.readthedocs.io/en/latest/ "${OUT_DIR}/backup/restic-index.html"
fetch https://restic.readthedocs.io/en/latest/030_preparing_a_new_repo.html "${OUT_DIR}/backup/restic-030-preparing-repo.html"
fetch https://restic.readthedocs.io/en/latest/040_backup.html "${OUT_DIR}/backup/restic-040-backup.html"
fetch https://restic.readthedocs.io/en/latest/050_restore.html "${OUT_DIR}/backup/restic-050-restore.html"
fetch https://restic.readthedocs.io/en/latest/060_forget.html "${OUT_DIR}/backup/restic-060-forget.html"

find "${OUT_DIR}" -type f | sort | xargs sha256sum > "${OUT_DIR}/SHA256SUMS.local"
printf 'External documentation cache updated: %s\n' "${OUT_DIR}"
