# 04_BENCHMARK_RESULTS — Результаты измерений и A/B серии

- **Среда измерения:** Windows (`FlClash` ядро `Mihomo v1.19.34`, изолированный SOCKS/mixed режим без TUN), сеть `windows_via_amnezia_tun2` (поверх `AmneziaVPN` `89.124.65.229`).
- **Полные сырые данные:** [measurements.csv](file:///e:/Linux%20mint/virtual_VM/shared/NAS_Jetson_Nano/docs/sweden_vpn_v2/measurements.csv), [measurements.jsonl](file:///e:/Linux%20mint/virtual_VM/shared/NAS_Jetson_Nano/docs/sweden_vpn_v2/measurements.jsonl).

## 1. Первичный отсев (5 холодных запусков на кандидата)

| Кандидат | Успех | Медиана `T_ready` | `p95` | `max` | Выбранный транспорт | Примечание |
|---|---:|---:|---:|---:|---|---|
| `v1_current` | `5/5` | `1244.2` мс | `1380.3` мс | `1407.7` мс | `SE-HY2` | DoH/DoT `1.1.1.1` на старте |
| `v1_ip_endpoint_h01` | `5/5` | `1000.8` мс | `1177.5` мс | `1187.6` мс | `SE-HY2` | Без DNS-ожидания (`-243` мс) |
| `v1_reality_only` | `0/5` | `null` | `null` | `null` | `SE-PRIMARY` | Через `tun2` SNI `www.googletagmanager.com` перехватывается; с самого VPS `45.140.13.178` `rc=0` |
| `v1_hy2_only` | `5/5` | `1519.2` мс | `5271.6` мс | `6177.2` мс | `SE-HY2` | Зафиксирован выброс `6.18` с |
| `v2_hy2_first_fallback` | `5/5` | `727.1` мс | `903.2` мс | `937.6` мс | `AUTO->SE-HY2` | Быстрый DNS bootstrap + `fallback` |
| `v2_reality_first_fallback` | `5/5` | `728.3` мс | `912.5` мс | `936.2` мс | `AUTO->SE-HY2` | `AUTO` автоматически переключился на `SE-HY2` |

## 2. Серия A/B (30 холодных запусков на кандидата)

| Кандидат | Успех | Медиана `T_ready` | `p95` | `max` | Выигрыш по `p95` |
|---|---:|---:|---:|---:|---|
| `v1_current` | `30/30` | `1195.1` мс | `1283.1` мс | `1384.8` мс | База |
| `v2_hy2_first_fallback` | `30/30` | **`718.4` мс** | **`835.7` мс** | **`1169.3` мс** | **`-34.9%` (`-447.4` мс)** |

## 3. Ограничения выборки
- Серия проведена поверх `AmneziaVPN` (`tun2`) на Windows без TUN. Живой пилот в прямой домашней сети (Wi-Fi/Ethernet без `AmneziaVPN`) и на Android (Wi-Fi + мобильная сеть) — **`PENDING_DEVICE` (этап G1)**.
