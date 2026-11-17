# Print Parameter Explorer – 3D-printing test data viewer (PETG/PLA, week 1)

Single offline HTML file (`print_parameter_explorer.html`, ~3.3 MB) that loads a parameter sheet (.xlsx, fixed template) and plots print settings against the visual grades Clarity and Stability. Built in stages with checks after each; final version 16 Nov 2026 (rev. 4: per-item text sizes, live export preview, Roboto audit).

## Deliverables
- `print_parameter_explorer.html` – the tool; includes the user guide (collapsible section at the top) and a "Download blank template" button. Runs offline; data never leaves the computer.
- `print_parameter_template.xlsx` – blank template (Parameters / Instructions / Grading Metrics sheets, score validation 1–5, notes column O).
- `print_parameter_explorer_source.tar.gz` – source (`src/`), `build.py` (inlines libraries + fonts into one HTML), `make_template.py`, all current test scripts and the font audit. Rebuild: `npm install xlsx@0.18.5 plotly.js-basic-dist-min jspdf svg2pdf.js @fontsource/roboto @expo-google-fonts/roboto`, then `python3 build.py`.

## Data rules (fixed template)
- Data sheet = any sheet with "S/N" in A2. Headers rows 1–3 (checked cell by cell), data from row 4, columns A–N:
  S/N · Material · Colour · Layer Height · Temperature · e1 · e2 · v1 · v2 · a1 · a2 · t1 · Clarity · Stability.
- Blank / "-": Layer Height → 2 mm (assumed, flagged); Colour → "unspecified"; e2/v2/a2 → "not used". Any other blank → row skipped with reason.
- Scores must be whole numbers 1–5. Columns right of N and cell fills are ignored. Parameters that never vary in a file (week 1: Colour, a1, a2) are hidden automatically.
- Units: e = mm/s, v = mm/s, a = mm/s², t = s, layer height = mm, temperature = °C.

## Views kept (after review)
- **B · 2D map** – X/Y = two parameters, colour = score. All prints plotted; dotted lines connect only prints whose *other* settings are identical ("R1: show every print, connect only like with like"). Pooling across different settings was rejected because on week-1 data it produces false trends (e.g. pooled "lower temperature = clearer" is driven by PETG at 265 °C and the later two-speed prints at 210 °C).
- **D · Clarity vs Stability** – each print in its score cell, coloured by a chosen parameter.
- **E · History** – scores in S/N order + up to two overlay parameters on their own right axes (dual-axis caveat shown in UI and caption), per-line line type, top-n callouts.
- Removed on request: line plot (A), 3D map (F). Surface interpolation (stage 4) skipped – with strict like-for-like groups only 3–4 prints per surface on week-1 data.

## Top-n ranking (History)
Rank by Clarity, Stability, Combined (sum) or Weakest score then combined (default). Competition ranking; all prints tied at the cut-off are included. Shown as a band + rank label (at the foot of the band) + ring per top S/N, a settings table under the chart, and a caption line in exports. Week 1: "top 1" by weakest score = 9 prints at 5/5 (S/N 14, 15, 16, 28–33).

## Styling & export
- Graph area is **16:9** on screen, matching the slide exports.
- **Typeface:** Roboto everywhere – page, controls, graphs (incl. Plotly toolbar tooltips) and exports (embedded in PNG and PDF; SVG via @font-face). Verified by an audit of every visible text element and of the fonts used in the PDF.
- **Text sizes per item:** axis titles (default 13), tick labels (12), legend (12), point labels – S/N and rank labels (10) – plus caption (12, export only). Sliders 6–40 px; apply to the on-screen graph and every export. Sizes are px of the 1600 px-wide export layout: on a 16:9 slide 10 px ≈ 6 pt, so ~24 px (≈ 14 pt) or more is advised for projection. The space below the plot grows with the chosen tick/axis sizes so the caption never overlaps. (Replaces the earlier ×1 / ×1.3 / ×1.6 text option.)
- **Export preview:** live picture under the export options of exactly what will be saved (size, proportions, background – checkerboard for transparent – text sizes, caption). PNG and SVG are made from this exact picture (exported SVG verified identical to the preview); the PDF is converted from it.
- Score colour ramps (blue/orange/aqua/magenta/grey) and categorical palette validated (CVD + contrast) against #000; custom two-colour ramp; per-entry colour, opacity (baked into colours so PDF matches PNG) and line type (History).
- History: fading an overlay also fades its own right-hand axis (axis line, ticks, tick labels, title) by the same amount; the left Score axis is shared by Clarity and Stability and is not faded.
- Export PNG / SVG / PDF; background black or transparent; optional caption (view, axes, S/Ns, top-n, assumptions, source).
- Sizes:
  - 16:9 slide Full HD 1920 × 1080 (PNG tagged 144 dpi) and 4K 3840 × 2160 (288 dpi, default) – both size to exactly 13.33 × 7.5 in, a standard widescreen slide; PDF page 960 × 540 pt.
  - A4 / A3 landscape at 300 dpi for print (PDF page = exact A4 / A3).

## Verification (final build, rev. 4)
- Parser vs independent pandas read: 462/462 cells; 5 deliberately broken files give the expected messages; filled template parses identically to the week-1 file.
- Like-for-like grouping vs independent Python implementation: 49/49 axis pairs identical.
- Delaunay (used for connection edges): 203 random/grid sets – exact hull coverage, empty-circumcircle property.
- Labels/hover: 100 view combinations, every S/N labelled exactly once. History: 66 overlay combinations match the sheet; top-n rankings checked by hand.
- Headless Chrome: 126 UI checks – loading, 16:9 preview in every view, every option, colours, opacity incl. overlay-axis fading, line types, top-n, per-item text sizes in all three views (layout and rendered sizes), export preview following every option, hover, reset, all export formats / sizes / backgrounds (pixel size, dpi tag, PDF page size, exported font sizes), guide, template download – all pass, no console errors.
- Font audit: no visible text element in any view resolves to a font other than Roboto; Roboto 400/500/700 loaded; PDF text uses only Roboto.
- Bugs found and fixed by testing: PDF ignored nested opacity (now baked into colours); Plotly drew size-varying markers at 70 % opacity by default; top-n rings ignored the chosen colour (open markers take `marker.color`); Plotly toolbar tooltips used Open Sans (now Roboto).
- Not tested: Firefox / Safari (browsers could not be installed in the build environment) – check once manually.

## Known limitations / reading caveats
- Scores are visual ordinal grades; repeats of identical settings vary (S/N 1–4: different filament reels).
- S/N 23 changes six parameters at once – no view can attribute the effect.
- Geometry and reel are not recorded in the sheet; S/N 5–6 groupings rely on the assumed 2 mm layer height.
- History assumes S/N order = test order.
- Very large point-label sizes crowd the fullest Clarity vs Stability cells (e.g. 5/5 with 9 prints); reduce the point-label size or switch S/N labels off there.
