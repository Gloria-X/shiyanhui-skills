#!/usr/bin/env bash
# Install the single production skill; never log in to the platform or use sudo.
set -euo pipefail
umask 077

skill_name='shiyanhui-platform'
skill_version='2026-11-09-53d418f44e7d'
expected_sha256='53d418f44e7d2009ad72768ff6892430e57243af162bc942fdd3b2c9fb8d927a'
github_url='https://raw.githubusercontent.com/Gloria-X/shiyanhui-skills/a9ae3cb5028d7f7f89669d1603f3ec9e01b7bc46/shiyanhui-platform/SKILL.md'
platform_origin="${1:-http://192.168.0.158}"
platform_origin="${platform_origin%/}"
if [[ $# -gt 1 || ! "$platform_origin" =~ ^https?://(\[[0-9a-fA-F:]+\]|[a-zA-Z0-9.-]+)(:[0-9]+)?$ ]]; then
  printf '%s\n' 'Usage: bash install.sh [http(s)://platform-host[:port]]' >&2
  exit 1
fi

command -v curl >/dev/null || { printf '%s\n' 'curl is required.' >&2; exit 1; }
if command -v sha256sum >/dev/null; then
  checksum_command=(sha256sum)
elif command -v shasum >/dev/null; then
  checksum_command=(shasum -a 256)
else
  printf '%s\n' 'sha256sum or shasum is required.' >&2
  exit 1
fi

skill_home="${CODEX_HOME:-$HOME/.codex}"
if [[ "$skill_home" != /* ]]; then
  printf '%s\n' 'CODEX_HOME must be an absolute path.' >&2
  exit 1
fi
destination="$skill_home/skills/$skill_name"

file_sha256() {
  "${checksum_command[@]}" "$1" | awk '{print $1}'
}

if [[ -L "$destination" || -L "$destination/SKILL.md" ]]; then
  printf '%s\n' 'Refusing to replace a symbolic link.' >&2
  exit 1
fi
if [[ -e "$destination" ]]; then
  if [[ -f "$destination/SKILL.md" && "$(file_sha256 "$destination/SKILL.md")" == "$expected_sha256" ]]; then
    printf 'Already installed: %s (%s)\n' "$skill_name" "$skill_version"
    exit 0
  fi
  printf 'Existing skill was preserved: %s. Review it before updating.\n' "$destination" >&2
  exit 1
fi

temporary_directory=$(mktemp -d)
trap 'rm -rf -- "$temporary_directory"' EXIT
download_file="$temporary_directory/SKILL.md"
download_source='MinIO'
if ! curl --fail --silent --show-error --location --proto '=http,https' --proto-redir '=http,https' \
  --connect-timeout 3 --max-time 15 --max-filesize 131072 \
  "$platform_origin/api/platform-skill/SKILL.md" --output "$download_file" \
  || [[ "$(file_sha256 "$download_file")" != "$expected_sha256" ]]; then
  printf '%s\n' 'MinIO unavailable or verification failed; trying the pinned GitHub version.' >&2
  download_source='GitHub'
  curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
    --connect-timeout 5 --max-time 30 --max-filesize 131072 \
    "$github_url" --output "$download_file"
fi

if [[ "$(file_sha256 "$download_file")" != "$expected_sha256" ]]; then
  printf '%s\n' 'SHA256 mismatch; no skill was installed.' >&2
  exit 1
fi

mkdir -p "$skill_home/skills"
# mkdir is exclusive: a concurrent install must never overwrite another skill.
mkdir "$destination"
if ! install -m 600 "$download_file" "$destination/SKILL.md"; then
  rmdir "$destination" 2>/dev/null || true
  exit 1
fi
printf 'Installed %s (%s) from %s into %s\n' "$skill_name" "$skill_version" "$download_source" "$destination"
printf '%s\n' 'The skill is available on your next Codex turn. Restart Codex if it is not listed.'
