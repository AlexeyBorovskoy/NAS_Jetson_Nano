# 01_STARTUP_RCA — Расследование задержки первого подключения Sweden VPN

- **Дата:** `2026-11-17`
- **Узел:** `45.140.13.178` (`vpn.privet.dynv6.net`)
- **Статус:** `OBSERVED` + `MEASURED` (на Windows-стенде); пилот в прямой домашней сети без `AmneziaVPN` и на Android — `PENDING_DEVICE`.

---

## 1. Выявленные и подтверждённые причины задержки

### Причина #1 (`OBSERVED` + `MEASURED`, критическая): Медленный DNS bootstrap (`DoH` / `DoT` к `1.1.1.1` и `8.8.8.8`)
- В `FAMILY-SE-Alexey-Windows.yaml` (v1) для разрешения `vpn.privet.dynv6.net` заданы:
  - `default-nameserver: ["tls://1.1.1.1", "tls://8.8.8.8"]`
  - `proxy-server-nameserver: ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query"]`
- Прямые замеры на Windows (`5` попыток, 2026-11-17):
  - `system_getaddrinfo`: `vals=[368.5, 0.5, 0.4, 0.3, 0.2]` мс, **медиана `0.4` мс**
  - `doh_1.1.1.1` (`https://1.1.1.1/dns-query`): `vals=[2546.4, 2425.5, 2308.8, 288.6, 2310.7]` мс, **медиана `2310.7` мс** (`2.31` с на один запрос!)
  - `doh_8.8.8.8`: медиана `248.9` мс
  - `dot_tls_1.1.1.1` (`tls://1.1.1.1:853`): медиана `210.0` мс
- Кроме того, `respect-rules` не был включён (`false`), а `direct-nameserver` отсутствовал — даже прямые `.ru`-запросы шли через `https://1.1.1.1/dns-query`.
- Замена `proxy-server-nameserver` и `default-nameserver` на `["1.1.1.1", "8.8.8.8", "system"]` + `direct-nameserver: ["system"]` в изолированном стенде Mihomo сразу сократила `p95 T_ready` с **`1283.1` мс** до **`835.7` мс** (`-34.9%`, 30 прогонов).

### Причина #2 (`OBSERVED`, критическая для надёжности): Отсутствие автоматического failover (`type: select` вместо `fallback`)
- Во всех 10 YAML v1 группа `PROXY` имеет `type: select` со списком `["SE-HY2", "SE-PRIMARY"]`.
- При потере первых UDP-пакетов (QUIC Initial) или временной деградации UDP/443 в домашнем Wi-Fi / мобильной сети клиент **не переключается** на `SE-PRIMARY` (`VLESS+REALITY` TCP/443), пока пользователь вручную не перевключит VPN или не сменит узел.
- Подтверждение нестабильности первого запуска `HY2` без доработки: в 5-прогонном тесте `v1_hy2_only` зафиксирован выброс `max = 6177.2 мс` (`p95 = 5271.6 мс`).

### Причина #3 (`OBSERVED` на Windows): Конфликт с `AmneziaVPN` (`tun2`) и GUI-переопределения `FlClash`
- На Windows одновременно запущены `AmneziaVPN` (`tun2socks Tunnel`, маршруты `0.0.0.0/1`, `128.0.0.0/1`, `1.1.1.1/32`, `1.0.0.1/32` через `tun2`) и `FlClash 0.9.3+2026110401`.
- Эффективный `C:\Users\Alexey\AppData\Roaming\com.follow\clash\config.yaml` отличается от импортированного профиля:
  - `tun.enable: false`, `tun.stack: mips` (перезаписано GUI `patchClashConfig`),
  - `unified-delay: false`, `tcp-concurrent: false`, `sniffer.enable: false`, `log-level: error`.
- В `FAMILY-SE-Alexey-Windows.yaml` также стоял `strict-route: true`, что при нескольких адаптерах (`Ethernet`, `tun2`, `vEthernet (WSL)`) способно блокировать стартовые запросы.
- **Важное наблюдение стенда:** при запуске `VLESS+REALITY` (`SNI=www.googletagmanager.com`) поверх активного `AmneziaVPN` (`tun2`) промежуточный сниффер перехватывает SNI и направляет соединение на реальный `www.googletagmanager.com` (`*.google-analytics.com`), вызывая `REALITY authentication failed`. С самого VPS (`45.140.13.178`) `VLESS+REALITY` работает (`rc=0`, egress `45.140.13.178`). Поэтому реальная проверка `REALITY` с Windows/Android должна выполняться на пилоте **без** активного `AmneziaVPN`.

---

## 2. Таблица гипотез (Шаг B2)

| ID | Гипотеза | Статус | Доказательство |
|---|---|---|---|
| H01 | DNS-зависимость старта от DoH/DoT `1.1.1.1` | `CONFIRMED` (`MEASURED`) | `doh_1.1.1.1` медиана `2310.7` мс vs `system` `0.4` мс; `v1_ip_endpoint_h01` быстрее `v1_current` (`1000.8` vs `1244.2` мс); `v2` DNS даёт `p95=835.7` мс |
| H02 | Потери/задержка HY2 на старте без failover (`select`) | `PARTIAL / CONFIRMED_DESIGN` | `v1_hy2_only` дал выброс `max=6177.2` мс; `select` не переключает на `SE-PRIMARY` |
| H03 | Задержка выбора узла (`select` vs `fallback`) | `CONFIRMED` (`MEASURED`) | `AUTO` (`fallback`) переключает при отказе и с `unified-delay: true` + `tcp-concurrent: true` стабилен (`30/30`, `p95=835.7` мс) |
| H04 | Загрузка rule/proxy providers блокирует старт | `REFUTED` (для v1) | В 10 YAML нет `proxy-providers` / `rule-providers`; кэш локальный |
| H05 | Некорректный IPv6-путь | `PARTIAL` | На VPS IPv6 egress `HTTP=200`, но у `vpn.privet.dynv6.net` нет AAAA; `ipv6: false` в профилях уже задан |
| H06 | Конфликт TUN / второго VPN (`AmneziaVPN` `tun2`) | `OBSERVED` | На Windows активен `tun2` с `1.1.1.1/32` и `0.0.0.0/1`; `FlClash` `config.yaml` имеет `tun.enable: false` |
| H07 | Android Doze / смена сети | `PENDING_DEVICE` | Нет подключённого Android-устройства (`adb devices -l` пуст) |
| H08 | Серверные буферы / RAM | `NOT_PRIMARY_CAUSE` | IMP-02/03 уже применены 2026-11-16, RAM `1.6 GiB` avail, UDP errors `0` |
| H09 | REALITY handshake ошибка | `OBSERVED_VIA_TUN2` | Через `tun2` SNI `www.googletagmanager.com` уходит на Google; с самого VPS `45.140.13.178` REALITY `OK` |
