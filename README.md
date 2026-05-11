# weavers-town

This repository owns the public website for `weavers.town`.

It contains:

- the Hugo layouts and site structure
- the homepage and non-book pages
- the static assets used by the site
- the GitHub Pages deployment workflow

It does not own the book manuscript. The book source of truth lives in the `threads-of-meaning` repository.

## How book updates arrive here

The book repo generates Hugo-ready content and syncs these paths into this repo:

- `content/book/`
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