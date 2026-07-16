# ADR-0004: Tailscale для внешнего доступа (Stage 2)
# ADR-0004: Tailscale for External Access (Stage 2)

## Статус / Status

🇷🇺 **Заменено** ADR-0005 (2026-06-21). Tailscale не реализован — выбран VPS + autossh reverse SSH tunnel. Причина: данные Tailscale проходят через DERP-серверы третьей стороны; VPS уже есть в проекте.
🇬🇧 **Superseded** by ADR-0005 (2026-06-21). Tailscale was not implemented — VPS + autossh reverse SSH tunnel chosen instead. Reason: Tailscale traffic goes through third-party DERP servers; the project already has a VPS.

> 🇷🇺 См. / 🇬🇧 See: [ADR-0005-vps-autossh-reverse-tunnel.md](ADR-0005-vps-autossh-reverse-tunnel.md)

## Контекст / Context

🇷🇺 После провала двух VPN-попыток (ADR-0003) нужно решение для внешнего доступа из мобильной сети. Требования: CGNAT-proof, не трогает Amnezia, простая установка, бесплатно до 100 устройств.
🇬🇧 After two failed VPN attempts (ADR-0003), a solution for external access from mobile networks is needed. Requirements: CGNAT-proof, does not touch Amnezia, simple setup, free up to 100 devices.

## Рассмотренные варианты / Options considered

| Вариант / Option | CGNAT | Независим от Amnezia / Independent | Сложность / Complexity |
|---|---|---|---|
| wg-nas_jetson_nano | ✗ | да / yes | высокая / high |
| Amnezia Desktop App | частично / partial | нет / no | средняя / medium |
| ngrok/cloudflared | ✓ | да / yes | низкая, НО третья сторона / low, BUT third party |
| **Tailscale** | ✓ DERP-relay | да / yes | очень низкая / very low |
| ZeroTier | ✓ | да / yes | низкая / low |

## Решение (исторически) / Decision (historical)

🇷🇺 **Tailscale** — userspace WireGuard с DERP-relay для обхода CGNAT.
🇬🇧 **Tailscale** — userspace WireGuard with DERP-relay for CGNAT bypass.

- 🇷🇺 Устанавливается как userspace-демон, не конфликтует с Amnezia / 🇬🇧 Installs as userspace daemon, no Amnezia conflict
- 🇷🇺 Jetson получает IP из диапазона `100.x.x.x` / 🇬🇧 Jetson gets IP from `100.x.x.x` range
- 🇷🇺 Трафик зашифрован (WireGuard), при CGNAT идёт через DERP-серверы / 🇬🇧 Traffic encrypted (WireGuard), goes via DERP servers under CGNAT

## Последствия / Consequences

- 🇷🇺 Бесплатно до 100 устройств; требует аккаунт Tailscale / 🇬🇧 Free up to 100 devices; requires Tailscale account
- 🇷🇺 При недоступности серверов Tailscale — LAN продолжает работать / 🇬🇧 If Tailscale servers are down — LAN continues working
- 🇷🇺 Не требует изменений в роутере или Amnezia / 🇬🇧 No router or Amnezia changes needed
