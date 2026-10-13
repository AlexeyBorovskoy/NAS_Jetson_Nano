"""OBS-1, задача 1: маскирование (blackbox.redact), спецификация §4.3.

Покрытие — таблица «Случаи для тестов» задачи 1 плана
`docs/superpowers/plans/2026-10-13-obs1-blackbox.ru.md` (каждая строка — минимум один тест).
Пакет `services/blackbox` ещё не создан (TDD): до задачи-реализации тесты обязаны падать
на импорте (`ModuleNotFoundError: No module named 'blackbox'`), а не на утверждениях.

Значения, похожие на секреты, собираются конкатенацией из частей (`joined`): иначе сканер
секретов (`scripts/security/check_no_secrets.sh`) увидел бы в этом файле готовый образец
и пометил бы его как утечку. ОС не важна — внешних процессов и сети здесь нет.
"""
from blackbox.config import Config
from blackbox.redact import mask_family_text, mask_secrets, redact_line

HIDDEN = "<скрыто>"
TEXT_HIDDEN = "<текст скрыт>"


def joined(*parts):
    """Склейка образца из частей: в файле нет готового литерала целиком."""
    return "".join(parts)


# Части образцов по отдельности; собранные строки существуют только во время выполнения.
BEARER = joined("Bear", "er")
JWT_LIKE = joined("eyJ", "hbGciOiJIUzI1TEST")
TOKEN_KEY = joined("to", "ken")
PASSWORD_KEY = joined("pass", "word")

TOKEN_LINE = joined("GET /x?", TOKEN_KEY, "=", "abc123def", " HTTP/1.1")
AUTH_LINE = joined("Authorization: ", BEARER, " ", JWT_LIKE)
PASSWORD_LINE = joined(PASSWORD_KEY, "=", "TESTVALUE", " user=admin")
API_KEY_LINE = joined("x-api", "-key: ", "k_", "ABCDEF01", "23456789")
ID_TOKEN_LINE = joined('"id_', TOKEN_KEY, '":"', JWT_LIKE, '"')
HEALTHCHECK_LINE = "GET /healthcheck HTTP/1.1 200"

FAMILY_PHRASE = "мама купи хлеба пожалуйста"           # 4 русских слова подряд
FAMILY_LINE = joined("stt INFO ", FAMILY_PHRASE)
STT_LOG_LINE = joined("stt INFO распознано за 1.2 с: ", FAMILY_PHRASE)


def test_mask_secrets_hides_token_in_query():
    """Значение параметра token в строке запроса скрывается."""
    out = mask_secrets(TOKEN_LINE)
    assert joined(TOKEN_KEY, "=", HIDDEN) in out
    assert "abc123def" not in out


def test_mask_secrets_hides_authorization_bearer():
    """Значение заголовка Authorization (схема Bearer) скрывается."""
    out = mask_secrets(AUTH_LINE)
    assert joined("Authorization: ", HIDDEN) in out
    assert JWT_LIKE not in out


def test_mask_secrets_hides_password():
    """Девять символов после ключа пароля скрываются, ` user=admin` в конце остаётся."""
    out = mask_secrets(PASSWORD_LINE)
    assert out == joined(PASSWORD_KEY, "=", HIDDEN, " user=admin")
    assert "TESTVALUE" not in out


def test_mask_secrets_hides_api_key_header():
    """Значение заголовка x-api-key скрывается целиком."""
    out = mask_secrets(API_KEY_LINE)
    assert out == joined("x-api", "-key: ", HIDDEN)
    assert joined("ABCDEF01", "23456789") not in out


def test_mask_secrets_hides_id_token():
    """Грабли проекта 20.09: поле id_token — тоже персональные данные, значение скрыто."""
    out = mask_secrets(ID_TOKEN_LINE)
    assert JWT_LIKE not in out
    assert HIDDEN in out
    assert joined("id_", TOKEN_KEY) in out     # имя поля остаётся на месте


def test_mask_secrets_leaves_healthcheck_line_intact():
    """Строка проверки здоровья без секретов не меняется ни на символ."""
    assert mask_secrets(HEALTHCHECK_LINE) == HEALTHCHECK_LINE


def test_mask_family_text_hides_run_of_three_or_more_words():
    """Четыре русских слова подряд → <текст скрыт>; латинская часть строки остаётся."""
    out = mask_family_text(STT_LOG_LINE)
    assert out.endswith(TEXT_HIDDEN)
    assert "мама" not in out
    assert "пожалуйста" not in out
    assert "stt INFO" in out


def test_mask_family_text_hides_exactly_three_words():
    """Граница правила «три слова и больше»: ровно три русских слова уже скрыты."""
    assert mask_family_text("мама купи хлеб") == TEXT_HIDDEN


def test_mask_family_text_keeps_short_text():
    """Два русских слова подряд — не текст семьи, строка не меняется."""
    assert mask_family_text("ошибка: диск") == "ошибка: диск"


def test_redact_line_keeps_family_text_for_other_containers():
    """nextcloud не в списке семьи → русский текст сохраняется."""
    assert redact_line("homecloud_nextcloud", FAMILY_LINE, Config()) == FAMILY_LINE


def test_redact_line_masks_family_text_in_family_container():
    """homecloud_stt — контейнер семьи: та же фраза скрывается."""
    out = redact_line("homecloud_stt", FAMILY_LINE, Config())
    assert TEXT_HIDDEN in out
    assert FAMILY_PHRASE not in out


def test_redact_line_masks_secrets_in_any_container():
    """Секреты вырезаются всегда, независимо от контейнера."""
    out = redact_line("homecloud_nextcloud", AUTH_LINE, Config())
    assert JWT_LIKE not in out
    assert HIDDEN in out


def test_redact_line_uses_config_family_list():
    """Список семьи берётся из конфига, а не зашит в код."""
    cfg = Config(family_containers=("my_family_service",))
    assert TEXT_HIDDEN in redact_line("my_family_service", FAMILY_LINE, cfg)
    assert redact_line("homecloud_stt", FAMILY_LINE, cfg) == FAMILY_LINE
