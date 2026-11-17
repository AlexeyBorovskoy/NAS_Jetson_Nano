# 02_ARCHITECTURE_ADR — Архитектурное решение Sweden VPN v2

- **Дата:** `2026-11-17`
- **Статус:** Принято для пилота **G1** (ожидает согласования пользователя)

## 1. Сохранение серверного стека v1
- Сохраняем на VPS (`45.140.13.178`) существующие `sing-box 1.14.4` (`vless-reality-in` TCP/443 + `hy2-in` UDP/443 + file masquerade `/var/www/vpn-landing`), `nginx` TCP/8443 и `vpn-monitor` `127.0.0.1:8088`.
- **Backward compatibility:** реквизиты v1 (UUID, пароли, ключи, порты) не отзываются и не изменяются; профили v1 остаются рабочим откатом на каждом устройстве.

## 2. Выбор транспорта (`PROXY` → `AUTO` `fallback`)
- Вместо плоского `select: [SE-HY2, SE-PRIMARY]` вводится:
  - `PROXY` (`type: select`): `["AUTO", "SE-PRIMARY", "SE-HY2"]` — по умолчанию `AUTO`, с возможностью ручного переключения для диагностики.
  - `AUTO` (`type: fallback`):
    - `url: https://www.gstatic.com/generate_204`
    - `interval: 120` (120 с, баланс между скоростью восстановления и батареей Android)
    - `timeout: 3000` (3000 мс — таймаут health-check, не каждого соединения)
    - `lazy: false` (проверять кандидатов сразу при старте)
    - `max-failed-times: 2`
- **Порядок кандидатов на пилоте:** в `policy_v2.yaml` подготовлен `SE-PRIMARY -> SE-HY2` (TCP REALITY первым как наиболее устойчивый против UDP-шейпинга и потерь первого пакета, с автоматическим fallback на HY2) и параметр `--auto-order hy2-first` в генераторе для сравнительного пилота на живой сети без `AmneziaVPN`.
- **Запрет DIRECT-утечки:** `DIRECT` запрещён внутри `AUTO`, последнее правило всегда `MATCH,PROXY`.

## 3. Независимый DNS bootstrap
- `default-nameserver: ["1.1.1.1", "8.8.8.8", "system"]` (без DoH/DoT, чтобы исключить TLS-цикл на старте).
- `proxy-server-nameserver: ["1.1.1.1", "8.8.8.8", "system"]` (устраняет 2.3-секундную задержку DoH `1.1.1.1`).
- `direct-nameserver: ["system"]` + `respect-rules: true` (прямые `.ru` и LAN-домены резолвятся системным DNS без выхода через прокси).
- `nameserver: ["https://1.1.1.1/dns-query", "https://8.8.8.8/dns-query"]`, `fallback: ["tls://1.1.1.1:853", "tls://8.8.8.8:853"]` для VPN-трафика.
- `fake-ip-filter` дополнен `vpn.privet.dynv6.net` и индивидуальными прямыми доменами устройства.

## 4. Платформенные настройки TUN и совместимость с FlClash
- **Windows:** `tun.enable: true`, `stack: gvisor`, `auto-route: true`, `auto-detect-interface: true`, `strict-route: false` (предотвращает блокировку при нескольких адаптерах). При использовании `FlClash` на Windows в GUI необходимо включить TUN (поскольку в текущем `shared_preferences.json` `tun.enable=false`) и убедиться, что второй VPN (`AmneziaVPN`) выключен во время работы/пилота Sweden VPN.
- **Android:** `tun.enable: true`, `stack: gvisor`, `dns-hijack: ["any:53"]`.

## 5. Второй независимый узел (опция, не реализуется автоматически)
- Два протокола (`TCP/443` и `UDP/443`) на одном IP `45.140.13.178` защищают от блокировки конкретного транспорта, но не от отказа самого VPS/IP/провайдера.
- Опция резервного VPS на другом хостере/ASN оценивается отдельно (~400–600 руб/мес) и требует отдельного согласования.
