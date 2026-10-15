# Ourogen Coworker: pitch deck and demo

| File | What it is |
|---|---|
| `demo/ourogen-demo.mp4` | 2-minute product demo recorded from the running app: replying to email from chat, sending the coworker to a meeting, the Today view, and onboarding. Re-record with `scripts/demo/record_demo.py`. |
| `pitch-deck/ourogen-pitch-deck.pdf` | 14-slide pitch deck, ready to send. |
| `pitch-deck/ourogen-pitch-deck.html` | The same deck as one web page. |
| `pitch-deck/slides/*.html`, `deck.json` | Deck source (one file per slide; speaker notes are in each slide's `<aside>`). |
| `pitch-deck/build.py` | Rebuilds the HTML and PDF from the source: `python materials/ourogen-coworker/pitch-deck/build.py --pdf` |

Bracketed placeholders such as `[$__]`, `[__%]` and `[Founder name]` are figures still to fill in before presenting: the raise, use of funds, pilot users, revenue and contact details. None of the deck's numbers are invented; the product figures (tests, eval cases, detection rates) come from this repository.
