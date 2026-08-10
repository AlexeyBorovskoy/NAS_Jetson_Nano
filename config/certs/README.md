# Russian Trusted CA bundle — для GigaChat

> 🇷🇺 Публичные корневые сертификаты НУЦ Минцифры. **Это не секреты** —
> они специально коммитятся, чтобы развёртывание было воспроизводимым.
>
> 🇬🇧 Public root certificates of the Russian Ministry of Digital Development CA.
> **Not secrets** — committed on purpose so deployment is reproducible.

## Зачем

Эндпоинты Сбера (`ngw.devices.sberbank.ru`, `gigachat.devices.sberbank.ru`)
подписаны НУЦ Минцифры, которого нет в стандартном хранилище доверия Python
и Debian. Без этого бандла запрос падает так:

```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
self-signed certificate in certificate chain
```

Проверено 2026-08-10: с бандлом OAuth и `chat/completions` проходят
**с включённой проверкой TLS**. Отключать верификацию не нужно.

## Файлы

| Файл | Что это |
|---|---|
| `russian_trusted_root_ca.cer` | корневой сертификат (PEM) |
| `russian_trusted_sub_ca.cer` | промежуточный сертификат (PEM) |
| `russian_trusted_bundle.pem` | оба, склеенные — **этот путь и указывается** |

## Как пересобрать

```bash
cd config/certs
curl -sfLO https://gu-st.ru/content/Other/doc/russian_trusted_root_ca.cer
curl -sfLO https://gu-st.ru/content/Other/doc/russian_trusted_sub_ca.cer
cat russian_trusted_root_ca.cer russian_trusted_sub_ca.cer > russian_trusted_bundle.pem
```

Если файлы придут в DER, а не PEM — сконвертировать:

```bash
openssl x509 -inform DER -in russian_trusted_root_ca.cer -out root.pem
```

## Как используется

Монтируется в контейнер `homecloud_llm_gateway` как `/certs` (read-only),
путь передаётся переменной `GIGACHAT_CA_BUNDLE=/certs/russian_trusted_bundle.pem`.
См. `docker/compose/docker-compose.llm-gateway.yml`.
