# 04_CREDENTIAL_ROTATION_PLAN — Безопасная ротация и +5 новых устройств

1. **Принцип:** **add new → pilot → confirm device → revoke old**. Массовый отзыв (`mass-revoke`) запрещён.
2. **Учётные данные v3 (12 индивидуальных пар):**
   - `7` ротированных пар для существующих устройств (`alexey-windows`, `ivan-windows`, `ivan-android`, `olga-android`, `ulyana-android-1`, `ulyana-android-2`, `hagircbmsszlx4in`).
   - `5` новых пар (`new-01`..`new-05`) в статусе `PREPARED` (добавляются на сервер в S3, выдаются только при назначении устройства в S5).
3. **Зависимости старых общих секретов:**
   - Пара `hagircbmsszlx4in` используется в 4 файлах (`FAMILY-SE-01.yaml`, `02`, `03-HY2`, `04-TLS`). Отзыв старой записи `hagircbmsszlx4in` допустим только после подтверждения, что ни одно устройство не осталось на этих 4 файлах.
   - На физическом телефоне `ANDROID_G1` использовался `FAMILY-SE-Olga-Android.yaml` (`olga-android`), поэтому `olga-android` в v1 сохраняется до завершения миграции телефона Ольги и тестового телефона.
4. **Хранение:** секреты v3 сгенерированы через ОС CSPRNG (`os.urandom` / `secrets.token_urlsafe(24)`) и хранятся исключительно в `.agent-work/private-releases/sweden-v3/vault_v3.json` (вне Git).
