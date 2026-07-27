---
name: build-lesson-slides
description: Create multi-subject 16:9 LaTeX Beamer teaching decks and synchronized speaker notes from a subject, audience or grade, topic, and duration. Use whenever users ask for 课件, 教学PPT, lesson slides, teaching PDFs, knowledge-point explanations, formula derivations, text annotation, experiments, timelines, maps, worked examples, or lecture notes where editable .tex and PDF output are acceptable. Route through subject-specific pedagogy for Chinese, English, mathematics, physics, chemistry, biology, history, geography, computer science, or a general fallback. Do not use when the user specifically requires an editable .pptx file.
---

# Build Lesson Slides

Create a concise classroom deck, synchronized speaker notes, source assets, and rendered previews. Treat the LaTeX source as the single source of truth and deliver PDF rather than editable PowerPoint.

## Workflow

1. Collect or infer subject, knowledge point, audience or grade, language, duration, and lesson goal. Ask only when a missing value would materially change the lesson.
2. Create or reuse the course directory described in Workspace Layout. Do not build lesson artifacts in the Skill directory when the Skill is invoked from another workspace.
3. Read references/subject-index.md. Then read references/common-pedagogy.md and exactly one matching subject reference:
   - references/subject-math.md
   - references/subject-chinese.md
   - references/subject-english.md
   - references/subject-physics.md
   - references/subject-chemistry.md
   - references/subject-biology.md
   - references/subject-history.md
   - references/subject-geography.md
   - references/subject-computer-science.md
   - references/subject-general.md
4. Run scripts/doctor.py --write before the first build after installation. Reuse .runtime/environment.json later. Re-run only when paths fail, the environment changes, or compilation fails.
5. Draft a slide outline before writing LaTeX. Give every slide one teaching job and one takeaway. Match the requested duration.
6. Copy assets/lesson-template.tex, assets/lesson-theme.sty, and assets/lesson-elements.json into the course directory. Replace all sample content and mapping entries.
7. Create only visuals that materially improve understanding.
8. Write speaker-notes.md in the same slide order.
9. Run scripts/build.py lesson.tex --notes speaker-notes.md --elements lesson-elements.json --output-dir . from the course directory.
10. Run scripts/contact_sheet.py previews previews/contact-sheet.png when Pillow is already available. Inspect the contact sheet first, then open only suspicious pages at full size. If Pillow is unavailable, inspect previews in small batches; do not install it solely for the contact sheet.

## Workspace Layout

Create one English subject directory under the user's current working directory, then one course directory named for the current knowledge point. Reuse an existing directory without adding numeric or timestamp suffixes.

    <user-workspace>/
      mathematics/
        lagrange-mean-value-theorem/
          lesson.tex
          lesson-theme.sty
          lesson-elements.json
          speaker-notes.md
          lesson.pdf
          assets/
          previews/

Use these stable subject names: mathematics, chinese, english, physics, chemistry, biology, history, geography, computer-science, and general. Preserve the user's knowledge-point wording for the course directory or use a concise kebab-case English translation when unambiguous. Keep all lesson-specific generated files, compiler intermediates, caches, previews, and final deliverables inside that course directory.

## Environment Rules

- Require a runnable Python interpreter, XeLaTeX, pdfinfo, and pdftoppm. Do not trust PATH entries without executing them.
- Prefer a local .runtime/venv created by doctor.py --create-venv. Do not distribute the virtual environment with the Skill.
- Keep Python dependencies minimal. Install scripts/requirements.txt only when Python figures are needed.
- After creating the virtual environment and receiving approval for dependency download, run its Python with -m pip install -r scripts/requirements.txt.
- Treat image generation as optional. Check host tool availability at runtime; a Python process cannot reliably detect Codex image tools.
- If a required component is missing, stop compilation and tell the user exactly what is missing. Do not silently install system software.

## Visual Routing

- Use LaTeX and TikZ for formulas, labels, simple geometric constructions, and precise structural diagrams.
- Use Python and Matplotlib for plots, coordinate geometry, experimental curves, numeric diagrams, and charts that need exact control.
- Use the host image-generation tool when available for aesthetic backgrounds, scenes, visual metaphors, historical atmosphere, and illustrations that do not require exact labels. When directly using the OpenAI Image API, prefer gpt-image-2.
- If image generation is unavailable or does not materially improve the lesson, continue without blocking and build restrained backgrounds with LaTeX or TikZ.
- Never ask an image model to render formulas, quotations, labels, or slide text. Overlay all text in LaTeX.
- Generate a combined 2-by-2 sheet only for related decorative illustrations when it reduces cost. Crop it with Python or Pillow. Do not batch precise teaching diagrams this way.

## Background Safety

- Choose exactly one background system for the entire deck: generated-image backgrounds or LaTeX/TikZ decorative backgrounds. Never mix the two systems in one deck. TikZ teaching diagrams, plots, and formula annotations are content and may still be used with image backgrounds.
- In generated-image mode, create separate 16:9 background files for at least the cover, ordinary content, and closing summary. Add a separate section or middle-transition background when the deck uses those pages. Generate each file separately from one shared visual brief; do not generate one composite image and crop it into page types.
- Name them predictably: assets/cover-bg.png, assets/content-bg.png, optional assets/section-bg.png, and assets/closing-bg.png. Reuse the quiet content background across ordinary pages; create a second content variant only when a materially different layout requires it.
- Make content-bg the quietest asset: no focal subject, no strong edge, and low detail across the title and body regions. Do not add decorative TikZ circles, ribbons, waves, or corner shapes over any generated background.
- With LaTeX/TikZ backgrounds, do not use generated background images anywhere in the deck.
- Keep backgrounds minimal and reserve a plain title band across the full slide width. No shape, curve, texture, or illustration may enter the title band.
- Give the cover, section or middle transitions, and closing summary distinct compositions while keeping one palette, texture, and visual language.
- Reserve a low-detail text-safe region in every image prompt, normally 55-65 percent of the canvas on the intended text side.
- Keep high-detail subjects and strong contrast outside the text-safe region.
- Place every background at the true bottom layer with `\LessonBackground{...}` immediately before `\begin{frame}`. This macro uses Beamer's background template. Never place a background with an overlay node, foreground `\includegraphics`, or a TikZ picture created after slide content.
- Keep the layer order fixed: full-slide background, optional contrast panel, title/body/formulas/teaching diagrams, then invisible clickable annotations. All readable information must remain above the background.
- Place LaTeX content only inside the reserved region or on a high-opacity panel. Switch or clear the background before the next frame as required.
- Render and inspect the composed slide. If the background competes with text, crop, dim, blur, cover, or regenerate it.

## Content Budget

- Keep one main idea per slide.
- Use three to five short points on ordinary slides; keep each point to about two lines.
- Prefer a diagram, formula, excerpt, or example over explanatory paragraphs.
- Permit denser content only for necessary derivations, source-text annotation, close reading, tables, or definitions. Split before shrinking text.
- Put full explanation, timing, emphasis, and transitions in speaker-notes.md.

## Title Style

- Use short, neutral classroom titles, normally 2-10 Chinese characters or one concise noun phrase.
- Prefer standard labels such as 课程目标、问题引入、定理、几何意义、辅助函数、定理证明、使用条件、常用推论、例 1、例 2、课堂练习、课程回顾.
- Put explanations, metaphors, questions, conclusions, and transitions in the slide body or speaker notes, not in the title.
- Avoid promotional or conversational titles such as “先把目标放在桌面上”, “从条件到应用”, “搭好证明的桥”, “函数变化的限速”, or other decorative AI-style phrasing.

## Footer Style

- Keep the footer plain: course title only on the left and current page number only on the right.
- Align both items to the same outer margins as the slide body. Do not add a leading rule, icon, bullet, label, separator, total-page count, or decorative character.
- Use the short course title through `\insertshorttitle`; do not hard-code a lesson name in the theme.
- Omit the footer on plain cover pages.

## Speaker Notes Contract

Create exactly one second-level heading per slide:

    ## 第 6 页：页面标题

Under each heading include:

- 页面目标
- 建议时长
- 讲解内容
- 强调内容
- 过渡语

Keep page numbers consecutive and equal to the compiled PDF page count. Do not put internal production notes on visible slides.

## Clickable Element Mapping

- Wrap every displayed formula, and any inline formula or text span that should be queryable, with `\LessonElement{stable-id}{rendered-content}`. Use IDs such as `s04-mvt-formula`; never reuse an ID.
- Add exactly one matching object to lesson-elements.json with `id`, `page`, `kind`, and the original `source_tex` or `source_text`.
- Treat the manifest source as the canonical text sent to the question-answering frontend. Keep it semantically identical to the rendered content.
- `\LessonElement` emits a `lesson://element/<id>` PDF link annotation. A PDF.js frontend can read each annotation rectangle and resolve its ID against lesson-elements.json; multiple rectangles with the same ID are one logical element.
- Keep mappings invisible. Do not use colored link borders or place separate transparent overlays by hand.

## Output Contract

Deliver:

- lesson.tex
- lesson-theme.sty
- lesson.pdf
- lesson-elements.json
- speaker-notes.md
- assets/ for generated or sourced visuals
- previews/ containing every rendered slide and, when available, contact-sheet.png

Preserve source provenance for externally sourced claims and assets. Include short visible citations or a final references slide when the lesson relies on research.

## Quality Gate

- Verify subject facts, formulas, quotations, dates, terminology, units, and worked-example answers.
- Verify that the deck follows the selected subject profile rather than a generic presentation outline.
- Verify slide count, notes count, and order.
- Verify a 16:9 page ratio.
- Verify no background pattern overlaps or weakens text.
- Verify the deck uses only one background system and that every title band is completely clear.
- Verify generated-image mode contains separate cover, content, and closing assets, plus a section asset when needed, and that every background is applied through the Beamer background template below all information.
- Verify titles are short, neutral, and descriptive rather than conversational or metaphorical.
- Verify the footer contains only the left-aligned course title and right-aligned page number, with no leading rule or extra character.
- Verify no unintended overlap, clipping, broken glyphs, unresolved placeholders, or unreadably small text.
- Verify every displayed formula is wrapped by `\LessonElement`, every mapped ID is unique, and lesson-elements.json matches the TeX IDs and page numbers.
- Deliver only after inspecting every preview at full size.
