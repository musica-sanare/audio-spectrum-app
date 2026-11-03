[Docs index](../en/README.md)

# Public release checklist

The repository is private. Making it public is the owner's decision and action. Every item below covers all refs that
will be visible on GitHub, not only the current tree. The procedure behind each item is the `claude-shared-rules`
repository's `docs/en/PUBLIC_RELEASE.md`. lyrics-video-app depends on this repository's tag `v0.5.0`, so this
repository goes public first.

Items marked `要確認` wait for the owner. Results are recorded with their date (all checks so far: 2026-11-03, on
`dev` at `f5be472`). The owner's decisions on scope, the merge of `main`, internal notes, `SECURITY.md` and
`CONTRIBUTING.md` were given on 2026-11-03.

## 1. Scope

- [x] `git ls-remote origin` listed (2026-11-03): `HEAD` pointing to `main`, `refs/heads/main` (`10869b9`),
  `refs/heads/dev` (`f5be472`) and `refs/pull/1/head` (`16c242b`). No tags on GitHub yet. The owner decided to publish `main`, `dev`
  and the tag `v0.5.0`; there are no other refs to delete.
- [x] `refs/pull/*`: pull request 1 (`dev` into `main`). Its head `16c242b` is an ancestor of `dev`, so the scan below
  covers it. The merge commit `10869b9` on `main` has the same tree as `16c242b`.
- [ ] Local branches and tags to publish are pushed. Local `dev` equals `origin/dev`. `origin/main` (`10869b9`) is
  not an ancestor of `dev`, so `main` cannot be fast-forwarded to `dev`; the owner merges `dev` into `main` locally with
  a merge commit (section 6, step 1). The tag `v0.5.0` (annotated, on `dc7ce4f`, contained in `main` and `dev`) exists only locally;
  lyrics-video-app needs it on GitHub. The final scan (section 5) runs after these pushes.

## 2. History

- [x] Secret scan over all history (2026-11-03): gitleaks 8.30.1, `gitleaks git --log-opts="--all" --redact .`,
  41 commits (the 42nd, merge commit `10869b9`, adds no change), no leaks found. `gitleaks dir --redact` over the
  tracked tree of `f5be472` (exported with `git archive`): no leaks found. The ignored `work/` (632 MB of media) and
  the legacy project are never published and were not scanned.
- [x] Every finding reviewed and resolved: there were none.
- [x] Commit identities: every author, committer and the tagger of `v0.5.0` is `musica-sanare` (one author name
  spelled `MusicaSanare`) with its GitHub `noreply` address. The merge commit of pull request 1 has GitHub
  (`noreply@github.com`) as committer.
- [x] No AI co-author or "Generated with" lines in any commit message.
- [x] No `.env*`, local settings, build output, or logs ever committed. Files ever committed outside `src/`, `tests/`
  and `docs/`: `.gitignore`, `CLAUDE.md`, `LICENSE`, `README.md`, `README.ja.md`, a removed `README.es.md`,
  `bench/render_compare.py`, `pyproject.toml`, `uv.lock`. No audio, video, image or font file was ever committed;
  the only non-code files are presets (TOML), the GUI page (HTML, CSS, JS) and its translations (JSON).
- [x] No local absolute paths under a home folder, no user name, no email address other than the `noreply` one in
  the history. The legacy project's folder name never appears.

## 3. Content

- [x] Identifiers: none. The project uses no cloud resources, hosts or accounts. URLs in the history are PyPI
  (`uv.lock`), `brew.sh`, the GUI's `127.0.0.1` address and `evil.example` in a test.
- [x] Third-party material: no songs, videos, reference frames, fonts or images in the tree or the history
  (`.gitignore` excludes media). Songs are named in docs only generically ("a real song", `song.wav`). The legacy
  Unity project is described in words only (`unity-classic` preset, ADR-004); none of its files were committed.
- [x] Internal notes: `CLAUDE.md` and `docs/working/` (requirements, ADRs, phase plans and acceptance reports) stay
  public (owner decision). A search found no local paths, personal data, song titles or the legacy folder name. They
  mention the owner's Mac (M1) and iMovie workflow. `CLAUDE.local.md` and `.claude/` are ignored
  and were never committed.
- [ ] GitHub-side data. `要確認` (owner, on GitHub): pull request 1 (title, description, comments) becomes public;
  check that there are no issues, releases, wiki pages or workflow runs that should not be public. There are no
  workflow files in the history.

## 4. Presentation

- [x] `LICENSE`: MIT (`Copyright (c) 2026 musica-sanare`). Runtime dependencies (from `uv.lock`, 2026-11-03) are
  under permissive licenses compatible with MIT: NumPy (BSD-3-Clause and others), pydantic (MIT), skia-python (BSD),
  soundfile (BSD-3-Clause); GUI extra: FastAPI (MIT), uvicorn (BSD-3-Clause). The repository distributes source only.
  ffmpeg is installed by the user and not distributed.
- [x] README status and quick start (English and Japanese): status says Phases 1 to 4 accepted, version 0.5.0; the
  quick start needs only Homebrew, `uv sync` and a local audio file, no private resources.
- [x] `SECURITY.md` added: reports go to GitHub's private vulnerability reporting; it names the GUI's local web
  server, the file dialogs, the user preset folder and the files the app reads and writes as the parts in scope.
- [x] `CONTRIBUTING.md` and templates: not wanted (owner decision).

## 5. Final checks

- [x] Tests on `f5be472` (2026-11-03): `uv run pytest`, 237 passed, 1 warning (a Starlette deprecation warning
  from FastAPI's test client, test-only). There is no lint configuration and no build step; there is no CI.
- [x] Dependency audit (2026-11-03): `uv audit --frozen` (uv 0.13.5, built in, experimental; it looks up the locked
  versions in the OSV database): no known vulnerabilities in 29 packages.
- [ ] Secret scan and audit repeated on the final commit, after the owner's pushes (section 6, step 4).

## 6. Switch (owner)

No branch deploys anything; pushes only publish commits.

1. Merge `dev` into `main` locally with a merge commit and push it (no new pull request, so no new
   `refs/pull/*`): `git switch main`, `git merge --ff-only origin/main`, `git merge --no-ff dev`,
   `git push origin main`, `git switch dev`. Push `dev` too if it gained commits since `f5be472`.
2. Push the tag: `git push origin v0.5.0`.
3. Check that `git ls-remote origin` shows only `HEAD`, `main`, `dev`, `refs/pull/*` and `refs/tags/v0.5.0` (plus
   `v0.5.0^{}`).
4. Claude reruns the secret scan and the audit on the pushed refs.
5. **Settings → General → Danger Zone → Change repository visibility → Make public.**

- [ ] Visibility changed to public on: date.

## 7. GitHub settings right after (owner)

Setting names as checked against GitHub Docs for lyrics-video-app on 2026-11-01. Everything here is free for a public
repository.

1. **Settings → Security and quality → Advanced Security**:
   - **Private vulnerability reporting → Enable** (`SECURITY.md` points to it).
   - **Secret Protection → Enable** if it is not on yet, then **Push protection → Enable**.
   - **Dependabot alerts → Enable** (Python dependencies in `uv.lock`). Leave Dependabot security and version
     updates off: they open pull requests, and there is no CI to check them.
2. **Settings → Rules → Rulesets → New ruleset → New branch ruleset**: name it, set enforcement to **Active**, add
   the target **Include default branch** (and `dev` by name if wanted), and turn on **Restrict deletions** and
   **Block force pushes**. Leave the bypass list empty. No required status checks: there is no CI.
3. Optional: **New ruleset → New tag ruleset** targeting `v*` with **Restrict updates** and **Restrict deletions**, so
   the tag `v0.5.0` that lyrics-video-app depends on cannot be moved or deleted.
4. **Settings → Actions → General → Actions permissions**: disable actions for this repository (there are no
   workflows), then **Save**.
5. **Settings → General → Features**: turn off Wiki, Projects and Discussions. Issues: off unless you want reports in
   public.

- [ ] Private vulnerability reporting.
- [ ] Secret scanning push protection.
- [ ] Dependabot alerts.
- [ ] Ruleset on the default branch: no force push, no deletion.
- [ ] Actions disabled.
- [ ] Unused features turned off.
- [ ] Setting names checked against GitHub Docs on: 2026-11-01 (for lyrics-video-app); recheck on the settings page.

## 8. Verification

- [ ] A signed-out browser shows only `main`, `dev`, the tag `v0.5.0` and the expected files.
- [ ] The README quick start works from a clean `git clone` over HTTPS without credentials.
- [ ] `uv pip install "audio-spectrum-app @ git+https://github.com/musica-sanare/audio-spectrum-app@v0.5.0"` resolves
  without credentials (what lyrics-video-app needs).
- [ ] No secret scanning alerts under **Security → Secret scanning**.
- [ ] README status updated.
