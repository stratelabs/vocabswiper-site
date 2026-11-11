#!/usr/bin/env python3
"""Product landing pages: /flashcards/ and /compare/quizlet-alternative/.

They target the searches people use when they're choosing an app ("vocabulary flashcard app",
"flashcard app for language learning", "quizlet alternatives"). Called from learn_pages.py, which
passes in its page parts. Facts follow ~/Desktop/VocabSwiper/MARKETING_FACTS.md: free to download on
iPhone and Android, a Pro subscription for premium voices and advanced features, no prices.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def esc(s):
    import html
    return html.escape(str(s), quote=True)


STYLE = """<style>
.steps4{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:14px}
.steps4 div{border:1px solid var(--line);border-radius:16px;padding:16px;background:var(--bg)}
.steps4 b{display:block;font-size:15.5px}
.steps4 span{display:block;color:var(--muted);font-size:13.5px;line-height:1.55;margin-top:6px}
.steps4 i{font-style:normal;color:var(--accent2);font-weight:800;font-size:12px;letter-spacing:1.5px}
.cmp{width:100%;border-collapse:collapse;margin-top:14px;font-size:14.5px}
.cmp th,.cmp td{text-align:left;vertical-align:top;padding:12px 10px;border-top:1px solid var(--line);line-height:1.5}
.cmp thead th{border-top:0;color:var(--accent2);font-size:12px;letter-spacing:1.5px;text-transform:uppercase}
.cmp td:first-child{color:var(--muted);width:28%}
.pick{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin-top:14px}
.pick div{border:1px solid var(--line);border-radius:16px;padding:16px;background:var(--bg)}
.pick ul{margin:8px 0 0 18px;color:rgba(11,18,32,.84);font-size:14.5px;line-height:1.7}
@media (max-width:560px){.cmp td:first-child{width:auto}.cmp th,.cmp td{padding:10px 6px;font-size:13.5px}}
</style>"""


def _jsonld(items):
    return '<script type="application/ld+json">' + json.dumps(items, ensure_ascii=False) + "</script>"


def _faq(faq):
    plain = lambda s: re.sub(r"<[^>]+>", "", s)
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": plain(a)}} for q, a in faq]}


def _page(H, rel, up, title, desc, jsonld, body):
    url = f"{H['SITE']}/{rel}"
    out = [H["HEAD"].format(title=esc(title), desc=esc(desc), url=url, site=H["SITE"], up=up,
                            store=H["APP_STORE"], jsonld=jsonld + STYLE)]
    out.append(body)
    out.append(H["FOOT"].format(up=up, langs=H["foot_langs"](H["ALL_LANGS"], up)))
    path = os.path.join(ROOT, rel)
    os.makedirs(path, exist_ok=True)
    open(os.path.join(path, "index.html"), "w", encoding="utf-8").write("".join(out))
    return rel


def flashcards(H):
    langs = H["ALL_LANGS"]
    n_lang = len(langs)
    rel, up = "flashcards/", "../"
    title = "Vocabulary Flashcard App: Flashcards You Swipe, in 56 Languages | Vocab Swiper".replace("56", str(n_lang))
    desc = (f"Vocab Swiper is a free vocabulary flashcard app for iPhone and Android. Ready-made decks in {n_lang} languages, "
            "native audio and example sentences, and spaced repetition that brings each card back right before you'd forget it.")
    faq = [
        ("Is Vocab Swiper free?",
         "Yes. It's free to download on iPhone and Android, and the flashcards are free to learn with. "
         "An optional Pro subscription adds premium voices and some advanced features."),
        ("What is spaced repetition?",
         "A way of timing reviews. Each card comes back just before you'd forget it: soon after you learn it, then at longer "
         "and longer gaps as it sticks. It takes far fewer reviews than going through a pile of flashcards in order. "
         "Vocab Swiper uses FSRS, a modern spaced repetition algorithm."),
        ("Why swipe instead of flipping a card?",
         "Grading yourself is one motion, so a review takes a couple of seconds and you can do ten in the queue for coffee. "
         "Swipe right if you knew it, left if you didn't. Peeking at the answer first counts as a miss."),
        ("Can I add my own words?",
         "Yes. Met a word in a lesson, a show or a menu? Tap + and add it. It goes into your own deck, next to the ready-made ones."),
        ("Which languages are there?",
         f"{n_lang} languages, each with a real graded deck of thousands of words: Japanese (JLPT N5 to N1), Korean, Chinese, "
         "Spanish, French, German, Italian, Portuguese and many more. See them all on the languages page."),
    ]
    jsonld = _jsonld([
        {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Vocab Swiper",
         "operatingSystem": "iOS, Android", "applicationCategory": "EducationalApplication",
         "description": desc, "url": f"{H['SITE']}/{rel}",
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}},
        _faq(faq)])
    top = sorted(langs, key=lambda l: -len(l["rows"]))[:12]
    cards = "".join(f'<a class="lang" href="../learn/{l["slug"]}/"><span class="n">{esc(l["name"])}</span>'
                    f'<span class="c">{len(l["rows"]):,} words</span></a>' for l in top)
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{a}</p></details>" for q, a in faq)
    body = f"""<main class="wrap">
<header class="hero">
  <div class="eyebrow">Flashcard app</div>
  <h1>Vocabulary flashcards you swipe</h1>
  <p class="lede">Vocab Swiper is a flashcard app built for learning a language's vocabulary. Every card is a real word with audio and an example sentence. Recall it, reveal it, swipe to grade yourself, and spaced repetition decides when you see it again.</p>
  {H['BADGE'].format(store=H['APP_STORE'], play=H['PLAY_STORE'])}
</header>

<section class="card">
  <h2>How the flashcards work</h2>
  <div class="steps4">
    <div><i>1</i><b>Recall first</b><span>You see the word and try to remember what it means before you reveal it. Peeking counts as a miss.</span></div>
    <div><i>2</i><b>Swipe to grade</b><span>Right if you knew it, left if you didn't. One motion, about two seconds a card.</span></div>
    <div><i>3</i><b>Spaced repetition</b><span>FSRS brings each card back right before you'd forget it, so you review less and remember more.</span></div>
    <div><i>4</i><b>Then use it</b><span>As words stick, you spell them, type them, say them out loud and read them in short stories.</span></div>
  </div>
</section>

<section class="card">
  <h2>Ready-made decks in {n_lang} languages</h2>
  <p class="sub">No building flashcards by hand. Every language has a graded deck of real words, levelled to JLPT, HSK, TOPIK or CEFR, with the most common words first. You can add your own words too.</p>
  <div class="grid" style="margin-top:14px">{cards}</div>
  <p style="margin-top:14px"><a class="all" href="../learn/">All {n_lang} languages →</a></p>
</section>

<section class="card">
  <h2>Free word lists</h2>
  <p class="sub">Study on the web, then let the app handle the reviews.</p>
  <div class="links" style="margin-top:12px">
    <a href="../learn/japanese/jlpt-n5/">JLPT N5 vocabulary</a><a href="../learn/japanese/travel-phrases/">Japanese travel phrases</a>
    <a href="../learn/spanish/false-friends/">Spanish false friends</a><a href="../learn/french/false-friends/">French false friends</a>
    <a href="../learn/japanese/jlpt-test/">Free JLPT level test</a>
  </div>
</section>

<section class="cta">
  <h2>Your first deck is one swipe away.</h2>
  <p class="free">Free to download. Works offline once your deck is on your phone.</p>
  {H['BADGE'].format(store=H['APP_STORE'], play=H['PLAY_STORE'])}
</section>

<section class="card faq">
  <h2>Questions</h2>
  {faq_html}
</section>

<nav class="more" aria-label="Compare">
  <p><a class="all" href="../compare/quizlet-alternative/">Vocab Swiper vs Quizlet for learning a language →</a></p>
</nav>
</main>
"""
    return _page(H, rel, up, title, desc, jsonld, body)


def quizlet(H):
    n_lang = len(H["ALL_LANGS"])
    rel, up = "compare/quizlet-alternative/", "../../"
    title = "A Quizlet Alternative for Learning Languages | Vocab Swiper"
    desc = ("Looking for a Quizlet alternative for language vocabulary? How Vocab Swiper compares: ready-made decks in "
            f"{n_lang} languages, spaced repetition, audio and example sentences. Free on iPhone and Android.")
    faq = [
        ("Is there a free Quizlet alternative for learning languages?",
         f"Vocab Swiper is free to download on iPhone and Android, with ready-made vocabulary decks in {n_lang} languages "
         "and spaced repetition built in. An optional Pro subscription adds premium voices and some advanced features."),
        ("Is Vocab Swiper better than Quizlet?",
         "For learning a language's vocabulary from scratch, it's built for exactly that: graded decks, audio, example sentences "
         "and review timing are all done for you. For other subjects, or a set your teacher shared, Quizlet is the better fit."),
        ("Can I bring my own word list?",
         "You can add your own words to your own decks, next to the ready-made ones, so a word from class or a show goes straight into your reviews."),
    ]
    jsonld = _jsonld([_faq(faq)])
    rows = [
        ("Built for", "Studying anything: languages, science, history, exams", "Learning a language's vocabulary"),
        ("Where the cards come from", "Sets you make, or sets other users made", f"Ready-made graded decks in {n_lang} languages, plus your own words"),
        ("Levels", "Whatever the set's author chose", "JLPT, HSK, TOPIK or CEFR levels, most common words first"),
        ("Audio and sentences", "Text-to-speech; example sentences if the set has them", "Audio for every word, and example sentences for every card"),
        ("When you review", "You pick a study mode and go", "Spaced repetition (FSRS) schedules every card for you"),
        ("Price", "Free plan, plus a paid Quizlet Plus plan", "Free to download, plus an optional Pro subscription"),
    ]
    table = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in rows)
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{a}</p></details>" for q, a in faq)
    body = f"""<main class="wrap">
<header class="hero">
  <div class="eyebrow"><a href="../../flashcards/">Flashcard app</a> / Compare</div>
  <h1>A Quizlet alternative for learning languages</h1>
  <p class="lede">Quizlet is a great all-round study tool. But if what you're studying is a language, you end up building or hunting for decks, guessing which words matter, and deciding when to review. Vocab Swiper does those parts for you.</p>
  {H['BADGE'].format(store=H['APP_STORE'], play=H['PLAY_STORE'])}
</header>

<section class="card">
  <h2>Quizlet vs Vocab Swiper</h2>
  <table class="cmp">
    <thead><tr><th></th><th>Quizlet</th><th>Vocab Swiper</th></tr></thead>
    <tbody>{table}</tbody>
  </table>
</section>

<section class="card">
  <h2>Which one should you use?</h2>
  <div class="pick">
    <div><b>Pick Quizlet if</b><ul><li>you're studying something other than a language</li><li>your teacher shared a set for class</li><li>you want games like Match</li></ul></div>
    <div><b>Pick Vocab Swiper if</b><ul><li>you're learning a language's vocabulary</li><li>you want decks that already exist, levelled and in order</li><li>you'd rather the app decide when to review</li></ul></div>
  </div>
  <p class="sub" style="margin-top:14px">Plenty of people use both: Quizlet for class sets, Vocab Swiper for the language itself.</p>
</section>

<section class="cta">
  <h2>Try the swipe flashcards.</h2>
  <p class="free">Free on iPhone and Android. <a href="../../flashcards/" style="color:var(--accent2)">How the flashcards work →</a></p>
  {H['BADGE'].format(store=H['APP_STORE'], play=H['PLAY_STORE'])}
</section>

<section class="card faq">
  <h2>Questions</h2>
  {faq_html}
</section>
<p class="credit">Quizlet is a trademark of Quizlet, Inc. Vocab Swiper isn't affiliated with Quizlet. Comparison written in November 2026; check Quizlet's site for its current plans.</p>
<nav class="more"><a class="all" href="../../learn/">Browse all {n_lang} languages →</a></nav>
</main>
"""
    return _page(H, rel, up, title, desc, jsonld, body)


def write_all(H):
    return [flashcards(H), quizlet(H)]
