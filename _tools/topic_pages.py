#!/usr/bin/env python3
"""Topic word-list pages (/learn/<language>/<topic>/), built from the Instagram carousels.

The carousels in ../../vocabswiper-content/carousels (build.py, build_batch2.py, year_q*.py)
are already checked word lists. Each topic page merges every round of a topic into one
complete list, so the site and the feed share one source. Called from learn_pages.py:

    python3 _tools/learn_pages.py      # also writes these pages and adds them to the sitemap

Topics live in TOPICS below. Each one names the carousels it merges.
"""
import html
import importlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONTENT = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "vocabswiper-content", "carousels")


def esc(s):
    return html.escape(str(s), quote=True)


def _carousel_items():
    """name -> list of items, from the batch files and the year plan."""
    sys.path.insert(0, CONTENT)
    cwd = os.getcwd()
    os.chdir(CONTENT)  # the build scripts resolve paths relative to themselves
    try:
        out = {}
        for mod in ("year_q1", "year_q2", "year_q3", "year_q4"):
            try:
                for s in importlib.import_module(mod).SPECS:
                    out[s["name"]] = s["items"]
            except ModuleNotFoundError:
                pass
    finally:
        os.chdir(cwd)
    # Batch 1 and 2 false friends were written as plain tuples (word, real, looks, right_word).
    out["false-friends-fr"] = [
        ("librairie", "a bookshop", "library", "bibliothèque"),
        ("actuellement", "currently", "actually", "en fait"),
        ("blesser", "to injure", "to bless", "bénir"),
        ("sensible", "sensitive", "sensible", "raisonnable"),
        ("location", "a rental", "location", "emplacement"),
        ("préservatif", "a condom", "preservative", "conservateur"),
    ]
    out["false-friends-es"] = [
        ("embarazada", "pregnant", "embarrassed", "avergonzada"),
        ("constipado", "stuffed up, with a cold", "constipated", "estreñido"),
        ("éxito", "success", "exit", "salida"),
        ("librería", "a bookshop", "library", "biblioteca"),
        ("actualmente", "currently", "actually", "en realidad"),
        ("carpeta", "a folder", "carpet", "alfombra"),
    ]
    out["konbini-ja"] = [
        ("いらっしゃいませ", "irasshaimase", "Welcome in!", "Staff say it. You don't need to answer."),
        ("レジ", "reji", "Checkout counter", ""),
        ("袋", "ふくろ · fukuro", "Bag", "袋いりますか？ Do you need a bag?"),
        ("温めますか？", "あたためますか · atatamemasu ka", "Shall I heat it up?", "Asked when you buy a bento or other hot food."),
        ("お箸", "おはし · ohashi", "Chopsticks", ""),
        ("ポイントカード", "pointo kādo", "Point card", "Asked every time. A head shake is fine."),
        ("大丈夫です", "だいじょうぶです · daijōbu desu", "No thanks, I'm fine", "The polite way to say no to all of the above."),
        ("現金", "げんきん · genkin", "Cash", ""),
        ("電子マネー", "でんしマネー · denshi manē", "IC card / e-money", "Suica, PASMO and friends."),
        ("レシート", "reshīto", "Receipt", ""),
    ]
    return out


# Carousel slides shorten some readings to fit. The web pages show them in full.
READING_FIX = {
    "試着してもいいですか？": "しちゃくしてもいいですか · shichaku shite mo ii desu ka?",
    "タクシー乗り場": "タクシーのりば · takushī noriba",
    "〜までお願いします": "〜までおねがいします · … made onegaishimasu",
    "ここで止めてください": "ここでとめてください · koko de tomete kudasai",
    "カード使えますか？": "カードつかえますか · kādo tsukaemasu ka?",
    "お会計お願いします": "おかいけいおねがいします · okaikei onegaishimasu",
}


def _right_html(looks, right):
    """Year-plan items already carry their own hint (with <b> tags); batch items just name the word."""
    if "<" in right or right.endswith("."):
        return right
    return f"For “{esc(looks)}”, say <b>{esc(right)}</b>."


FF_FAQ_WHAT = ("A false friend is a word that looks or sounds like a word in another language but means something "
               "different. Teachers also call them false cognates. The danger is that they feel safe: you don't "
               "think to check a word you already “know”.")
FF_FAQ_AVOID = ("Learn words in sentences instead of guessing from how they look. When a new word looks like English, "
                "check it once. Most of the time it really is the same, which is exactly why the exceptions catch people out.")

TOPICS = [
    dict(lang="spanish", code="es", speech="es-ES", slug="false-friends", name="Spanish",
         carousels=["false-friends-es", "false-friends-es-2", "false-friends-es-3"],
         title="Spanish False Friends: {n} Words That Don't Mean What You Think",
         desc="{n} Spanish false friends that look like English but mean something else, from embarazada to éxito. What each one means, and the word to use instead.",
         intro="Spanish and English share thousands of words from Latin, and most of them mean what they look like. "
               "These {n} are the exceptions: words that look like English but mean something else. "
               "A few of them, like <i>embarazada</i>, have caused some very confusing conversations.",
         worst=("Which Spanish false friend causes the most trouble?",
                "<i>Embarazada</i>. It means pregnant, not embarrassed. “Estoy muy embarazada” announces a baby. "
                "For embarrassed, say <i>avergonzado</i> (or <i>avergonzada</i>), or “me da vergüenza”.")),
    dict(lang="french", code="fr", speech="fr-FR", slug="false-friends", name="French",
         carousels=["false-friends-fr", "false-friends-fr-2", "false-friends-fr-3"],
         title="French False Friends: {n} Words That Don't Mean What You Think",
         desc="{n} French false friends that look like English but mean something else, from librairie to préservatif. What each one means, and the word to use instead.",
         intro="After 1066, English borrowed thousands of words from French, so a lot of French looks familiar. "
               "Over nine centuries many of those words drifted apart. These {n} look like English but mean something else.",
         worst=("Which French false friend causes the most trouble?",
                "<i>Préservatif</i> is the famous one: it means a condom, not a preservative. Ask for food “sans préservatifs” "
                "and you'll get a funny look. For preservatives, say <i>conservateurs</i>.")),
    dict(lang="german", code="de", speech="de-DE", slug="false-friends", name="German",
         carousels=["false-friends-de", "false-friends-de-2", "false-friends-de-3"],
         title="German False Friends: {n} Words That Don't Mean What You Think",
         desc="{n} German false friends that look like English but mean something else, from Gift (poison) to bekommen. What each one means, and the word to use instead.",
         intro="German and English grew from the same roots, so plenty of words still match: <i>Hand</i>, <i>Haus</i>, <i>Finger</i>. "
               "But some drifted. These {n} look like English and mean something else, and two of them come up in almost every first conversation.",
         worst=("Which German false friend causes the most trouble?",
                "<i>Bekommen</i>. It means to get, not to become, so “Ich bekomme ein Steak” in a restaurant is perfectly normal. "
                "<i>Gift</i> (poison) is the funniest one, but <i>bekommen</i> is the one you'll actually trip over.")),
    dict(lang="italian", code="it", speech="it-IT", slug="false-friends", name="Italian",
         carousels=["false-friends-it", "false-friends-it-2"],
         title="Italian False Friends: {n} Words That Don't Mean What You Think",
         desc="{n} Italian false friends that look like English but mean something else, from camera to confetti. What each one means, and the word to use instead.",
         intro="Italian comes from Latin, like a big share of English vocabulary, so many words look shared. "
               "These {n} look like English but mean something else, starting with the one every traveller meets at the hotel desk.",
         worst=("Which Italian false friend causes the most trouble?",
                "<i>Camera</i>. It means a room, so a hotel “camera doppia” is a double room. A camera is a "
                "<i>macchina fotografica</i>. And <i>parenti</i> are your relatives, not your parents (<i>genitori</i>).")),
    dict(lang="portuguese", code="pt", speech="pt-BR", slug="false-friends", name="Portuguese",
         carousels=["false-friends-pt", "false-friends-pt-2"],
         title="Portuguese False Friends: {n} Words That Don't Mean What You Think",
         desc="{n} Portuguese false friends that look like English but mean something else, from puxar to novela. What each one means, and the word to use instead.",
         intro="Portuguese shares a lot of Latin vocabulary with English, so plenty of words look familiar. "
               "These {n} look like English but mean something else. They're the same in Brazil and Portugal.",
         worst=("Which Portuguese false friend causes the most trouble?",
                "<i>Puxar</i>. It looks like push but means pull, and it's written on doors everywhere. "
                "Push is <i>empurrar</i>. <i>Pretender</i> (to intend, not to pretend) comes a close second.")),
]


# Phrase lists: sections of (word, reading, meaning, note), merged from several carousels.
KONBINI_EXTRA = [
    ("袋はご利用ですか？", "ふくろはごりようですか · fukuro wa go-riyō desu ka?", "Would you like a bag?", "The politer way staff ask. Bags cost a few yen."),
    ("お箸おつけしますか？", "おはしおつけしますか · ohashi otsuke shimasu ka?", "Shall I put in chopsticks?", ""),
    ("ポイントカードはお持ちですか？", "ポイントカードはおもちですか · pointo kādo wa o-mochi desu ka?", "Do you have a point card?", "大丈夫です or a small head shake is fine."),
    ("お支払いは？", "おしはらいは · o-shiharai wa?", "How will you pay?", ""),
    ("カードでお願いします", "カードでおねがいします · kādo de onegaishimasu", "By card, please", "Swap カード for 現金 (cash) or 電子マネー."),
    ("レシートは大丈夫です", "レシートはだいじょうぶです · reshīto wa daijōbu desu", "I don't need the receipt", ""),
    ("おにぎり", "onigiri", "Rice ball", "Pull tab 1, then corners 2 and 3, and the seaweed stays crisp."),
    ("ATM", "ē-tī-emu", "Cash machine", "Konbini ATMs, especially 7-Eleven's, usually take foreign cards."),
]

PHRASE_TOPICS = [
    dict(lang="japanese", code="ja", speech="ja-JP", slug="travel-phrases", name="Japanese", label="Japanese travel phrases",
         crumb="Travel phrases",
         title="Japanese Phrases for Travel: {n} Phrases with Pronunciation",
         h2="{n} Japanese travel phrases, with readings",
         desc="{n} Japanese phrases for your trip, with readings and pronunciation: trains, the airport, hotels, taxis, shopping, konbini and izakaya. Hear each one.",
         h1="Japanese phrases for travel",
         intro="Everything you'll need between landing and leaving, grouped by where you'll need it. "
               "Every phrase has its reading and romaji, and the speaker reads it aloud. Save the page for your trip.",
         sections=[("At the airport", "airport-ja"), ("On the train", "train-words-ja"), ("At the hotel", "hotel-words-ja"),
                   ("In a taxi", "taxi-ja"), ("At the konbini", "konbini-ja"), ("Shopping", "shopping-ja"),
                   ("At an izakaya", "izakaya-ja")],
         faq=[("What Japanese phrases should I learn before a trip?",
               "Start with すみません (sumimasen: excuse me, sorry, and thank you), これください (kore kudasai: I'll take this), "
               "and 大丈夫です (daijōbu desu: no thanks, I'm fine). With those three and pointing, you can get through most shops and restaurants."),
              ("Do I need to speak Japanese to travel in Japan?",
               "No. Signs in cities and on trains are in English too, and staff are used to visitors. A few phrases make every "
               "interaction smoother, and people really do appreciate the effort."),
              ("How do I pronounce Japanese?",
               "Japanese sounds are simpler than they look. Vowels are always a (ah), i (ee), u (oo), e (eh), o (oh), and a line over a "
               "vowel (ō, ū) just means hold it twice as long. Tap the speaker next to any phrase to hear it.")]),
    dict(lang="japanese", code="ja", speech="ja-JP", slug="konbini-phrases", name="Japanese", label="Konbini phrases",
         crumb="Konbini phrases",
         title="Japanese Konbini Phrases: {n} Words for the Convenience Store",
         h2="{n} konbini words and phrases, with readings",
         desc="Every phrase you'll hear at a Japanese konbini (7-Eleven, Lawson, FamilyMart), from いらっしゃいませ to レシート. {n} words with readings, meanings and audio.",
         h1="Japanese konbini phrases",
         intro="The konbini (7-Eleven, Lawson, FamilyMart) is where you'll speak the most Japanese on any trip. "
               "The staff ask the same few questions every time, so once you know them, checkout takes ten seconds.",
         sections=[("The words", "konbini-ja"), ("What staff ask, and how to answer", KONBINI_EXTRA)],
         faq=[("What does the konbini staff say when I walk in?",
               "いらっしゃいませ (irasshaimase): “welcome in”. It's not a question, so you don't need to answer. A small nod is plenty."),
              ("How do I say no thank you at a konbini?",
               "大丈夫です (daijōbu desu). It works for the bag, the chopsticks, heating your food and the point card. "
               "A small shake of the head works too."),
              ("Can I use a foreign card at a konbini?",
               "Usually, yes, for paying and at the ATM. 7-Eleven ATMs are the most reliable for foreign cards.")]),
]


def topics_by_lang():
    """lang slug -> [(topic slug, label)], for links from the language pages."""
    out = {}
    for t in PHRASE_TOPICS:
        out.setdefault(t["lang"], []).append((t["slug"], t["label"]))
    for t in TOPICS:
        out.setdefault(t["lang"], []).append((t["slug"], f"{t['name']} false friends"))
    return out


STYLE = """<style>
.ff{list-style:none;margin-top:14px;display:grid;gap:10px}
.ff li{display:grid;grid-template-columns:28px 1fr 34px;gap:4px 12px;align-items:start;border:1px solid var(--line);
  border-radius:14px;padding:14px 14px;background:var(--bg)}
.ff .num{color:var(--muted);font-size:13px;padding-top:3px;font-variant-numeric:tabular-nums}
.ff .w{font-size:20px;font-weight:800}
.ff .m{grid-column:2;font-size:15px}
.ff .m b{color:var(--accent2)}
.ff .not{grid-column:2;font-size:13.5px;color:var(--muted);line-height:1.55}
.ff .not .x{color:#F08A7E;font-weight:700}
.ff .not b{color:var(--text)}
.ff .say{grid-row:1/span 3;grid-column:3}
.ph{list-style:none;margin-top:12px;display:grid;gap:8px}
.ph li{display:grid;grid-template-columns:1fr 34px;gap:2px 12px;border:1px solid var(--line);border-radius:14px;padding:12px 14px;background:var(--bg)}
.ph .w{font-size:19px;font-weight:800}
.ph .rd{grid-column:1;font-size:13.5px;color:var(--accent2)}
.ph .g{grid-column:1;font-size:15px;font-weight:600;margin-top:4px}
.ph .nt{grid-column:1;font-size:13.5px;color:var(--muted);line-height:1.55}
.ph .say{grid-row:1/span 2;grid-column:2}
.card h3{font-size:17px;margin-top:22px}
.card h3:first-of-type{margin-top:14px}
.related{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:12px}
</style>"""

SAY_JS = """<script>
(function(){
  var main=document.querySelector('main'), list=document.querySelector('[data-speech]'), lang=list.getAttribute('data-speech');
  if(!('speechSynthesis' in window)){document.body.classList.add('no-say');return;}
  main.addEventListener('click',function(e){
    var b=e.target.closest('.say'); if(!b)return;
    speechSynthesis.cancel(); var u=new SpeechSynthesisUtterance(b.getAttribute('data-say')); u.lang=lang; u.rate=.85;
    var v=speechSynthesis.getVoices().filter(function(x){return x.lang&&x.lang.replace('_','-').indexOf(lang.split('-')[0])===0;})[0];
    if(v)u.voice=v; speechSynthesis.speak(u);
  });
})();
</script>"""


def build(t, items_by_carousel, H):
    """H: the helpers from learn_pages (HEAD, FOOT, BADGE, SITE, APP_STORE, PLAY_STORE, foot_langs, ALL_LANGS)."""
    items, seen = [], set()
    for c in t["carousels"]:
        for word, real, looks, right in items_by_carousel.get(c, []):
            if word.lower() in seen:
                continue
            seen.add(word.lower())
            items.append((word, real, looks, _right_html(looks, right)))
    n = len(items)
    url = f"{H['SITE']}/learn/{t['lang']}/{t['slug']}/"
    title = t["title"].format(n=n) + " | Vocab Swiper"
    desc = t["desc"].format(n=n)
    up = "../../../"
    faq = [("What is a false friend?", FF_FAQ_WHAT), t["worst"], ("How do you avoid false friends?", FF_FAQ_AVOID)]
    plain = lambda s: re.sub(r"<[^>]+>", "", s)
    jsonld = ('<script type="application/ld+json">' + json.dumps([
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Vocab Swiper", "item": H["SITE"] + "/"},
            {"@type": "ListItem", "position": 2, "name": "Languages", "item": H["SITE"] + "/learn/"},
            {"@type": "ListItem", "position": 3, "name": f"Learn {t['name']}", "item": f"{H['SITE']}/learn/{t['lang']}/"},
            {"@type": "ListItem", "position": 4, "name": f"{t['name']} false friends", "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(a)}} for q, a in faq]}],
        ensure_ascii=False) + "</script>")
    rows = "".join(
        f'<li><span class="num">{k}</span><span class="w" lang="{t["code"]}">{esc(w)}</span>'
        f'<button class="say" type="button" data-say="{esc(w)}" aria-label="Hear {esc(w)}"></button>'
        f'<span class="m">means <b>{esc(real)}</b></span>'
        f'<span class="not"><span class="x">Not “{esc(looks)}”.</span> {right}</span></li>'
        for k, (w, real, looks, right) in enumerate(items, 1))
    others = "".join(f'<a class="pill" href="../../{o["lang"]}/{o["slug"]}/">{esc(o["name"])}</a>'
                     for o in TOPICS if o is not t)
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{a}</p></details>" for q, a in faq)
    out = [H["HEAD"].format(title=esc(title), desc=esc(desc), url=url, site=H["SITE"], up=up,
                            store=H["APP_STORE"], jsonld=jsonld + STYLE)]
    out.append(f"""<main class="wrap">
<header class="hero">
  <div class="eyebrow"><a href="../../">Languages</a> / <a href="../">{esc(t['name'])}</a> / False friends</div>
  <h1>{esc(t['name'])} false friends</h1>
  <p class="lede">{t['intro'].format(n=n)}</p>
</header>

<section class="card">
  <h2>{n} {esc(t['name'])} words that don't mean what you think</h2>
  <p class="sub">What each word really means, and what to say instead. Tap the speaker to hear it.</p>
  <ol id="ff" class="ff" data-speech="{t['speech']}">{rows}</ol>
</section>

<section class="cta">
  <h2>Learn {esc(t['name'])} words the way people use them.</h2>
  <p class="free">Vocab Swiper shows every word in a real example sentence, so false friends don't catch you out. 50+ languages, free on the App Store and Google Play.</p>
  {H['BADGE'].format(store=H['APP_STORE'], play=H['PLAY_STORE'])}
</section>

<section class="card faq">
  <h2>Questions about {esc(t['name'])} false friends</h2>
  {faq_html}
</section>

<nav class="more" aria-label="More false friends">
  <h2>False friends in other languages</h2>
  <div class="related">{others}</div>
  <p style="margin-top:18px"><a class="all" href="../">Learn {esc(t['name'])} vocabulary →</a></p>
</nav>
</main>
{SAY_JS}
""")
    out.append(H["FOOT"].format(up=up, langs=H["foot_langs"](H["ALL_LANGS"], up)))
    return f"learn/{t['lang']}/{t['slug']}/", "".join(out)


def _speak(word, reading):
    """What the voice reads: the kana reading when there is one, else the word, without 〜 or …."""
    kana = reading.split(" · ")[0] if " · " in reading else ""
    text = kana if kana and re.search(r"[\u3040-\u30ff]", kana) else word
    return text.replace("〜", "").replace("…", "").strip()


def build_phrases(t, items_by_carousel, H):
    sections, seen, n = [], set(), 0
    for heading, src in t["sections"]:
        rows = []
        for w, r, g, note in (src if isinstance(src, list) else items_by_carousel.get(src, [])):
            if w in seen:
                continue
            seen.add(w)
            rows.append((w, READING_FIX.get(w, r), g, note))
        n += len(rows)
        sections.append((heading, rows))
    url = f"{H['SITE']}/learn/{t['lang']}/{t['slug']}/"
    title = t["title"].format(n=n) + " | Vocab Swiper"
    desc = t["desc"].format(n=n)
    up = "../../../"
    plain = lambda s: re.sub(r"<[^>]+>", "", s)
    jsonld = ('<script type="application/ld+json">' + json.dumps([
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Vocab Swiper", "item": H["SITE"] + "/"},
            {"@type": "ListItem", "position": 2, "name": "Languages", "item": H["SITE"] + "/learn/"},
            {"@type": "ListItem", "position": 3, "name": f"Learn {t['name']}", "item": f"{H['SITE']}/learn/{t['lang']}/"},
            {"@type": "ListItem", "position": 4, "name": t["label"], "item": url}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(a)}} for q, a in t["faq"]]}],
        ensure_ascii=False) + "</script>")

    def row(w, r, g, note):
        return (f'<li><span class="w" lang="{t["code"]}">{esc(w)}</span>'
                f'<button class="say" type="button" data-say="{esc(_speak(w, r))}" aria-label="Hear {esc(w)}"></button>'
                + (f'<span class="rd" lang="{t["code"]}">{esc(r)}</span>' if r and r != w else "")
                + f'<span class="g">{esc(g)}</span>'
                + (f'<span class="nt">{esc(note)}</span>' if note else "") + "</li>")
    body = "".join(f'<h3>{esc(h)}</h3><ul class="ph">{"".join(row(*x) for x in rows)}</ul>' for h, rows in sections)
    others = "".join(f'<a class="pill" href="../{o["slug"]}/">{esc(o["label"])}</a>'
                     for o in PHRASE_TOPICS if o["lang"] == t["lang"] and o is not t)
    if t["lang"] == "japanese":
        others += '<a class="pill" href="../jlpt-n5/">JLPT N5 vocabulary</a>'
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{a}</p></details>" for q, a in t["faq"])
    out = [H["HEAD"].format(title=esc(title), desc=esc(desc), url=url, site=H["SITE"], up=up,
                            store=H["APP_STORE"], jsonld=jsonld + STYLE)]
    out.append(f"""<main class="wrap">
<header class="hero">
  <div class="eyebrow"><a href="../../">Languages</a> / <a href="../">{esc(t['name'])}</a> / {esc(t['crumb'])}</div>
  <h1>{esc(t['h1'])}</h1>
  <p class="lede">{t['intro'].format(n=n)}</p>
</header>

<section class="card" data-speech="{t['speech']}">
  <h2>{esc(t['h2'].format(n=n))}</h2>
  <p class="sub">Tap the speaker to hear each one.</p>
  {body}
</section>

<section class="cta">
  <h2>Learn {esc(t['name'])} words the way people use them.</h2>
  <p class="free">Vocab Swiper shows every word in a real example sentence, with native audio and spaced repetition. 50+ languages, free on the App Store and Google Play.</p>
  {H['BADGE'].format(store=H['APP_STORE'], play=H['PLAY_STORE'])}
</section>

<section class="card faq">
  <h2>Questions</h2>
  {faq_html}
</section>

<nav class="more" aria-label="More {esc(t['name'])} word lists">
  <h2>More {esc(t['name'])} word lists</h2>
  <div class="related">{others}</div>
  <p style="margin-top:18px"><a class="all" href="../">Learn {esc(t['name'])} vocabulary →</a></p>
</nav>
</main>
{SAY_JS}
""")
    out.append(H["FOOT"].format(up=up, langs=H["foot_langs"](H["ALL_LANGS"], up)))
    return f"learn/{t['lang']}/{t['slug']}/", "".join(out)


def write_all(H):
    items = _carousel_items()
    paths = []
    for t in PHRASE_TOPICS:
        rel, page = build_phrases(t, items, H)
        d = os.path.join(ROOT, rel)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
        paths.append(rel)
    for t in TOPICS:
        rel, page = build(t, items, H)
        d = os.path.join(ROOT, rel)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
        paths.append(rel)
    return paths
