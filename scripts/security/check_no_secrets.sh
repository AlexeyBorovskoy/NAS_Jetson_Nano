#!/usr/bin/env bash
set -euo pipefail

SECRET_ASSIGNMENT_PATTERN='[A-Z0-9_]*(API[_-]?KEY|SECRET|TOKEN|PASSWORD|BEARER)[A-Z0-9_]*[[:space:]]*[:=][[:space:]]*['"'"'"]?[A-Za-z0-9_./+=:@-]{16,}'
PRIVATE_KEY_PATTERN='-----BEGIN [A-Z ]*PRIVATE KEY-----'
PLACEHOLDER_PATTERN='(change_me|replace_me|example|mock|REDACTED|ВАШ_|x{8,}|X{8,})'
# *_FILE / *_PATH указывают на путь к секрету, а не на само значение —
# тот же паттерн (docker secrets, restic) уже используется в проекте
# (RESTIC_PASSWORD_FILE=/root/..., password_file: /run/secrets/...).
# Найдено 2026-08-30: check_no_secrets.sh ловил такие строки как ложные срабатывания
# на каждом коммите.
SECRET_FILE_REF_PATTERN='(API[_-]?KEY|SECRET|TOKEN|PASSWORD|BEARER)[A-Z0-9_]*_(FILE|PATH)[[:space:]]*[:=][[:space:]]*['"'"'"]?/'

# Сканируем только то, что git реально опубликует (tracked-файлы).
# Untracked/.gitignored (например локальный config/.env с реальными ключами)
# не являются риском публикации. Если секретный файл случайно git add-нут —
# он попадёт в список и будет пойман.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  file_list="$(git ls-files)"
else
  file_list="$(find . -type f -not -path './.git/*')"
fi

scan_files="$(printf '%s\n' "$file_list" \
  | grep -Ev '(^|/)\.env\.example$|(^|/)\.gitignore$|\.md$|\.zip$|(^|/)check_no_secrets\.sh$' \
  || true)"

matches=""
if [ -n "$scan_files" ]; then
  matches="$(printf '%s\n' "$scan_files" | tr '\n' '\0' \
    | xargs -0 grep -InE "$SECRET_ASSIGNMENT_PATTERN|$PRIVATE_KEY_PATTERN" 2>/dev/null || true)"
fi

matches="$(printf '%s\n' "$matches" | grep -Ev "$PLACEHOLDER_PATTERN" || true)"
matches="$(printf '%s\n' "$matches" | grep -Ev "$SECRET_FILE_REF_PATTERN" || true)"

if [ -n "$matches" ]; then
  printf '%s\n' "$matches"
  echo "Potential secret-like strings found. Review before publishing." >&2
  exit 1
fi

echo "No obvious secrets found outside allowed files."
