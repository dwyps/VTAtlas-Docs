# VT Atlas documentation

Source for **https://docs.vestro.hr**, the documentation for VT Atlas, a region and zone plugin for
Unreal Engine 5.8.

Docusaurus 3, deployed to Cloudflare Pages. `docs/` is also a working Obsidian vault.

## The one idea holding this together

**`docs/` is simultaneously the site source and an Obsidian vault, with no transform between them.**
The folder a buyer opens in Obsidian is byte-for-byte the folder that builds the site. There is no
generation step, no intermediate tree and no per-file dialect switching.

That works because of three settings:

- `markdown.format: 'md'` in `docusaurus.config.ts`. CommonMark, not MDX. MDX fails on C++ generics and
  its `import` and JSX syntax is meaningless inside Obsidian.
- `useMarkdownLinks: true` and `newLinkFormat: "relative"` in `docs/.obsidian/app.json`. Obsidian keeps
  its link autocomplete but writes `[Concepts](./02_concepts.md)`, which Docusaurus resolves natively.
- Numeric prefixes on folders and files. Docusaurus strips them from URLs and sidebar labels; Obsidian
  sorts alphabetically. The vault tree and the site sidebar therefore read in the same order, with no
  `sidebar_position` frontmatter anywhere.

## Authoring

```bash
npm install
npm start                        # dev server with hot reload
npm run build                    # production build into build/
python tools/check_markdown.py   # the authoring gate
```

Run the gate before committing. It is not style policing: the two failures it exists to catch are
**invisible in the rendered output**.

- **A type expression outside backticks** builds green and *silently deletes the type name*, in
  Obsidian too. Written bare, "returns TArray of FGameplayTag" in angle-bracket form renders as
  "returns TArray". Always backtick type expressions. Never use a backslash escape; it prints
  literally in some renderers.
- **`%%comments%%`** are invisible in Obsidian's editor and published in full on the site.

Callouts use the uppercase GitHub form, which is the only spelling that renders natively in Obsidian,
natively on GitHub, and degrades to a plain blockquote everywhere else:

```markdown
> [!NOTE]
> Five types only: NOTE, TIP, IMPORTANT, WARNING, CAUTION.
```

Banned: `[[wikilinks]]`, `![[embeds]]`, `==highlights==`, `%%comments%%`, `^block-ids`, `:::directives`,
MDX imports, and `.mdx` files. The gate enforces all of them and every clause is mutation-verified.

## Opening the vault

Obsidian, **Open folder as vault**, point it at `docs/`. Graph view, backlinks, the file tree and the
link picker all work, because a graph over relative Markdown links is still a graph.

Buyers get the same thing without this repo: Fab ships plugin source, so the vault is on disk at
`Plugins/VTAtlas/Docs` once VT Atlas is installed.

## Media

Stills are **AVIF**, clips are **H.264 MP4**, and neither goes near Git LFS.

```bash
# still
ffmpeg -y -i raw/shot.png -vf "format=rgb24,scale='min(1600,iw)':-2:flags=lanczos" \
  -c:v libaom-av1 -still-picture 1 -crf 32 -cpu-used 2 -pix_fmt yuv444p -frames:v 1 \
  docs/03_reference/media/shot.avif

# clip (drop -tune stillimage and use -crf 23 for real gameplay)
ffmpeg -y -ss IN -t DUR -i raw/clip.mkv \
  -vf "scale='min(1280,iw)':-2:flags=lanczos,format=yuv420p" \
  -c:v libx264 -preset veryslow -crf 26 -tune stillimage -profile:v high -level 4.0 \
  -movflags +faststart -an docs/01_getting_started/media/clip.mp4
```

`yuv444p` keeps coloured UI text sharp. No animated GIF: a loop over five seconds cannot offer the
pause control WCAG 2.2.2 requires, and `<video controls>` gets it for free. No LFS: whether Cloudflare
smudges LFS pointers during clone is undocumented, and the failure mode is a deployed site full of
130-byte text files where the screenshots belong.

Diagrams are **committed SVGs** under a page's `media/` folder, not Mermaid fences.

Mermaid looks like the obvious choice and does not work here: with `markdown.format: 'md'` a
```` ```mermaid ```` fence is replaced by an empty HTML comment on the site, because Docusaurus turns
it into a React component and CommonMark mode has no JSX to render one. It renders correctly in
Obsidian, so the author sees a diagram and the reader sees nothing, and the build stays green. The
gate rejects the fence for that reason. Give every SVG a `<title>` and `<desc>` and reference it with
alt text.

## Deployment

Cloudflare Pages, Git integration (never Direct Upload, which cannot be converted to Git later).

| Setting | Value |
|---|---|
| Build command | `npm run build` |
| Output directory | `build` |
| Node | pinned by `.nvmrc` |

## Versioning

Not switched on. There is one `docs/` folder and one copy in the vault. The **URL shape** is set today
(`/docs/1.0/...`) because that is the expensive part to change later.

The trigger to actually cut a version is not shipping 1.1. It is the first time an engine version is
**dropped** from the supported set while development continues, because studios frozen on that engine
still need their docs reachable. At that point run `npm run docusaurus docs:version 1.0`, then relabel
the current version to 1.1. Every existing `/docs/1.0/...` URL keeps working.

## Why this stack

`docs/research/DOCS_STACK_RESEARCH.md` in the VTSuite repo has the full comparison: six candidate
generators and four cross-cutting investigations. Short version: Quartz is the only option with a
published graph view but has no versioning at all, MkDocs Material reaches end of life on 2026-11-05,
and Obsidian Publish serves crawlers raw wikilink source behind 239 KB of JavaScript.
