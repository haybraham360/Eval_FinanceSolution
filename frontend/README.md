# Ledger-Eval Explorer

This is a read-only website over the committed state of this repository. It shows tasks, results, graded failures and methodology. Everything on it is extracted at build time from the files in the commit being deployed. See [data/source-map.md](data/source-map.md) for which file feeds which part of the page.

The site makes no model calls, needs no API keys or database, and cannot change any benchmark result.

## How it stays in sync

```text
edit in VS Code -> git push to main -> .github/workflows/deploy-explorer.yml
  -> validate_graders.py                       (graders still sound)
  -> scripts/verify_committed_results.py       (committed scores re-grade identically)
  -> scripts/export_explorer_data.py           (builds the data bundle, fails on bad data)
  -> npm test, npm run build                   (static site)
  -> GitHub Pages deploy
```

If any step fails, nothing is deployed and the last good site stays up. On every page view, the site compares the commit it was built from with the current head of `main` through GitHub's public API. If they differ, it shows a notice that the page may be out of date.

`public/explorer-data.json` is generated and git-ignored. Never edit it by hand.

## Run it locally

You need Python 3.10+ and Node 22+.

```sh
cd frontend
npm install
npm run data      # extract from your working copy into public/explorer-data.json
npm run dev       # http://localhost:5173
```

A local build from uncommitted files shows a "Local preview" banner, because the published site only ever shows what is committed.

Tests:

```sh
python -m unittest discover -s ../scripts/tests   # the extractor follows the repository
npm test                                           # the page follows the data bundle
```

## One-time GitHub setting

In the repository, open **Settings → Pages** and set **Source** to **GitHub Actions**. No secrets are needed. The site is then published at `https://<owner>.github.io/<repo>/`. To rebuild without a new commit, run the workflow from the **Actions** tab ("Run workflow").

## Editing copy

Only `src/content/site.json` holds hand-written text: the headline, the description and the "How it works" steps. Task descriptions come from the README's task tables, and limitations from the README's limitations section. Edit those in the README and they update on the next push.
