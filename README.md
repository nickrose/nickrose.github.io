# nickrose.github.io

Personal academic/CV site, built with [Hugo](https://gohugo.io/) (extended) and the
[Hugo Blox](https://hugoblox.com/) "Academic CV" theme (fetched as a Hugo Module).

## Prerequisites

- **Hugo, extended edition, v0.164.0** (pinned in `hugoblox.yaml`) — `brew install hugo`
- **Go 1.19+** — needed for Hugo Modules to fetch the theme (`brew install go`)
- **Node.js 22+ and pnpm** — needed for the Tailwind CSS build (`brew install node && npm install -g pnpm`)

## First-time setup

```sh
pnpm install   # Tailwind CLI, Pagefind, etc.
hugo mod tidy  # fetches the Hugo Blox theme modules (needs network access)
```

## Run the site locally (dev server, live reload)

This is the Hugo equivalent of `uvicorn module:app --port 8000`:

```sh
hugo server --disableFastRender --port 8000
```

- Open the printed URL (e.g. `http://localhost:8000`) — Hugo watches the filesystem and
  live-reloads the browser on every save.
- Omit `--port` to use Hugo's default, `1313`.
- Equivalent shortcut: `pnpm run dev` (always uses port `1313`).
- Stop the server with `Ctrl+C`.

## Production build

```sh
hugo --minify && pnpm run pagefind
```

or equivalently `pnpm run build`. This writes the fully static site to `public/` — the
same command the GitHub Actions workflow (`.github/workflows/build.yml`) runs to deploy
to GitHub Pages on every push to `master`.

## Project layout

- `content/` — pages (Markdown + front matter)
- `data/authors/me.yaml` — CV data (bio, education, experience, skills, awards, links)
- `config/_default/` — site config, nav menus, theme/params
- `assets/media/` — images, favicon, etc.
- `public/`, `resources/`, `node_modules/` — build artifacts, gitignored, not checked in
