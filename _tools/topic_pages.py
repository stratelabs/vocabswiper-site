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
    return out


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


def topics_by_lang():
    """lang slug -> [(topic slug, label)], for links from the language pages."""
    out = {}
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
.related{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:12px}
</style>"""

SAY_JS = """<script>
(function(){
  var list=document.getElementById('ff'), lang=list.getAttribute('data-speech');
  if(!('speechSynthesis' in window)){document.body.classList.add('no-say');return;}
  list.addEventListener('click',function(e){
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


def write_all(H):
    items = _carousel_items()
    paths = []
    for t in TOPICS:
        rel, page = build(t, items, H)
        d = os.path.join(ROOT, rel)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(page)
        paths.append(rel)
    return paths
