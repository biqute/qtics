---
name: qtics documentation
description: Sphinx (Furo) docs for the BiQuTe lab's Python instrument drivers, styled as a dilution refrigerator in Lab blue.
colors:
  can: "#0f1b2a"
  can-raised: "#172638"
  can-line: "#2c3d52"
  accent: "#4fa3d1"
  accent-light: "#8cc6e6"
  plate: "#182a3f"
  plate-link: "#e6edf4"
  window: "#f5f7fa"
  ink: "#1b2430"
  ink-soft: "#475466"
  ink-muted: "#566273"
  placeholder: "#9fb0c3"
  link: "#1b6290"
  rule: "#d5dde6"
  tint: "#e7edf3"
  highlight: "#d9eaf6"
  can-dark: "#0a131e"
  window-dark: "#141e2a"
  ink-dark: "#e3e9f0"
  tint-dark: "#1c2836"
  link-dark: "#7fc0e6"
typography:
  display:
    fontFamily: "Archivo, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "2.5rem"
    fontWeight: 780
    lineHeight: 1.08
    letterSpacing: "-0.015em"
    fontVariation: "'wdth' 108"
  headline:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 720
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
  body:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.65
  stage-caption:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 650
    letterSpacing: "0"
  label:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 650
  code:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.7
  group-rubric:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 650
  group-link:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 550
    lineHeight: 1.4
rounded:
  plate: "6px"
  inline-code: "3px"
  control: "4px"
  code-block: "6px"
  panel: "8px"
  window: "10px"
spacing:
  frame-gutter: "0.75rem"
  frame-gutter-narrow: "0.5rem"
  stage-gap: "0.75rem"
  catalogue-gap: "0.75rem"
  plate-inset: "1rem"
  section-top: "3rem"
components:
  stage-plate:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.plate-link}"
    typography: "{typography.stage-caption}"
    rounded: "{rounded.plate}"
    padding: "0.7rem 1rem 0.35rem"
  stage-plate-current:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.can}"
    rounded: "{rounded.plate}"
  reading-window:
    backgroundColor: "{colors.window}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.window}"
  version-select:
    backgroundColor: "{colors.can-raised}"
    textColor: "{colors.plate-link}"
    rounded: "{rounded.control}"
    padding: "0.4rem 0.5rem"
  sidebar-search:
    backgroundColor: "{colors.can-raised}"
    textColor: "{colors.plate-link}"
    rounded: "{rounded.control}"
  code-block:
    backgroundColor: "{colors.can}"
    textColor: "{colors.plate-link}"
    typography: "{typography.code}"
    rounded: "{rounded.code-block}"
    padding: "1rem 1.25rem"
  inline-code:
    backgroundColor: "{colors.tint}"
    rounded: "{rounded.inline-code}"
    padding: "0.1em 0.35em"
  instrument-group:
    backgroundColor: "{colors.tint}"
    textColor: "{colors.ink}"
    typography: "{typography.group-link}"
    rounded: "{rounded.panel}"
    padding: "0.9rem 1.1rem 0.7rem"
---

# Design System: qtics documentation

## Overview

**Creative North Star: "The Cryostat Descent"**

The docs are a dilution refrigerator seen in section. The whole frame is the deep navy vacuum can; the sidebar navigation is the stack of lab-blue stages, read top to bottom from the setup plate down to the API reference; the page itself is a light window inset into the can. A reader always knows which stage they are on because that plate fills with the accent.

The system is a restyle of Furo, not a replacement: every color lands through Furo's own custom properties, layered on a small set of `--qt-*` primitives on `body`. Density is that of a reference manual: a 72ch reading column, generous section breaks, code blocks that look like terminal output on the can's own color. Decoration is structural only: the accent bar on h2 and the accent edge on class signatures, which describe the cryostat rather than ornament the page.

It replaces the stock white-sidebar, purple-accent Python docs look.

**Key Characteristics:**
- Dark navy can frame around a single rounded light reading window.
- Navigation as stage plates with 6px outer corners (caption 6px 6px 0 0, list 0 0 6px 6px) and no top edge; each plate caption is a link.
- Current stage plate fills solid with the accent.
- The instrument catalogue is a grid of tinted, 8px-rounded panels.
- One hue family, Lab blue: the accent for fills and edges, link blue for text links.
- Archivo for all prose and headings, JetBrains Mono for code, both self-hosted.

## Colors

A Lab blue palette: deep navy can and plates, a mid sky-blue accent, and a cool near-white window, with a darker blue for links on the light window.

### Primary
- **Lab Blue** (accent, `--qt-accent`): the plating. The h2 bar and the 3px top border of class signatures; the fill of the current plate; the focus ring, selection tint (#4fa3d159) and the hover border of the version select.
- **Pale Lab Blue** (accent-light, `--qt-accent-light`): the version label on the can.
- **Link Blue** (link, `--qt-link`): links, active TOC entry, instrument-group link hover and caret on the light window. Hover deepens to #124466, visited to #15507a. In dark mode it is #7fc0e6 (link-dark), hover #b5dcf2, visited #6aaed6.

### Neutral
- **Can Navy** (can): page frame, sidebar, mobile header, code-block background (`--qt-code`), and text on the accent current plate.
- **Raised Can** (can-raised): sidebar search, version select, copy button.
- **Can Seam** (can-line): borders of controls on the can, sidebar scrollbar.
- **Plate Navy** (plate): resting stage plates.
- **Plate Link** (plate-link, `--qt-plate-link`): all text on the can and plates, and code-block foreground.
- **Window Pane** (window): the reading window background.
- **Ink / Soft Ink / Muted Ink** (ink, ink-soft, ink-muted): body text, secondary text, group rubrics and TOC title.
- **Rule** (rule) and **Tint** (tint): borders/dividers and secondary surfaces (inline code, API signatures, table headers, instrument-group panels).
- **Placeholder Blue-Grey** (placeholder, #9fb0c3): search placeholder and search icon on the can, chosen for contrast on Raised Can.
- **Highlight** (highlight): targeted/highlighted content on the light window (#1f3f5a in dark mode).

Dark mode keeps the plates and deepens the can and window: can-dark, window-dark, ink-dark, tint-dark, rule #2a3644, soft ink #b0bccb, and link swaps to link-dark (#7fc0e6). It follows both Furo's `data-theme="dark"` toggle and `prefers-color-scheme: dark` unless light is forced.

### Named Rules
**The Plating Rule.** The accent is the plating of the cryostat: it appears as the current-stage fill, as edges (the h2 bar, the class signature top border), and as focus. It is never a background for a resting surface on the reading window.

**The One Hue Rule.** The palette has one hue family, blue. The accent (#4fa3d1) is for fills, edges and focus; link blue is for text. A second accent hue is not part of this system.

## Typography

**Display Font:** Archivo (variable, weight 400-800, width 100-125%), with system-ui fallback
**Body Font:** Archivo
**Label/Mono Font:** JetBrains Mono (400-600), with ui-monospace fallback

**Character:** A sturdy grotesque, slightly widened in the H1, for an instrument-panel voice; a technical mono for code and readouts. Both are self-hosted latin woff2 with `font-display: swap`.

### Hierarchy
- **Display** (780, 2.5rem, 1.08, width 108%, -0.015em, balanced): page H1 only. Drops to 2rem below 67em (intentional).
- **Headline** (720, 1.6rem, -0.01em, 3rem above, balanced): article h2, always preceded by the accent bar.
- **Title** (700, 1.25rem, 2rem above): article h3.
- **Body** (400, 1.0625rem, 1.65): paragraphs and list items capped at 72ch.
- **Stage caption** (650, 1rem, no letter-spacing, sentence case): plate names in the sidebar; the caption is a link, underlined on hover.
- **Label** (650, 0.8125rem, muted): instrument group rubrics; version label (600, 0.8125rem, pale lab blue).
- **Code** (JetBrains Mono, 0.8125rem, 1.7): code blocks; inline code at 0.85em.
- **Group link** (550, 1.0625rem, 1.4): instrument catalogue links.

### Named Rules
**The Sentence Case Caption Rule.** Stage captions override Furo's uppercase: sentence case, letter-spacing 0. Small-caps-style uppercase labels are not part of this system.

**The Readout Rule.** Monospace is reserved for code and measured values (version numbers in the select). Prose never goes mono.

## Layout

The frame is a three-column Furo layout on the can background: sidebar on the left, the reading window in the middle, the page TOC on the right sharing the window's surface. The window sits inset with a 0.75rem gutter on top, right and bottom (none on the sidebar side), and is at least viewport height minus 1.5rem. At 82em and above the right margin becomes max(0.75rem, 50% - 41em), mirroring the left gutter so the window stays centered when zoomed out. Below 67em the window gutter tightens to 0.5rem on the sides and bottom and the mobile header takes the can color.

The sidebar stacks, top to bottom: logo (directly on the can, max 9.5rem wide), version switcher, search, then the stage plates. Each block keeps a 0.75rem side inset from the sidebar edge. Plates are separated by a 0.75rem gap. Inside a plate, entries indent 1rem, sub-levels 1.75rem.

The reading column caps paragraphs and list items at 72ch. Sections open with 3rem above h2 and 2rem above h3. The instrument catalogue (home page and instruments/modules) is an auto-fill grid of min 15rem columns with a 0.75rem gap.

## Elevation & Depth

Flat. No box-shadows anywhere. Depth is conveyed by tonal layering of the cryostat: can (darkest) behind plates (a lighter navy) behind raised controls, and the light window as the one surface that reads as an opening in the can. State is expressed by fill (the current plate fills with the accent) and translucent overlays (#ffffff14 hover on dark plates, #00000014 hover on the current plate; both intentional), never by lifting.

### Named Rules
**The Flat Can Rule.** Nothing casts a shadow. If a surface must stand out, change its tone or give it an accent edge.

## Shapes

Rectilinear and machined. Stage plates are 6px-rounded on their outer corners (caption 6px 6px 0 0, list 0 0 6px 6px); class signatures are square-cornered with a 3px accent top border. The reading window is the only large rounded form (rounded.window, also applied to the right edge of the TOC drawer). Mid rounding is kept to the instrument-group panels at rounded.panel (8px, intentional). Small rounding is kept to functional parts: controls on the can (search, version select) at rounded.control, code blocks at rounded.code-block, inline code at rounded.inline-code.

Recurring geometry: the 3px accent edge (full width on class signatures, a 2.5rem x 3px bar above every article h2).

### Named Rules
**The Accent Edge Rule.** Structural markers are accent lines: the short 3px bar above each h2 and the 3px top border on API class signatures. Sidebar plates carry no top edge.

## Components

### Stage Plates (signature)
The sidebar toctree sections, one per plate.
- **Shape:** no top border; caption radius 6px 6px 0 0 and list radius 0 0 6px 6px, caption padding 0.7rem 1rem 0.35rem, list padding-bottom 0.6rem.
- **Rest:** Plate background, Plate Link text, caption in Plate Link. The caption is a link (wrapped by captions.js), sentence case, 650 weight, 1rem, underlined on hover.
- **Current:** the plate containing the current page fills with Lab Blue (caption and list), text turns Can Navy. On the home page the first plate is current via the `qt-home` class on the navigation wrapper.
- **Current page:** weight 700 with a 2px underline at 0.3em offset.
- **Hover:** #ffffff14 overlay on dark plates, #00000014 on the current plate, 150ms ease-out background transition.

### Reading Window
- **Corner Style:** rounded.window. **Background:** Window Pane. **Border:** none. **Shadow:** none.

### Logo
The BiQuTe logo sits directly on the can, no plate behind it: margin 1.25rem 0.75rem 0.25rem, 0.25rem side padding, max 9.5rem wide.

### Inputs / Fields
- **Version select:** Raised Can, 1px Can Seam border, rounded.control, mono 0.8125rem Plate Link; label "Version" in Archivo 600 Pale Lab Blue. Hover border goes Lab Blue. Disabled (local builds, before versions.json loads) at 0.85 opacity with an explanatory title.
- **Search:** Raised Can, 1px Can Seam border, rounded.control, placeholder Placeholder Blue-Grey (#9fb0c3).
- **Focus (all):** 2px Lab Blue outline, 2px offset.

### Code
- **Blocks:** #0f1b2a background in light mode (the can color), #0d1620 in dark mode with a 1px #2a3a4e edge, Plate Link foreground (#e6edf4), rounded.code-block, padding 1rem 1.25rem, pygments `a11y-dark`. Emphasized lines get a full-bleed #4fa3d133 band, forced with `!important` over the pygments highlight.
- **Inline:** Tint background, no border, rounded.inline-code, 0.85em. Copy button sits on Raised Can with a Can Seam border.

### Navigation (page TOC)
Furo's right-hand contents in Soft Ink, active entry Link Blue. Code-literal entries render as plain text, one ellipsized line each.

### Instrument Groups
Catalogue grid cells (`.qt-group`, on the home page and instruments/modules): Tint background, rounded.panel (8px), padding 0.9rem 1.1rem 0.7rem, muted 0.8125rem Label rubric, a bare list of links in Ink at 550 weight (no bullets, no underline until hover; hover turns Link Blue with underline); code literals inside render as plain link text.

### API Signatures
Class and exception signatures sit on a plate: square corners, 3px Lab Blue top border, Tint background.

## Do's and Don'ts

### Do:
- **Do** route every color through Furo's custom properties backed by the `--qt-*` primitives, and define both light and dark values.
- **Do** keep the 3px Lab Blue top border on class signatures and the 2.5rem x 3px accent bar above every article h2.
- **Do** keep plates at 6px outer corners (caption 6px 6px 0 0, list 0 0 6px 6px) and the reading window as the only large rounded surface (rounded.window); catalogue panels stay at rounded.panel.
- **Do** mark the current stage by filling its plate with Lab Blue and switching its text to Can Navy.
- **Do** keep stage captions in sentence case, and keep them as links.
- **Do** use JetBrains Mono only for code and measured values; Archivo for everything else; self-host both.
- **Do** keep code blocks dark on the can's own color in both themes.

### Don't:
- **Don't** add box-shadows; depth comes from tone (The Flat Can Rule).
- **Don't** introduce a second accent hue beyond the blue family.
- **Don't** fill resting surfaces on the reading window with the accent; accent is edge, focus and current state only.
- **Don't** add uppercase tracked labels or kickers above headings.
