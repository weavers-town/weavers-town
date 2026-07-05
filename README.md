# weavers-town

This repository owns the public website for `weavers.town`.

It contains:

- the Hugo layouts and site structure
- the homepage and non-book pages
- the static assets used by the site
- the GitHub Pages deployment workflow

It does not own the book manuscript. The book source of truth lives in the `threads-of-meaning` repository.

## Languages

The site supports English (default) and Vietnamese.

- English: `/`, `/book/`, `/explorations/`
- Vietnamese: `/vi/`, `/vi/book/`, `/vi/explorations/`

Site UI strings live in `i18n/en.yaml` and `i18n/vi.yaml`. The header includes a language dropdown that scales to additional locales.

To add a new language (for example Persian), add a `[languages.fa]` block in `hugo.toml`, create `content/fa/` and `i18n/fa.yaml`, and set `dir = "rtl"` in the language params when needed.

Explorations are translated and audio-enabled separately from the book:

```bash
export XAI_API_KEY="xai-..."   # or add to .env / threads-of-meaning/.env
npm run audio                 # generate missing/changed exploration MP3s (en + vi)
npm run translate             # Vietnamese posts in content/vi/explorations/
```

When you add a new exploration markdown file under `content/explorations/`, the deploy
workflow generates English and Vietnamese MP3s with xAI TTS, updates `audio:` frontmatter,
and commits the results before building the site.

## How book updates arrive here

The book repo generates Hugo-ready content and syncs these paths into this repo:

- `content/book/` (English)
- `content/vi/book/` (Vietnamese, from `manuscript-vi/` in the book repo)
- `static/images/`

That sync happens either:

- locally via `make web` in the book repo
- or through the book repo workflow `.github/workflows/publish-book-to-website.yml`

## Local development

Install dependencies:

```bash
npm install
```

Run the local Hugo server:

```bash
npm run dev
```

Build the production site:

```bash
npm run build
```

Serve the built site:

```bash
npm run serve
```

## Deploy

This repo deploys to GitHub Pages through `.github/workflows/deploy-pages.yml`.

Pages should be configured to use GitHub Actions and the custom domain `weavers.town`.