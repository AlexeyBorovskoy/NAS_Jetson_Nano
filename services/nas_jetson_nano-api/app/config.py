import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    api_port: int = 8099
    api_log_level: str = "INFO"

    # Log file inside container — mount as volume to persist on host
    log_file: str = "/var/log/nas_jetson_nano-monitor/nas_jetson_nano-api.jsonl"
    log_max_bytes: int = 10 * 1024 * 1024  # 10 MB per file
    log_backup_count: int = 5

    # JWT auth — secret should be set via NAS_JETSON_NANO_API_JWT_SECRET in .env
    # If not set, a random secret is generated (tokens lost on container restart).
    jwt_secret: str = secrets.token_hex(32)
    jwt_ttl_hours: int = 24

    # Nextcloud internal URL for OCS credential validation
    # Inside docker network: http://homecloud_nextcloud:80 or via host-gateway
    nextcloud_internal_url: str = "http://host.docker.internal:8080"

    # Space-separated list of expected container names
    expected_containers: str = (
        "homecloud_nextcloud "
        "homecloud_nextcloud_db "
        "homecloud_nextcloud_redis "
        "homecloud_immich_server "
        "homecloud_immich_microservices "
        "homecloud_immich_db "
        "homecloud_immich_redis "
        "homecloud_llm_gateway "
        "homecloud_nasa_api "
        "homecloud_samba "
        "homecloud_netdata "
        "homecloud_uptime_kuma "
        "homecloud_portainer"
    )

    # Telegram report integration
    report_cmd: str = "/usr/local/sbin/nas_jetson_nano-send-report-telegram.sh"

    # Services to HTTP-check
    local_services: str = (
        "Nextcloud=http://host.docker.internal:8080/ "
        "Immich=http://host.docker.internal:2283/ "
        "LLM-Gateway=http://host.docker.internal:8090/health"
    )

    # Nextcloud admin credentials (for Talk API and user management)
    nextcloud_admin_user: str = "admin"
    nextcloud_admin_password: str = ""  # Set via NEXTCLOUD_ADMIN_PASSWORD

    # Talk (Nextcloud spreed) — default family room token
    talk_family_room: str = "37pcobmf"

    # ── Talk AI bot (Phase A, polling) ──────────────────────────────────────
    # Disabled by default: enabling starts a background long-poll loop that
    # reads the family room and answers simple commands (ping, статус, диск, фото).
    talk_bot_enabled: bool = False
    # Room the bot listens to; empty → falls back to talk_family_room.
    talk_bot_room: str = ""
    # Optional command prefix (e.g. "нас" → "нас статус"). Empty = match a
    # known command as the first word of the message.
    talk_bot_trigger: str = ""
    # Display name the bot posts replies under.
    talk_bot_display_name: str = "NAS Bot"
    # Server-side long-poll timeout in seconds (how long a read call waits).
    talk_bot_poll_timeout: int = 30

    # ── Talk AI bot (Phase C, free-form questions → DeepSeek) ───────────────
    # A SECOND, deliberately separate callsign. The privacy boundary is the word
    # you type: `talk_bot_trigger` answers from local data and never leaves the
    # house; this one goes out to the provider through the redaction gateway.
    # Empty = feature off (the bot stays local-only).
    # Space-separated room tokens. Each family member can have their OWN private
    # room with the bot; the bot polls them all in parallel. Empty → single room
    # from talk_bot_room / talk_family_room.
    talk_bot_rooms: str = ""
    talk_bot_llm_trigger: str = ""  # e.g. "@бобик"
    # Display name used for LLM replies, so the family can tell them apart.
    talk_bot_llm_display_name: str = "Бобик"
    # Redaction gateway endpoint — the ONLY outbound door.
    talk_bot_llm_url: str = "http://host.docker.internal:8090/v1/chat"
    talk_bot_llm_timeout: int = 60
    # Guard against a wall-of-text question inflating the bill.
    talk_bot_llm_max_chars: int = 1000
    # Second budget guard, at bot level: max LLM replies per day. 0 = unlimited.
    talk_bot_llm_daily_replies: int = 50
    # Картинки генерируются заметно дольше текста.
    talk_bot_image_timeout: int = 300

    # Immich internal URL and API key
    immich_internal_url: str = "http://host.docker.internal:2283"
    immich_api_key: str = ""  # Set via IMMICH_API_KEY (generate in Immich → API Keys)

    # Backup script path (for POST /v1/actions/backup/now)
    backup_cmd: str = "/home/admin/nas_jetson_nano/scripts/backup/backup_databases.sh"

    # Whitelist of containers allowed to be restarted via API
    restartable_containers: str = (
        "homecloud_nextcloud "
        "homecloud_nextcloud_db "
        "homecloud_nextcloud_redis "
        "homecloud_immich_server "
        "homecloud_immich_microservices "
        "homecloud_llm_gateway "
        "homecloud_nasa_api "
        "homecloud_samba "
        "homecloud_netdata "
        "homecloud_uptime_kuma"
    )


settings = Settings()
