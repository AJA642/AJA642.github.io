# Portfolio Site — Ashish Abraham

Plain static HTML/CSS/JS portfolio. No framework, no build step.

## Structure
```
index.html      one page, all sections
styles.css      design system + layout
script.js       scroll-reveal only (IntersectionObserver)
assets/         CV PDF + project screenshots go here
```

## Deploy to GitHub Pages
Push this folder as the root of its own repo, then in the repo's
**Settings → Pages**, set Source to "Deploy from a branch" and
branch/folder to `main` / `/ (root)`. No build step required.

If the repo is named `AJA642.github.io`, the site serves at the
root domain (`https://aja642.github.io/`). Any other repo name
serves at `https://aja642.github.io/<repo-name>/`.

## Placeholders still to fill in
Search the codebase for `TODO` to find every one. As of this
writing:

- `assets/Ashish_Abraham_CV.pdf` — CV file (linked, not yet added)
- Dashboard screenshot for the Featured Project section
- Retail Sales KPI Dashboard card — screenshot, Tableau Public
  embed link, remove the "Building now" tag once live
- Email address and LinkedIn URL in the footer

The GitHub repo link for the featured project
(`github.com/AJA642/Football-PlayerValuation`) is already wired in
— confirmed against that project's own git remote.
