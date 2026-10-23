#!/usr/bin/env python3
"""Generate the /learn/<language>/ pages, the /learn/ hub and sitemap.xml.

Every number and word on these pages comes from the app's own decks, so a
page can never promise a deck the app does not have. Re-run after a deck
changes:

    python3 _tools/learn_pages.py                       # decks next door
    python3 _tools/learn_pages.py --decks path/to/decks

Reads ../vocabswiper_ios/decks/words_<code>_en.json,
../vocabswiper_ios/assets/languages.json and the core words in
../vocabswiper_ios/assets/words.json by default.
"""
import argparse
import html
import json
import os
import re
import unicodedata
from collections import Counter
from datetime import date

SITE = "https://vocabswiper.com"
APP_STORE = "https://apps.apple.com/app/id6782795150"
PLAY_STORE = "https://play.google.com/store/apps/details?id=com.stratelabs.vocab"
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
# Languages whose levels each get a full word-list page (/learn/<lang>/<level>/).
# Japanese is the pilot; add a code here once its levels have a LEVEL_INFO.
LEVEL_PAGES = {"ja"}

# What each level means, in our own words (paraphrasing the exam's published
# can-do descriptions), and where a list's words came from.
LEVEL_INFO = {
    "jlpt:N5": "N5 is the first JLPT level: reading simple phrases written in hiragana, katakana and basic kanji, and following slow, everyday conversation about familiar things.",
    "jlpt:N4": "N4 is the second step of basic Japanese: everyday topics in simple vocabulary and kanji, and conversations about daily life when spoken slowly.",
    "jlpt:N3": "N3 is the bridge to everyday Japanese: getting the gist of newspaper headlines and simple articles, and following everyday conversation at close to natural speed.",
    "jlpt:N2": "N2 is everyday Japanese and a step beyond: newspaper and magazine articles on general topics, and news and conversation at natural speed.",
    "jlpt:N1": "N1 is the top JLPT level: complex and abstract writing, editorials and lectures, and natural-speed conversation, news and debate across a wide range of topics.",
}
SOURCES = {
    "ja": ('Level lists based on Jonathan Waller\'s JLPT resources (<a href="https://www.tanos.co.uk/jlpt/" rel="noopener">tanos.co.uk</a>, CC BY). '
           'Readings and meanings checked against <a href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project" rel="noopener">JMdict</a> '
           '(Electronic Dictionary Research and Development Group, CC BY-SA 4.0). '
           'The JLPT has not published official vocabulary lists since 2010, so no list, this one included, is official.'),
}
SPEECH_LANG = {"ja": "ja-JP"}

CEFR = ("CEFR", [f"cefr:{l}" for l in ("A1", "A2", "B1", "B2", "C1", "C2")], lambda t: t.split(":")[1])


def esc(s):
    return html.escape(str(s), quote=True)


def slug(name):
    # "Māori" -> "maori", not "m-ori": strip accents before dropping non-letters.
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def load(decks, langs_path, canonical_path):
    langs = json.load(open(langs_path, encoding="utf-8"))
    # The 220 core words every language ships with (hello, eat, go…). They
    # live outside the per-language decks, so a level list built from the deck
    # alone would leave out 食べる and 行く.
    canonical = json.load(open(canonical_path, encoding="utf-8"))
    out = []
    for l in langs:
        code = l["code"]
        path = os.path.join(decks, f"words_{code}_en.json")
        if code == "en" or not os.path.exists(path):
            continue
        rows = json.load(open(path, encoding="utf-8"))
        name = NAME_OVERRIDE.get(code, l["exonym"])
        core = [r for r in canonical if r["translations"].get(code, {}).get("word")]
        out.append({"code": code, "name": name, "endonym": l["endonym"],
                    "slug": slug(name), "rows": rows, "core": core})
    return sorted(out, key=lambda x: x["name"])


def clean(rows):
    """Rows worth listing: alternate spellings and bound forms are cards in the
    app but noise in a word list."""
    return [r for r in rows if not any(t.startswith("quality:") for t in r.get("tags", []))]


def listed(lang):
    """Every word a level list shows: the core words plus the deck, cleaned,
    one row per written word. A word in both keeps the deck's row (its meaning
    is written as a gloss); a word the core block carries twice (見る as "see"
    and "look") keeps one row with both meanings."""
    code = lang["code"]
    deck = clean(lang["rows"])
    in_deck = {r["translations"][code]["word"] for r in deck}
    merged = {}
    for r in lang.get("core", []):
        w = r["translations"][code]["word"]
        if w in in_deck:
            continue
        if w in merged:
            m = merged[w]
            g = r["translations"]["en"]["word"]
            if g not in m["translations"]["en"]["word"].split(", "):
                m["translations"]["en"]["word"] += ", " + g
            continue
        merged[w] = json.loads(json.dumps(r))
    return list(merged.values()) + deck


def level_slug(tag):
    """'jlpt:N5' -> 'jlpt-n5', 'hsk:1' -> 'hsk-1'."""
    return tag.replace(":", "-").lower()


def levels(lang):
    scale_name, tags, label = SCALES.get(lang["code"], CEFR)
    # Where the levels have their own pages, count what those pages list.
    rows = listed(lang) if lang["code"] in LEVEL_PAGES else lang["rows"]
    counts = Counter(t for r in rows for t in r.get("tags", []) if t in tags)
    present = [(label(t), counts[t]) for t in tags if counts[t]]
    graded = sum(c for _, c in present)
    rest = len(rows) - graded
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
<link rel="stylesheet" href="{up}learn/learn.css?v=9">
{jsonld}
</head>
<body>
<div class="navbar"><div class="wrap"><nav>
  <a class="brand" href="{up}"><img class="brand-img" src="{up}icon.png?v=3" alt="">Vocab Swiper</a>
  <a class="cta-mini" href="{store}" target="_blank" rel="noopener">Get the app</a>
</nav></div></div>
"""

FOOT = """<footer>{langs}<div class="wrap foot-row">
  <span class="foot-brand"><img src="{up}icon.png?v=3" alt="">Vocab Swiper · © 2026 <a href="https://stratelabs.net" style="color:inherit">Strate Labs Limited</a></span>
  <span><a href="{up}learn/">Languages</a> &nbsp;·&nbsp; <a href="{up}privacy/">Privacy</a> &nbsp;·&nbsp; <a href="{up}support/">Support</a></span>
</div></footer>
</body>
</html>
"""

BADGE = """<span class="badges"><a class="badge" href="{store}" target="_blank" rel="noopener" aria-label="Download on the App Store">
  <svg viewBox="0 0 384 512"><path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z"/></svg>
  <span class="txt"><small>DOWNLOAD ON THE</small><span>App Store</span></span>
</a>
<a class="badge" href="{play}" target="_blank" rel="noopener" aria-label="Get it on Google Play">
  <svg viewBox="0 0 512 512"><path fill="#00D7FE" d="M64 24 L64 488 L300 256 Z"/><path fill="#00F076" d="M64 24 L300 256 L376 180 Z"/><path fill="#FF3A44" d="M64 488 L376 332 L300 256 Z"/><path fill="#FFD400" d="M376 180 L466 230 Q494 256 466 282 L376 332 L300 256 Z"/></svg>
  <span class="txt"><small>GET IT ON</small><span>Google Play</span></span>
</a></span>"""



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
    linked = code in LEVEL_PAGES
    tag_for = {SCALES.get(code, CEFR)[2](t): t for t in SCALES.get(code, CEFR)[1]}

    def lvl_row(l, c):
        inner = (f'<span class="lname">{esc(l)}</span>'
                 f'<span class="bar"><i style="width:{max(4, round(100 * c / maxc))}%"></i></span>'
                 f'<span class="lcount">{c:,}</span>')
        if linked and l in tag_for:
            return f'<a class="lvl" href="{level_slug(tag_for[l])}/">{inner}<span class="go">→</span></a>'
        return f'<div class="lvl">{inner}</div>'
    level_html = "".join(lvl_row(l, c) for l, c in lv)
    graded_n = sum(c for _, c in lv) if linked else n
    test_link = (f'<a class="testlink" href="{scale.lower()}-test/"><b>Not sure where you are?</b> '
                 f'Take the free 3-minute {esc(scale)} vocabulary test →</a>' if linked else "")
    level_sub = (f"Tap a level for its full word list, with readings and meanings. In the app you start at your own level and move up as words stick."
                 if linked else
                 f"How the {esc(name)} deck is spread across levels. You start at your own level and the app moves you up as words stick.")
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
  <h1>Learn {esc(name)} vocabulary one swipe at a time</h1>
  <p class="endonym" lang="{code}"{d}>{esc(lang['endonym'])}</p>
  <p class="lede">{n:,} real {esc(name)} words, starting from the most common and building up level by level. Every word comes with native audio and example sentences, and spaced repetition brings it back right before you'd forget it.</p>
  {BADGE.format(store=APP_STORE, play=PLAY_STORE)}
</header>

<section class="card">
  <h2>{graded_n:,} words, graded by {esc(scale)} level</h2>
  <p class="sub">{level_sub}</p>
  {test_link}
  <div class="levels">{level_html}</div>
</section>

<section class="card">
  <h2>Start with these {len(words)} {esc(name)} words</h2>
  <p class="sub">Some of the most common {esc(first_level)} words in the deck. In the app, each one is a card you recall, hear and practise.</p>
  <ul class="words">{word_html}</ul>
</section>


<section class="cta">
  <h2>Your first {esc(name)} words are one swipe away.</h2>
  {BADGE.format(store=APP_STORE, play=PLAY_STORE)}
  <p class="free">Free to download. Works offline once your deck is on your phone.</p>
</section>

<nav class="more" aria-label="Other languages">
  <h2>Other languages</h2>
  <div class="links">{other_html}<a class="all" href="../">All {len(all_langs)} languages →</a></div>
</nav>
</main>
""")
    out.append(FOOT.format(up=up, langs=foot_langs(ALL_LANGS, up)))
    return "".join(out)


LEVEL_JS = """<script>
(function(){
  var list=document.getElementById('vlist'), q=document.getElementById('q'), shown=document.getElementById('shown');
  var rows=[].slice.call(list.children);
  // Searched by everything a row shows: word, reading, romaji, meaning.
  var text=rows.map(function(li){return [].slice.call(li.querySelectorAll('.w,.k,.ro,.g')).map(function(e){return e.textContent;}).join(' ').toLowerCase();});
  function filter(){
    var v=q.value.trim().toLowerCase(), n=0;
    rows.forEach(function(li,i){var hit=!v||text[i].indexOf(v)>=0; li.hidden=!hit; if(hit)n++;});
    shown.textContent=n.toLocaleString();
  }
  q.addEventListener('input',filter);
  [['hide-g','tg'],['hide-r','tr']].forEach(function(p){
    var b=document.getElementById(p[1]);
    b.addEventListener('click',function(){
      var on=document.body.classList.toggle(p[0]); b.setAttribute('aria-pressed',on);
      if(on) rows.forEach(function(li){li.classList.remove('show');});
    });
  });
  // Quiz mode: tap a row to reveal what is hidden.
  list.addEventListener('click',function(e){
    var say=e.target.closest('.say');
    if(say){speak(say.getAttribute('data-say'));return;}
    var li=e.target.closest('li'); if(li) li.classList.toggle('show');
  });
  var lang=list.getAttribute('data-speech');
  function speak(t){
    if(!('speechSynthesis' in window))return;
    speechSynthesis.cancel(); var u=new SpeechSynthesisUtterance(t); u.lang=lang; u.rate=.85;
    var v=speechSynthesis.getVoices().filter(function(x){return x.lang&&x.lang.replace('_','-').indexOf(lang.split('-')[0])===0;})[0];
    if(v)u.voice=v; speechSynthesis.speak(u);
  }
  if(!('speechSynthesis' in window)) document.body.classList.add('no-say');
})();
</script>"""


def level_pages(lang):
    """One page per exam level: the whole list, most common word first, with a
    search box, a quiz mode and the browser's own voice reading each word."""
    code, name = lang["code"], lang["name"]
    scale, tags, label = SCALES.get(code, CEFR)
    rows = listed(lang)
    by_tag = {t: [r for r in rows if t in r.get("tags", [])] for t in tags}
    tags = [t for t in tags if by_tag[t]]
    pages, running = [], 0
    for i, tag in enumerate(tags):
        lv_rows = sorted(by_tag[tag], key=lambda r: -(r["translations"][code].get("zipf") or 0))
        n = len(lv_rows)
        running += n
        lname = label(tag)
        full = f"{scale} {lname}" if not lname.startswith(scale) else lname
        lslug = level_slug(tag)
        url = f"{SITE}/learn/{lang['slug']}/{lslug}/"
        title = f"{full} Vocabulary List: All {n:,} Words with Readings & Meanings | Vocab Swiper"
        desc = (f"The full {full} vocabulary list: {n:,} {name} words with readings, romaji and English "
                f"meanings, most common first. Quiz yourself, hear each word, and study them free in Vocab Swiper.")
        up = "../../../"
        jsonld = ('<script type="application/ld+json">' + json.dumps([
            {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Vocab Swiper", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": "Languages", "item": SITE + "/learn/"},
                {"@type": "ListItem", "position": 3, "name": f"Learn {name}", "item": f"{SITE}/learn/{lang['slug']}/"},
                {"@type": "ListItem", "position": 4, "name": f"{full} vocabulary", "item": url}]},
            {"@context": "https://schema.org", "@type": "LearningResource", "name": f"{full} vocabulary list",
             "description": desc, "url": url, "inLanguage": code, "educationalLevel": full,
             "learningResourceType": "Vocabulary list", "isAccessibleForFree": True,
             "provider": {"@type": "Organization", "name": "Strate Labs Limited", "url": "https://stratelabs.net"}}],
            ensure_ascii=False) + "</script>")

        pills = "".join(
            (f'<span class="pill on" aria-current="page">{esc(label(t))}</span>' if t == tag else
             f'<a class="pill" href="../{level_slug(t)}/">{esc(label(t))}</a>') for t in tags)
        items = []
        for k, r in enumerate(lv_rows, 1):
            t = r["translations"][code]
            w, kana, ro = t.get("word", ""), t.get("kana", ""), t.get("romanization", "")
            g = r["translations"]["en"].get("word", "") or r.get("concept", "")
            reading = kana if kana and kana != w else ""
            items.append(
                f'<li><span class="num">{k}</span>'
                f'<span class="w" lang="{code}">{esc(w)}</span>'
                f'<span class="rd"><span class="k" lang="{code}">{esc(reading)}</span>'
                f'<span class="ro">{esc(ro)}</span></span>'
                f'<span class="g">{esc(g)}</span>'
                f'<button class="say" type="button" data-say="{esc(kana or w)}" aria-label="Hear {esc(w)}"></button></li>')
        prev_n = running - n
        cum = (f"Together with the {prev_n:,} words below it, that makes {running:,} words by the end of {full}."
               if prev_n else f"It is the first level, so this is where everyone starts.")
        nxt = tags[i + 1] if i + 1 < len(tags) else None
        next_link = (f'<a class="next" href="../{level_slug(nxt)}/">Next: {esc(label(nxt))} vocabulary →</a>' if nxt else "")
        about = LEVEL_INFO.get(tag, "")
        source = SOURCES.get(code, "")
        out = [HEAD.format(title=esc(title), desc=esc(desc), url=url, site=SITE, up=up,
                           store=APP_STORE, jsonld=jsonld)]
        out.append(f"""<main class="wrap">
<header class="hero">
  <div class="eyebrow"><a href="../../">Languages</a> / <a href="../">{esc(name)}</a> / {esc(full)}</div>
  <h1>{esc(full)} vocabulary list</h1>
  <p class="lede">All {n:,} {esc(full)} words, with readings, romaji and meanings. The most common words come first, so the top of the list is where to start.</p>
  <nav class="pills" aria-label="{esc(scale)} levels">{pills}</nav>
  <p class="testline"><a href="../{scale.lower()}-test/">Not sure which level you are? Take the free {esc(scale)} test →</a></p>
</header>

<section class="card">
  <h2>What {esc(full)} covers</h2>
  <p class="prose">{esc(about)} This list has {n:,} words. {cum}</p>
  <p class="prose">Use the search to find a word, or switch on <b>Quiz me</b> to hide the meanings and test yourself: tap a word to check it. The speaker button reads each word aloud.</p>
</section>

<section class="card list">
  <div class="tools">
    <input id="q" type="search" placeholder="Search {n:,} words" aria-label="Search the list" autocomplete="off">
    <button id="tg" class="tog" type="button" aria-pressed="false">Quiz me</button>
    <button id="tr" class="tog" type="button" aria-pressed="false">Hide readings</button>
    <span class="count"><b id="shown">{n:,}</b> words</span>
  </div>
  <ol id="vlist" class="vlist" data-speech="{SPEECH_LANG.get(code, code)}">{"".join(items)}</ol>
</section>

<section class="cta">
  <h2>Learn every {esc(full)} word, not just read them.</h2>
  <p class="free">Vocab Swiper's {esc(name)} deck has every word on this page. You recall each one before you see its meaning, hear it and see it in a sentence, and spaced repetition brings it back right before you'd forget it.</p>
  {BADGE.format(store=APP_STORE, play=PLAY_STORE)}
</section>

<section class="card faq">
  <h2>Questions about {esc(full)} vocabulary</h2>
  <details><summary>How many words do you need for {esc(full)}?</summary>
    <p>There is no official number. This list has {n:,} words at {esc(full)}, and {running:,} counting every level up to it. Study lists differ in size because each one is compiled independently.</p></details>
  <details><summary>Is this the official {esc(full)} list?</summary>
    <p>No. The JLPT has not published vocabulary lists since 2010. This list builds on the most widely used community lists, with every reading checked against a dictionary and duplicate spellings removed.</p></details>
  <details><summary>What is the fastest way to learn these words?</summary>
    <p>Test yourself rather than re-reading. Trying to recall a word before you see its meaning, then reviewing it again just before you would forget it (spaced repetition), takes far fewer reviews than reading a list over and over.</p></details>
</section>

<p class="credit">{source}</p>
<nav class="more" aria-label="{esc(scale)} levels">{next_link}<a class="all" href="../">All {esc(name)} levels →</a></nav>
</main>
{LEVEL_JS}
""")
        out.append(FOOT.format(up=up, langs=foot_langs(ALL_LANGS, up)))
        pages.append((lslug, "".join(out)))
    return pages


TEST_PER_LEVEL = 6
TEST_POOL = 60


def short_gloss(g):
    """An answer option: 'to avoid; to ward off' -> 'to avoid'."""
    g = re.sub(r"\s*\([^)]*\)", "", g).strip()
    g = g.split(";")[0].strip()
    if len(g) > 28:
        g = g.split(",")[0].strip()
    return g


def test_pool(lang):
    """Per level, TEST_POOL words spread evenly from most to least common.

    Katakana loanwords are left out: an English speaker can guess ヨーロッパ
    without knowing any Japanese, and a guess is not a known word."""
    code = lang["code"]
    scale, tags, label = SCALES.get(code, CEFR)
    rows = listed(lang)
    katakana = re.compile(r"^[\u30A0-\u30FF]+$")
    pool = {}
    for tag in tags:
        cand = []
        seen = set()
        for r in sorted((r for r in rows if tag in r.get("tags", [])),
                        key=lambda r: -(r["translations"][code].get("zipf") or 0)):
            t = r["translations"][code]
            w, kana = t.get("word", ""), t.get("kana", "")
            g = short_gloss(r["translations"]["en"].get("word", "") or r.get("concept", ""))
            if not w or not g or len(g) > 28 or katakana.match(w) or g.lower() in seen:
                continue
            seen.add(g.lower())
            cand.append([w, kana if kana != w else "", g])
        if not cand:
            continue
        step = max(1, len(cand) / TEST_POOL)
        pool[label(tag)] = [cand[int(i * step)] for i in range(min(TEST_POOL, len(cand)))]
    return pool


TEST_JS = """<script>
(function(){
  var D=JSON.parse(document.getElementById('pool').textContent), PER=%(per)d;
  var levels=D.levels, $=function(id){return document.getElementById(id);};
  var qs=[], i=0, score={}, stopped=false;
  function shuffle(a){for(var j=a.length-1;j>0;j--){var k=Math.floor(Math.random()*(j+1)),t=a[j];a[j]=a[k];a[k]=t;}return a;}
  function build(){
    qs=[]; score={};
    levels.forEach(function(l){
      score[l.name]={right:0,wrong:0,skip:0,asked:0};
      shuffle(l.words.slice()).slice(0,PER).forEach(function(w){
        var others=shuffle(l.words.filter(function(o){return o[2]!==w[2];})).slice(0,3).map(function(o){return o[2];});
        qs.push({level:l.name,word:w[0],kana:w[1],answer:w[2],options:shuffle(others.concat([w[2]]))});
      });
    });
  }
  function show(id){['intro','quiz','result'].forEach(function(s){$(s).hidden=s!==id;});window.scrollTo(0,$('test').offsetTop-80);}
  function ask(){
    var q=qs[i];
    $('qlevel').textContent=q.level; $('qn').textContent=(i+1)+' / '+qs.length;
    $('bar').style.width=(100*i/qs.length)+'%%';
    $('qword').textContent=q.word; $('qkana').textContent=q.kana;
    var box=$('opts'); box.innerHTML='';
    q.options.forEach(function(o){var b=document.createElement('button');b.type='button';b.className='opt';b.textContent=o;b.onclick=function(){answer(o,b);};box.appendChild(b);});
  }
  function answer(o,btn){
    var q=qs[i], s=score[q.level], buttons=[].slice.call(document.querySelectorAll('#opts .opt'));
    buttons.forEach(function(b){b.disabled=true; if(b.textContent===q.answer)b.classList.add('right');});
    s.asked++;
    if(o===null){s.skip++;}else if(o===q.answer){s.right++;}else{s.wrong++;btn.classList.add('wrong');}
    $('skip').disabled=true;
    setTimeout(next,o===q.answer?450:1100);
  }
  function corrected(s){return s.asked?Math.max(0,(s.right-s.wrong/3)/s.asked):0;}
  function next(){
    $('skip').disabled=false;
    var q=qs[i]; i++;
    // A level that is clearly out of reach ends the test: nobody needs twelve
    // more N1 questions to learn that N2 was already a stretch.
    if(i===qs.length||qs[i].level!==q.level){
      if(corrected(score[q.level])<.25&&i<qs.length){stopped=true;return finish();}
    }
    if(i>=qs.length)return finish();
    ask();
  }
  function finish(){
    var est=null, known=0, rows='';
    levels.forEach(function(l,k){
      var s=score[l.name], c=corrected(s);
      known+=l.count*c;
      var pass=s.asked&&c>=.6;
      if(pass&&(k===0||est===levels[k-1].name))est=l.name;
      var pct=s.asked?Math.round(100*s.right/s.asked):0;
      rows+='<div class="lvl"><span class="lname">'+l.name+'</span><span class="bar"><i style="width:'+Math.max(3,pct)+'%%"></i></span><span class="lcount">'+(s.asked?s.right+'/'+s.asked:'–')+'</span></div>';
    });
    known=Math.round(known/50)*50;
    var idx=est?levels.map(function(l){return l.name;}).indexOf(est):-1;
    var nxt=levels[idx+1];
    $('rlevel').textContent=est?(D.scale+' '+est):'Just starting';
    $('rline').textContent=est?
      ('Your vocabulary looks ready for '+D.scale+' '+est+(nxt?'. '+nxt.name+' is your next step.':', the top level.')):
      ('Start with '+D.scale+' '+levels[0].name+': the most common words in the language.');
    $('rknown').textContent=known?('About '+known.toLocaleString()+' words'):'';
    $('rbars').innerHTML=rows;
    var target=nxt||levels[idx]||levels[0];
    if(!est)target=levels[0];
    $('rlist').href='../'+target.slug+'/'; $('rlist').textContent='Study the '+target.name+' words →';
    window.__result=$('rlevel').textContent;
    show('result');
  }
  $('start').onclick=function(){build();i=0;stopped=false;show('quiz');ask();};
  $('skip').onclick=function(){answer(null,null);};
  $('again').onclick=function(){build();i=0;stopped=false;show('quiz');ask();};
  $('share').onclick=function(){
    var text='I tested at '+window.__result+' on the free '+D.scale+' vocabulary test:', url=location.href.split('#')[0];
    if(navigator.share){navigator.share({title:document.title,text:text,url:url}).catch(function(){});}
    else if(navigator.clipboard){navigator.clipboard.writeText(text+' '+url);$('share').textContent='Link copied';}
  };
})();
</script>"""


def test_page(lang):
    """A free level test: TEST_PER_LEVEL words a level, easiest level first,
    pick the meaning. It estimates a level and a vocabulary size, and points
    at the list to study next."""
    code, name = lang["code"], lang["name"]
    scale, tags, label = SCALES.get(code, CEFR)
    pool = test_pool(lang)
    rows = listed(lang)
    lv = []
    for t in tags:
        if label(t) in pool:
            lv.append({"name": label(t), "slug": level_slug(t),
                       "count": sum(1 for r in rows if t in r.get("tags", [])),
                       "words": pool[label(t)]})
    nq = TEST_PER_LEVEL * len(lv)
    url = f"{SITE}/learn/{lang['slug']}/{scale.lower()}-test/"
    title = f"Free {scale} Vocabulary Test: What's Your {name} Level? | Vocab Swiper"
    desc = (f"Find your {scale} level in about three minutes. {nq} quick questions from N5 to N1 "
            f"estimate your {name} vocabulary level and how many words you know. Free, no sign-up.") if code == "ja" else \
           (f"Find your {name} {scale} level in about three minutes. Free, no sign-up.")
    up = "../../../"
    jsonld = ('<script type="application/ld+json">' + json.dumps([
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Vocab Swiper", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Languages", "item": SITE + "/learn/"},
            {"@type": "ListItem", "position": 3, "name": f"Learn {name}", "item": f"{SITE}/learn/{lang['slug']}/"},
            {"@type": "ListItem", "position": 4, "name": f"{scale} vocabulary test", "item": url}]},
        {"@context": "https://schema.org", "@type": "Quiz", "name": f"{scale} vocabulary level test",
         "description": desc, "url": url, "inLanguage": "en", "about": f"{name} vocabulary",
         "educationalLevel": f"{scale} {lv[0]['name']}–{lv[-1]['name']}", "isAccessibleForFree": True,
         "provider": {"@type": "Organization", "name": "Strate Labs Limited", "url": "https://stratelabs.net"}}],
        ensure_ascii=False) + "</script>")
    data = json.dumps({"scale": scale, "levels": lv}, ensure_ascii=False, separators=(",", ":"))
    level_links = "".join(f'<a class="pill" href="../{l["slug"]}/">{esc(l["name"])}</a>' for l in lv)
    out = [HEAD.format(title=esc(title), desc=esc(desc), url=url, site=SITE, up=up,
                       store=APP_STORE, jsonld=jsonld)]
    out.append(f"""<main class="wrap">
<header class="hero">
  <div class="eyebrow"><a href="../../">Languages</a> / <a href="../">{esc(name)}</a> / {esc(scale)} test</div>
  <h1>What's your {esc(scale)} level?</h1>
  <p class="lede">A free vocabulary test from {esc(lv[0]['name'])} to {esc(lv[-1]['name'])}. {nq} quick questions, about three minutes, no sign-up.</p>
</header>

<section id="test" class="card test">
  <div id="intro">
    <h2>How it works</h2>
    <ul class="howto">
      <li>You see a {esc(name)} word and pick its meaning from four.</li>
      <li>It starts easy and gets harder, {TEST_PER_LEVEL} words per level.</li>
      <li>Don't guess: <b>I don't know</b> is the honest answer, and wrong guesses count against you.</li>
    </ul>
    <button id="start" class="go-btn" type="button">Start the test</button>
  </div>
  <div id="quiz" hidden>
    <div class="qhead"><span id="qlevel" class="qlevel"></span><span id="qn" class="qn"></span></div>
    <div class="progress"><i id="bar"></i></div>
    <div class="qword"><span id="qword" lang="{code}"></span><span id="qkana" class="qkana" lang="{code}"></span></div>
    <div id="opts" class="opts"></div>
    <button id="skip" class="skip" type="button">I don't know</button>
  </div>
  <div id="result" hidden>
    <p class="eyebrow">Your result</p>
    <div id="rlevel" class="rlevel"></div>
    <p id="rline" class="rline"></p>
    <p id="rknown" class="rknown"></p>
    <div id="rbars" class="levels"></div>
    <div class="ractions">
      <a id="rlist" class="go-btn" href="#"></a>
      <button id="share" class="tog" type="button">Share result</button>
      <button id="again" class="tog" type="button">Take it again</button>
    </div>
    <p class="note">This measures vocabulary only. The real {esc(scale)} also tests grammar, reading and listening, so treat it as a guide to which words to study next.</p>
  </div>
</section>

<section class="cta">
  <h2>Close the gap to your next level.</h2>
  <p class="free">Vocab Swiper's {esc(name)} deck has every {esc(scale)} word from {esc(lv[0]['name'])} to {esc(lv[-1]['name'])}. Recall each one, hear it, and let spaced repetition bring it back right before you'd forget it.</p>
  {BADGE.format(store=APP_STORE, play=PLAY_STORE)}
</section>

<nav class="more" aria-label="{esc(scale)} word lists">
  <h2>{esc(scale)} word lists</h2>
  <div class="pills">{level_links}</div>
</nav>
<p class="credit">{SOURCES.get(code, "")}</p>
</main>
<script type="application/json" id="pool">{data.replace("</", "<\\/")}</script>
{TEST_JS % {"per": TEST_PER_LEVEL}}
""")
    out.append(FOOT.format(up=up, langs=foot_langs(ALL_LANGS, up)))
    return "".join(out)


ALL_LANGS = []  # set in main(); every page's footer links them all

FOOT_LANG_CSS = (".foot-langs{display:block;padding-top:0;margin-bottom:22px;padding-bottom:20px;border-bottom:1px solid rgba(255,255,255,.06)}"
                 ".foot-langs b{display:block;font-size:11px;font-weight:800;letter-spacing:1.8px;text-transform:uppercase;"
                 "color:rgba(236,241,240,.5);margin-bottom:10px}"
                 ".foot-langs div{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px}")


def foot_langs(all_langs, up):
    """Every language page, linked from the bottom of every page, so any one
    of them is a tap away wherever a learner lands. `up` is the path from the
    page to the site root."""
    links = "".join(f'<a href="{up}learn/{l["slug"]}/">{esc(l["name"])}</a>' for l in all_langs)
    return f'<nav class="wrap foot-langs" aria-label="Languages"><b>Learn a language</b><div>{links}</div></nav>'


# Hand-written pages carry the same block between these markers.
FOOT_MARK = ("<!-- foot-langs -->", "<!-- /foot-langs -->")
HAND_PAGES = {"index.html": "", "support/index.html": "../"}


def stamp_hand_pages(all_langs):
    for rel, up in HAND_PAGES.items():
        path = os.path.join(ROOT, rel)
        page = open(path, encoding="utf-8").read()
        a, b = FOOT_MARK
        block = a + foot_langs(all_langs, up) + b
        if a in page:
            page = page[:page.index(a)] + block + page[page.index(b) + len(b):]
        else:
            page = page.replace("<footer>", "<footer>\n  " + block, 1)
        open(path, "w", encoding="utf-8").write(page)


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
  {BADGE.format(store=APP_STORE, play=PLAY_STORE)}
</section>
</main>
""")
    out.append(FOOT.format(up=up, langs=foot_langs(ALL_LANGS, up)))
    return "".join(out)


def sitemap(all_langs):
    today = date.today().isoformat()
    urls = ["", "learn/", "support/", "privacy/"] + [f"learn/{l['slug']}/" for l in all_langs]
    for l in all_langs:
        if l["code"] in LEVEL_PAGES:
            tags = SCALES.get(l["code"], CEFR)[1]
            urls += [f"learn/{l['slug']}/{level_slug(t)}/" for t in tags
                     if any(t in r.get("tags", []) for r in listed(l))]
            urls.append(f"learn/{l['slug']}/{SCALES.get(l['code'], CEFR)[0].lower()}-test/")
    body = "".join(f"  <url><loc>{SITE}/{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n")


def main():
    ap = argparse.ArgumentParser()
    ios = os.path.join(os.path.dirname(ROOT), "vocabswiper_ios")
    ap.add_argument("--decks", default=os.path.join(ios, "decks"))
    ap.add_argument("--languages", default=os.path.join(ios, "assets", "languages.json"))
    ap.add_argument("--canonical", default=os.path.join(ios, "assets", "words.json"))
    a = ap.parse_args()
    langs = load(a.decks, a.languages, a.canonical)
    global ALL_LANGS
    ALL_LANGS = langs
    os.makedirs(os.path.join(ROOT, "learn"), exist_ok=True)
    for l in langs:
        d = os.path.join(ROOT, "learn", l["slug"])
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(lang_page(l, langs))
        if l["code"] in LEVEL_PAGES:
            for lslug, page in level_pages(l):
                os.makedirs(os.path.join(d, lslug), exist_ok=True)
                open(os.path.join(d, lslug, "index.html"), "w", encoding="utf-8").write(page)
            tdir = os.path.join(d, SCALES.get(l["code"], CEFR)[0].lower() + "-test")
            os.makedirs(tdir, exist_ok=True)
            open(os.path.join(tdir, "index.html"), "w", encoding="utf-8").write(test_page(l))
    open(os.path.join(ROOT, "learn", "index.html"), "w", encoding="utf-8").write(hub_page(langs))
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(sitemap(langs))
    stamp_hand_pages(langs)
    print(f"{len(langs)} language pages, hub and sitemap written")


if __name__ == "__main__":
    main()
