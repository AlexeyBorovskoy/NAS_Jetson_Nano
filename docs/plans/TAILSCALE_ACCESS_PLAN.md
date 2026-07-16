# План: Tailscale внешний доступ к Jetson Nano / Tailscale External Access Plan

> ⚠️ 🇷🇺 **УСТАРЕЛО (2026-06-21).** Tailscale не реализован. Вместо него выбран VPS + autossh reverse SSH tunnel (ADR-0005). Файл сохранён как исторический референс.
> ⚠️ 🇬🇧 **OBSOLETE (2026-06-21).** Tailscale was not implemented. Replaced by VPS + autossh reverse SSH tunnel (ADR-0005). File kept as historical reference.
>
> Актуальный план внешнего доступа: [docs/plans/VPS_INTEGRATION_PLAN.md](VPS_INTEGRATION_PLAN.md)  
> Архитектурное решение: [docs/decisions/ADR-0005-vps-autossh-reverse-tunnel.md](../decisions/ADR-0005-vps-autossh-reverse-tunnel.md)

---

**Статус:** ~~Запланировано (Stage 2)~~ → **Заменено ADR-0005**
**Решение:** ADR-0004 (Superseded)
**Дата:** 2026-06-20

---

## Цель (исторически)

Настроить внешний доступ к Nextcloud/Immich/LLM Gateway через мобильный интернет без нарушения LAN-конфигурации и Amnezia VPN семьи.

## Почему не реализовано

1. VPS уже присутствует в проекте (Amnezia на 193.8.215.130).
2. Tailscale передаёт трафик через DERP-серверы — третья сторона видит метаданные соединений.
3. Reverse SSH через уже имеющийся VPS проще, полностью под контролем, без аккаунтов.

## Этапы (для референса)

### Шаг 1: Аккаунт Tailscale

Зарегистрироваться на https://tailscale.com (Google/GitHub).

### Шаг 2: Установка на Jetson

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4   # запомнить Tailscale IP (100.x.x.x)
sudo systemctl enable tailscaled
```

### Шаг 3: Android

Play Store → "Tailscale" → войти с тем же аккаунтом.

### Rollback

```bash
sudo tailscale down
sudo apt remove tailscale
```

Amnezia и `nas_jetson_nano-lan` остаются нетронутыми.
