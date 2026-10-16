#!/usr/bin/env python3
"""Generate the /learn/<language>/ pages, the /learn/ hub and sitemap.xml.

Every number and word on these pages comes from the app's own decks, so a
page can never promise a deck the app does not have. Re-run after a deck
changes:

    python3 _tools/learn_pages.py                       # decks next door
    python3 _tools/learn_pages.py --decks path/to/decks

Reads ../vocabswiper_ios/decks/words_<code>_en.json and
../vocabswiper_ios/assets/languages.json by default.
"""
import argparse
import html
import json
import os
import re
from collections import Counter
from datetime import date

SITE = "https://vocabswiper.com"
APP_STORE = "https://apps.apple.com/app/id6782795150"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Display names where the app's exonym is not what a learner searches for.
NAME_OVERRIDE = {"tl": "Filipino"}
RTL = {"ar", "he", "fa", "ur"}
STARTERS = 24

# The level scale each language is graded on, easiest first.
SCALES = {
    "ja": ("JLPT", [f"jlpt:N{n}" for n in (5, 4, 3, 2, 1)], lambda t: t.split(":")[1]),
    "zh": ("HSK", [f"hsk:{n}" for n in range(1, 7)], lambda t: "HSK " + t.split(":")[1]),
    "ko": ("TOPIK", [f"topik:{n}" for n in range(1, 7)], lambda t: "TOPIK " + t.split(":")[1]),
}
CEFR = ("CEFR", [f"cefr:{l}" for l in ("A1", "A2", "B1", "B2", "C1", "C2")], lambda t: t.split(":")[1])


def esc(s):
    return html.escape(str(s), quote=True)


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load(decks, langs_path):
    langs = json.load(open(langs_path, encoding="utf-8"))
    out = []
    for l in langs:
        code = l["code"]
        path = os.path.join(decks, f"words_{code}_en.json")
        if code == "en" or not os.path.exists(path):
            continue
        rows = json.load(open(path, encoding="utf-8"))
        name = NAME_OVERRIDE.get(code, l["exonym"])
        out.append({"code": code, "name": name, "endonym": l["endonym"],
                    "slug": slug(name), "rows": rows})
    return sorted(out, key=lambda x: x["name"])


def levels(lang):
    scale_name, tags, label = SCALES.get(lang["code"], CEFR)
    counts = Counter(t for r in lang["rows"] for t in r.get("tags", []) if t in tags)
    present = [(label(t), counts[t]) for t in tags if counts[t]]
    graded = sum(c for _, c in present)
    rest = len(lang["rows"]) - graded
    if rest > 0 and lang["code"] in SCALES:
        # Chinese and Korean decks run past the top of their exam scale.
        present.append(("Beyond " + scale_name, rest))
    return scale_name, present


def starters(lang):
    code = lang["code"]
    scale_tags = SCALES.get(code, CEFR)[1]
    rows = [r for r in lang["rows"]
            if not any(t.startswith("quality:") for t in r.get("tags", []))]
    pool = []
    for tag in scale_tags:  # easiest level that has enough clean words
        pool += [r for r in rows if tag in r.get("tags", [])]
        if len(pool) >= STARTERS * 2:
            break
    if len(pool) < STARTERS:
        pool = rows
    has_zipf = any(r["translations"][code].get("zipf") for r in pool)
    if has_zipf:
        pool = sorted(pool, key=lambda r: -(r["translations"][code].get("zipf") or 0))
    picked, seen = [], set()
    for r in pool:
        t = r["translations"][code]
        word, gloss = t.get("word", "").strip(), r["translations"]["en"].get("word", "").strip()
        # Short glosses read as a word list; long ones are grammar notes.
        if not word or not gloss or len(gloss) > 22 or word.lower() in seen:
            continue
        seen.add(word.lower())
        picked.append((word, t.get("romanization", "").strip(), gloss))
        if len(picked) == STARTERS:
            break
    return picked


HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{site}/shots/og.jpg">
<link rel="icon" href="{up}favicon.ico?v=4" sizes="any">
<link rel="icon" type="image/png" href="{up}favicon.png?v=4" media="(prefers-color-scheme: light)">
<link rel="icon" type="image/png" href="{up}favicon-dark.png?v=4" media="(prefers-color-scheme: dark)">
<link rel="icon" type="image/png" href="{up}favicon.png?v=4">
<link rel="apple-touch-icon" href="{up}icon.png?v=3">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}learn/learn.css?v=4">
{jsonld}
</head>
<body>
<div class="navbar"><div class="wrap"><nav>
  <a class="brand" href="{up}"><img class="brand-img" src="{up}icon.png?v=3" alt="">Vocab Swiper</a>
  <a class="cta-mini" href="{store}" target="_blank" rel="noopener">Get the app</a>
</nav></div></div>
"""

FOOT = """<footer><div class="wrap foot-row">
  <span class="foot-brand"><img src="{up}icon.png?v=3" alt="">Vocab Swiper · © 2026 Strate Labs</span>
  <span><a href="{up}learn/">Languages</a> &nbsp;·&nbsp; <a href="{up}privacy/">Privacy</a> &nbsp;·&nbsp; <a href="{up}support/">Support</a></span>
</div></footer>
</body>
</html>
"""

BADGE = """<a class="badge" href="{store}" target="_blank" rel="noopener" aria-label="Download on the App Store">
  <svg viewBox="0 0 384 512"><path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z"/></svg>
  <span class="txt"><small>DOWNLOAD ON THE</small><span>App Store</span></span>
</a>"""

METHOD = """<section class="method">
  <h2>How Vocab Swiper teaches {name}</h2>
  <div class="steps">
    <div class="step"><b>Recall first</b><p>Each {name} word is shown without its meaning. You try to remember it before you reveal it, which is what makes it stick.</p></div>
    <div class="step"><b>Spaced repetition</b><p>FSRS, the memory model behind modern Anki, brings each word back right before you'd forget it.</p></div>
    <div class="step"><b>Hear it, say it</b><p>Native audio for every word, example sentences in context, and speaking practice with pronunciation feedback.</p></div>
  </div>
</section>"""


def lang_page(lang, all_langs):
    code, name, n = lang["code"], lang["name"], len(lang["rows"])
    scale, lv = levels(lang)
    words = starters(lang)
    url = f"{SITE}/learn/{lang['slug']}/"
    title = f"Learn {name} Vocabulary: {n:,} Words, One Swipe at a Time | Vocab Swiper"
    top = lv[-1][0] if lv else ""
    desc = (f"Learn {n:,} {name} words with Vocab Swiper, from the most common "
            f"{lv[0][0] if lv else ''} words up to {top}. Native audio, example "
            f"sentences and spaced repetition. Free on iPhone.")
    up = "../../"
    jsonld = ('<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Vocab Swiper", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Languages", "item": SITE + "/learn/"},
            {"@type": "ListItem", "position": 3, "name": f"Learn {name}", "item": url}]},
        ensure_ascii=False) + "</script>")
    out = [HEAD.format(title=esc(title), desc=esc(desc), url=url, site=SITE, up=up,
                       store=APP_STORE, jsonld=jsonld)]
    maxc = max((c for _, c in lv), default=1)
    level_html = "".join(
        f'<div class="lvl"><span class="lname">{esc(l)}</span>'
        f'<span class="bar"><i style="width:{max(4, round(100 * c / maxc))}%"></i></span>'
        f'<span class="lcount">{c:,}</span></div>' for l, c in lv)
    d = ' dir="rtl"' if code in RTL else ""
    word_html = "".join(
        f'<li><span class="w" lang="{code}"{d}>{esc(w)}</span>'
        + (f'<span class="r">{esc(r)}</span>' if r and r.lower() != w.lower() else "")
        + f'<span class="g">{esc(g)}</span></li>' for w, r, g in words)
    first_level = lv[0][0] if lv else ""
    others = [o for o in all_langs if o["code"] != code]
    others = sorted(others, key=lambda o: -len(o["rows"]))[:10]
    other_html = "".join(f'<a href="../{o["slug"]}/">{esc(o["name"])}</a>' for o in others)
    out.append(f"""<main class="wrap">
<header class="hero">
  <div class="eyebrow"><a href="../">Languages</a> / {esc(name)}</div>
  <h1>Learn {esc(name)} vocabulary, one swipe at a time.</h1>
  <p class="endonym" lang="{code}"{d}>{esc(lang['endonym'])}</p>
  <p class="lede">{n:,} real {esc(name)} words, starting from the most common and building up level by level. Every word comes with native audio and example sentences, and spaced repetition brings it back right before you'd forget it.</p>
  {BADGE.format(store=APP_STORE)}
</header>

<section class="card">
  <h2>{n:,} words, graded by {esc(scale)} level</h2>
  <p class="sub">How the {esc(name)} deck is spread across levels. You start at your own level and the app moves you up as words stick.</p>
  <div class="levels">{level_html}</div>
</section>

<section class="card">
  <h2>Start with these {len(words)} {esc(name)} words</h2>
  <p class="sub">Some of the most common {esc(first_level)} words in the deck. In the app, each one is a card you recall, hear and practise.</p>
  <ul class="words">{word_html}</ul>
</section>

{METHOD.format(name=esc(name))}

<section class="cta">
  <h2>Your first {esc(name)} words are one swipe away.</h2>
  {BADGE.format(store=APP_STORE)}
  <p class="free">Free to download. Works offline once your deck is on your phone.</p>
</section>

<nav class="more" aria-label="Other languages">
  <h2>Other languages</h2>
  <div class="links">{other_html}<a class="all" href="../">All {len(all_langs)} languages →</a></div>
</nav>
</main>
""")
    out.append(FOOT.format(up=up))
    return "".join(out)


def hub_page(all_langs):
    url = f"{SITE}/learn/"
    title = f"Learn Vocabulary in {len(all_langs)} Languages | Vocab Swiper"
    desc = (f"Pick a language and learn its vocabulary one swipe at a time. "
            f"{len(all_langs)} languages, from Spanish and Japanese to Swahili and Welsh, "
            f"each with a real graded deck.")
    up = "../"
    rtl = ' dir="rtl"'
    cards = "".join(
        f'<a class="lang" href="{l["slug"]}/"><span class="n">{esc(l["name"])}</span>'
        f'<span class="e" lang="{l["code"]}"{rtl if l["code"] in RTL else ""}>{esc(l["endonym"])}</span>'
        f'<span class="c">{len(l["rows"]):,} words</span></a>' for l in all_langs)
    out = [HEAD.format(title=esc(title), desc=esc(desc), url=url, site=SITE, up=up,
                       store=APP_STORE, jsonld="")]
    out.append(f"""<main class="wrap">
<header class="hero">
  <div class="eyebrow">Languages</div>
  <h1>Learn vocabulary in {len(all_langs)} languages.</h1>
  <p class="lede">Every language has its own graded deck of real words, with native audio and spaced repetition. Pick one to see its words and levels.</p>
</header>
<div class="grid">{cards}</div>
<section class="cta">
  <h2>Every language, one app.</h2>
  {BADGE.format(store=APP_STORE)}
</section>
</main>
""")
    out.append(FOOT.format(up=up))
    return "".join(out)


def sitemap(all_langs):
    today = date.today().isoformat()
    urls = ["", "learn/", "support/", "privacy/"] + [f"learn/{l['slug']}/" for l in all_langs]
    body = "".join(f"  <url><loc>{SITE}/{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")


def main():
    ap = argparse.ArgumentParser()
    ios = os.path.join(os.path.dirname(ROOT), "vocabswiper_ios")
    ap.add_argument("--decks", default=os.path.join(ios, "decks"))
    ap.add_argument("--languages", default=os.path.join(ios, "assets", "languages.json"))
    a = ap.parse_args()
    langs = load(a.decks, a.languages)
    os.makedirs(os.path.join(ROOT, "learn"), exist_ok=True)
    for l in langs:
        d = os.path.join(ROOT, "learn", l["slug"])
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(lang_page(l, langs))
    open(os.path.join(ROOT, "learn", "index.html"), "w", encoding="utf-8").write(hub_page(langs))
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(sitemap(langs))
    print(f"{len(langs)} language pages, hub and sitemap written")


if __name__ == "__main__":
    main()
