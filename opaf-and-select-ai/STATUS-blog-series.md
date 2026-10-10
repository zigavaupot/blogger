# Status: "Select AI Agent meets OPAF" blog series (paused 2026-10-08)

## Done
- Series split agreed: Part 0 (series overview) + Parts 1–8, files `opaf-select-ai-0N-*.md` + `.html` (HTML generated from MD).
- All MD reviewed by author through Part 8; HTML generated and validated for Parts 0–8 (code blocks verified identical to MD).
- Images renamed to placeholder names in `images/`; image URLs use `https://zigavaupot.github.io/blogger/opaf-and-select-ai/images/`.
- `02-dynamic-group.png` is a blurred copy (OCIDs). Unblurred original `Posnetek zaslona 2026–10–07 ob 17.23.10.png` is still in images/ — do not push.
- Part 5 title changed to "No-code Select AI Agent" (also in Part 0 list).
- Converter: `python3 tools/md2blogger.py <file.md>` → writes `<file>.html` and runs the checklist.

## Open
1. Featured images: DONE — all 9 posts use images/select-ai-opaf-blog-series.png.
2. Links: `SERIES-URL` (Parts 1–8), `PART1-URL`…`PART8-URL` (Part 0) — replace after publishing.
3. Missing screenshots (`IMAGE-TBD` + TODO comment): GenAI Playground (Part 2), Select AI node palette (Part 4).
4. Screenshots that contradict text (used as-is so far): 11 Flow A canvas shows OABOOTCAMP_SALES_SQL; 18 Flow D canvas has third Show SQL bridge (Part 8 text mentions it — remove phrase if retaken); 14 C1 dropdown on Chat, not Narrate.
5. Decide whether "All six flows compared" and "Key takeaways" stay in Part 0.
6. Parts 1–4, 6–8 titles: short alternatives proposed, author kept current ones (only Part 5 changed).
7. Unrelated screenshot `Posnetek zaslona 2026–10–08 ob 09.54.54.png` (personal data) in images/ — don't push.
8. CSS: line 21 stray fragment FIXED; zv-table-compact rules added — push BLOGGER/blogger-post-new.css to GitHub.

## Suggested labels
- Part 0: Series, Hero, OPAF, Select AI, MCP, Autonomous Database
- Parts 1–5, 8: Posts, OPAF, Select AI, Autonomous Database
- Parts 6–7: Posts, OPAF, Select AI, MCP, Autonomous Database
