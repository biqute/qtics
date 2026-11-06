---
version: 1
slug: "docs-source"
primary_target: "docs/source"
related_targets: []
---

# qtics documentation site

Scope: the Sphinx (Furo) docs site in docs/source, all pages. Visitor mode: Read.
Audience: BiQuTe lab members looking up a driver or writing an experiment script.
Constraints: keep Sphinx + Furo, no new dependencies; keep the BiQuTe logo; version switcher (latest + previous two releases).

## Direction contract

THESIS: The docs descend like a dilution refrigerator: the frame is the vacuum can and the navigation is the stack of gold-plated stages, from 300 K setup down to the 10 mK API reference. Refuses the stock white sidebar + purple accent Python docs.
OWN-WORLD: Anthracite can (#16191d) frame; gold-plated copper (#c8964a / #e3c07f) stage plates with a thin thermal link between them; a light paper reading window (#f6f4ef) inset into the can with rounded corners; ice blue (#7fb3c8) only for cold states. Archivo for text, JetBrains Mono for code and temperature labels.
STORY: A reader sees where they are by stage, finds a driver from the instrument list on the home page, copies a working snippet, and can switch to a past release.
FIRST VIEWPORT: Left: dark sidebar with logo, version switcher, search, then plates labelled 300 K / 50 K / 4 K / 10 mK with the current plate solid gold. Right: inset paper window with H1 "Drive the lab's instruments from Python.", one sentence, a dark code block, then the instrument list grouped by type with gold top rules. No kicker.
FORM: chosen form: Cryostat Stages, position 1 on the ordered list (IMPECCABLE'S PICK). seed:88b9c4a61530a8fd
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
