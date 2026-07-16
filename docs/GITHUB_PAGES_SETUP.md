# GitHub Pages setup

## Enable manually

1. Open the repository on GitHub: https://github.com/AlexeyBorovskoy/NAS_Jetson_Nano
2. Go to **Settings**.
3. Open **Pages** in the left sidebar.
4. Under **Build and deployment**, choose **Deploy from a branch**.
5. Select branch: `main`.
6. Select folder: `/docs`.
7. Click **Save**.
8. Wait 1–3 minutes for GitHub Pages deployment (check Actions tab).
9. Open the site:

```
https://alexeyborovskoy.github.io/NAS_Jetson_Nano/
```

## Verify

- `docs/index.md` → landing page
- `docs/articles/habr_article_ru.md` → Habr article in Russian
- `docs/articles/hackaday_project_en.md` → Hackaday draft in English
- `docs/pages/architecture.md` → Architecture overview
- `docs/pages/reliability.md` → Reliability and USB incidents
- `docs/pages/android.md` → Android client setup
- `docs/pages/evidence.md` → Evidence package links

## Notes

If the repository uses custom Actions-based publishing later, switch Pages source to **GitHub Actions** and add a dedicated workflow.
For the first version, `/docs` branch publishing is enough.

## Custom domain (optional)

Add a `CNAME` file to `/docs` with your domain name if you have one.
Example:
```
nas_jetson_nano.yourdomain.com
```
Then configure the DNS CNAME record to point to `alexeyborovskoy.github.io`.
