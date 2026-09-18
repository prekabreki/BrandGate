# site/tools

Source captures for the tool cards on the site.
`site/build_assets.py` cuts these to the JPEGs the page loads, so the page never drifts from what was captured.

One rule: every card face is a real screenshot of the tool running, at a scroll position the tool actually has.
Nothing is composited, retouched or mocked up.
Where a tool has no UI to screenshot, the card is real terminal output instead, and the page says so.

| file | what it is | how it was captured, 2026-09-18 |
|---|---|---|
| `shot-gate.png` | Handsel Gate, the review UI from #5 | The deployed Lovable build at `handsel-gate.lovable.app`, Chrome at 1600 by 1000. Cropped on the build to drop the Lovable badge in the corner. |
| `shot-swice.png` | Swice Daily, today's page | The live instance on the Pi over Tailscale, Chrome at 1500 by 1000. The day's suggestion, no submitted writing on screen. |
| `shot-fetchforge.png` | FetchForge, the conversion panel | `github.com/prekabreki/FetchForge` at HEAD, its own server on 8765, scrolled to the Video URL and Conversion sections. The auth panel above them is a cookie state, not the tool working, so the card starts below it. |
| `shot-scorescout.png` | ScoreScout, a real analysis report | `github.com/prekabreki/ScoreScout` at HEAD, run over Joplin's Maple Leaf Rag from the music21 corpus: `cli.py maple_leaf_rag.musicxml --no-llm --format html`. 579 of 579 chords identified locally, no model call. |
| `shot-deciwaves.png` | DeciWaves, the CLI | Rendered from `deciwaves-card.html` beside this file. Every line in it is real output from `deciwaves 0.1.0` (`--help` and `ds --help`). It stops at the invocation: this box has none of the three games installed, so there is no run to show, and inventing one was not an option. |

ck3's card face is not here.
It comes from the chronicler's own repo (`docs/images/chronicle.png`) through the `TOOLS` list in `build_assets.py`, which is the better pattern: the site shows what the repo shows.
The four other public tools ship no screenshot in their READMEs yet.
Putting these captures there and fetching them the same way would retire this folder.
