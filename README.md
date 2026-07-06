# weavers-town

Hugo website for [weavers.town](https://weavers.town).

This repo owns the site shell only: layouts, homepage, branding, i18n, tests, and GitHub Pages config. **All content is authored and published from the [threads-of-meaning](https://github.com/weavers-town/threads-of-meaning) repo.**

## What lives here vs. the book repo

| In **threads-of-meaning** (source) | In **weavers-town** (synced) |
|------------------------------------|------------------------------|
| `manuscript/`, `explorations/` | `content/book/`, `content/explorations/` |
| `images/` | `static/images/` |
| Generated audio | `static/audio/` |

Do not edit book chapters or explorations here — changes will be overwritten on the next publish.

## Publishing

All publishing is done locally from `threads-of-meaning`. See **[PUBLISHING.md](https://github.com/weavers-town/threads-of-meaning/blob/main/PUBLISHING.md)** in the book repo.

Quick version:

```bash
cd ../threads-of-meaning
make publish-website    # translate → audio → sync here → test → push both repos
```

Or sync only:

```bash
make web                # copies content into this repo and pushes
```

## Local development

```bash
npm install
npm run dev             # Hugo dev server
npm run build           # production build
npm test                # Playwright tests
```

## Deploy

GitHub Actions deploy is **manual only** (workflow dispatch). Normal workflow: publish from `threads-of-meaning`, which pushes synced content here, then build and deploy `public/` yourself or trigger **Deploy Website** in Actions if you want CI.

Pages should use GitHub Actions and the custom domain `weavers.town`.