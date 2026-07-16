Ты работаешь как open-source strategist, GitHub project maintainer, technical writer и инженер по продвижению технических проектов.

Проект: `NAS_Jetson_Nano`

Идея проекта:

```text
Old Hardware Must Live — домашний NAS на базе Jetson Nano первого поколения и старого HDD 2 ТБ.
```

Цель проекта:

```text
Сделать воспроизводимый open-source проект, который показывает, как превратить старое оборудование в полезную домашнюю инфраструктуру: NAS, Samba, monitoring, backup, documentation, healthcheck.
```

Текущая ситуация:

```text
GitHub Traffic:
- Clones за 14 дней: ~320
- Unique cloners: ~130
- Views: 0
- Unique visitors: 0
```

Интерпретация:

```text
Репозиторий активно клонируют, но публичная страница проекта пока не привлекает браузерные просмотры. Нужно превратить репозиторий в понятную витрину и подготовить проект к органическому росту без публикации статей.
```

Ниже будет audit report существующего состояния проекта.
Используй его как основной источник для плана продвижения.

```markdown
ВСТАВЬ СЮДА AUDIT REPORT
```

---

# 1. Главная задача

На основе audit report сформируй стратегию продвижения проекта без публикации статей, без рекламы и без спама.

Цель:

```text
Увеличить GitHub views, unique visitors, stars, forks, issues и повторяемость проекта.
```

Не нужно предлагать Хабр, Reddit, YouTube, Telegram-каналы и внешние статьи как первый шаг.
Сначала нужно улучшить сам репозиторий как продуктовую витрину.

---

# 2. Что нужно проанализировать

На основе audit report оцени:

1. Что мешает проекту получать views.
2. Почему могут быть clones, но нет views.
3. Какие элементы репозитория надо улучшить в первую очередь.
4. Как сделать проект понятным за 20–30 секунд.
5. Как сделать проект привлекательным для:

   * GitHub users;
   * Codeberg users;
   * Linux/self-hosted аудитории;
   * homelab аудитории;
   * владельцев старого железа;
   * начинающих пользователей Linux;
   * людей, которые ищут NAS на дешёвом оборудовании.

---

# 3. Стратегия продвижения без внешних статей

Сформируй план продвижения через сам репозиторий:

## 3.1. GitHub repository page

Что улучшить:

* название;
* About description;
* topics;
* README;
* badges;
* image/photo;
* architecture diagram;
* quick start;
* roadmap;
* release;
* pinned repository;
* social preview image;
* issue templates;
* good first issue;
* discussions.

## 3.2. README as landing page

Опиши, как README должен работать как посадочная страница:

* первый экран;
* фото;
* миссия проекта;
* hardware table;
* architecture diagram;
* quick start;
* safety warning;
* roadmap;
* how to contribute.

## 3.3. GitHub Topics

Предложи точный список topics:

```text
jetson-nano
nas
samba
linux
self-hosted
homelab
old-hardware
recycled-hardware
hdd
backup
arm64
open-source
```

Если есть более удачные topics — предложи.

## 3.4. Releases

Предложи схему релизов:

* v0.1.0 — documentation baseline;
* v0.2.0 — Samba NAS MVP;
* v0.3.0 — SMART monitoring;
* v0.4.0 — backup scripts;
* v1.0.0 — reproducible Jetson Nano NAS.

Для каждого релиза укажи:

* цель;
* что включить;
* что написать в release notes.

## 3.5. Issues как инструмент продвижения

Создай план issues:

* good first issue;
* documentation;
* hardware testing;
* bug report;
* enhancement;
* help wanted.

Дай 10 готовых названий issues.

Например:

```text
Add real photo of Jetson Nano NAS setup
Test Samba share from Windows 11
Add SMART healthcheck output example
Add hardware compatibility table
Create Codeberg mirror
```

## 3.6. Codeberg mirror

Сформируй план размещения проекта на Codeberg:

1. Создать пустой public repository.
2. Не инициализировать README/LICENSE.
3. Добавить remote.
4. Push mirror.
5. Добавить описание.
6. Добавить topics.
7. Добавить README mirror section.
8. Проверить отображение Markdown.

Дай команды для Git.

## 3.7. GitLab mirror

Сформируй краткий план для GitLab:

* зачем нужно зеркало;
* как добавить remote;
* как push;
* что использовать для CI/CD.

## 3.8. Project metrics

Предложи, как отслеживать рост проекта:

* GitHub views;
* unique visitors;
* clones;
* unique cloners;
* stars;
* forks;
* issues;
* releases downloads;
* Codeberg activity.

Предложи файл:

```text
docs/project_metrics.md
```

И формат записи раз в неделю.

---

# 4. План действий по срокам

Сформируй план:

## День 1

Только самые важные действия.

## Неделя 1

Что сделать за первую неделю.

## Месяц 1

Что сделать за первый месяц.

Для каждого пункта укажи:

| Действие | Цель | Ожидаемый эффект | Сложность |
| -------- | ---- | ---------------- | --------- |

---

# 5. Готовые тексты для GitHub

Сформируй готовые тексты:

## 5.1. About description

1 короткий вариант и 1 расширенный вариант.

## 5.2. Social preview text

Текст для изображения/описания social preview.

## 5.3. Короткое описание проекта

На английском.

## 5.4. Русское описание проекта

На русском.

## 5.5. Текст для README-блока `Why this project exists`

На английском.

## 5.6. Текст для README-блока `Safety warning`

На английском.

---

# 6. Что не делать

Сформируй список ошибок продвижения:

* не публиковать проект вовне до нормального README;
* не обещать надёжность старого HDD;
* не делать вид, что это production NAS;
* не добавлять неподтверждённые характеристики;
* не использовать чужие фото;
* не добавлять несуществующие результаты тестов;
* не использовать спам-продвижение;
* не накручивать stars.

---

# 7. Итоговый результат

Сформируй итоговый Markdown-отчёт:

```markdown
# Promotion Plan: NAS_Jetson_Nano

## 1. Executive summary
## 2. Current situation
## 3. Main problem
## 4. Positioning
## 5. GitHub improvement plan
## 6. README landing-page plan
## 7. Topics and discoverability
## 8. Release strategy
## 9. Issues strategy
## 10. Codeberg mirror plan
## 11. GitLab mirror plan
## 12. Metrics tracking
## 13. 1-day action plan
## 14. 1-week action plan
## 15. 1-month action plan
## 16. Ready-to-use texts
## 17. What not to do
```

---

# 8. Ограничения

Не редактируй файлы проекта автоматически, если тебя явно не попросили.
Сначала сформируй стратегию и список изменений.
Не предлагай внешние статьи как первый шаг.
Не используй спам, накрутку, фальшивые stars или искусственный трафик.
Не придумывай несуществующие метрики.
Не обещай надёжность старого HDD.
Сохраняй инженерный тон: честно, конкретно, практично.

Начни с анализа audit report и сформируй полный promotion plan.
