"""Maakt een RSS-feed van het nieuws op foerch.be (Nieuws en Events).

Leest de publieke OCC-API van foerch.be, haalt de artikelkaarten uit het
overzicht "Alle artikels" en schrijft docs/feed-nl.xml en docs/feed-fr.xml.

pubDate is het moment waarop het script een artikel voor het eerst zag
(bewaard in docs/gezien.json). Zo mist de Power Automate-flow geen artikel
dat met een oudere datum online komt. Bij de eerste run krijgen alle
bestaande artikels hun eigen datum, zodat er geen vloed aan berichten komt.
"""

import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from html.parser import HTMLParser
from pathlib import Path

API = (
    "https://shopapi.foerch.com/rest/v2/foerch-be/users/anonymous/cms/pages"
    "?fields=FULL&pageType=ContentPage&pageLabelOrId=/over-ons/nieuws-en-events"
    "&lang={lang}&curr=EUR"
)
SITE = "https://www.foerch.be"
DOCS = Path(__file__).parent / "docs"
GEZIEN = DOCS / "gezien.json"
TALEN = {
    "nl": ("nl_BE", "FÖRCH Belux: nieuws en events", "nl-BE"),
    "fr": ("fr_BE", "FÖRCH Belux : actualités et événements", "fr-BE"),
}


class Kaarten(HTMLParser):
    """Verzamelt de <a class="nw-card"> blokken uit het overzicht."""

    def __init__(self):
        super().__init__()
        self.kaarten = []
        self.huidig = None
        self.veld = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        klasse = a.get("class", "")
        if tag == "a" and "nw-card" in klasse.split():
            self.huidig = {"href": a.get("href", ""), "titel": "", "sub": "", "datum": "", "beeld": ""}
        elif self.huidig is None:
            return
        elif tag == "img" and "nw-img" in klasse:
            self.huidig["beeld"] = a.get("src", "")
        elif tag == "time":
            self.huidig["datum"] = a.get("datetime", "")
        elif "nw-title" in klasse:
            self.veld = "titel"
        elif "nw-sub" in klasse:
            self.veld = "sub"

    def handle_endtag(self, tag):
        if tag == "a" and self.huidig is not None:
            self.kaarten.append(self.huidig)
            self.huidig = None
        if tag == "div":
            self.veld = None

    def handle_data(self, data):
        if self.huidig is not None and self.veld:
            self.huidig[self.veld] += data


def haal_kaarten(lang):
    req = urllib.request.Request(API.format(lang=lang), headers={"User-Agent": "foerch-belux-nieuwsfeed"})
    with urllib.request.urlopen(req, timeout=60) as r:
        pagina = json.load(r)
    componenten = pagina["contentSlots"]["contentSlot"][0]["components"]["component"]
    inhoud = next(c["content"] for c in componenten if "nw-card" in (c.get("content") or "") and "nw-grid" in c["content"])
    inhoud = re.sub(r"<style>.*?</style>", "", inhoud, flags=re.S)
    p = Kaarten()
    p.feed(inhoud)
    kaarten = [k for k in p.kaarten if "/blogs/" in k["href"]]
    if not kaarten:
        sys.exit("Geen artikels gevonden: is de structuur van de nieuwspagina gewijzigd?")
    return kaarten


def rss(kaarten, gezien, titel, taal):
    nu = format_datetime(datetime.now(timezone.utc))
    items = []
    for k in kaarten:
        link = SITE + k["href"]
        datum = datetime.fromisoformat(gezien[k["href"]])
        beeldtype = "image/png" if ".png" in k["beeld"] else "image/jpeg"
        items.append(
            "<item>"
            f"<title>{html.escape(k['titel'].strip())}</title>"
            f"<link>{html.escape(link)}</link>"
            f"<guid isPermaLink=\"true\">{html.escape(link)}</guid>"
            f"<description>{html.escape(k['sub'].strip())}</description>"
            # De Power Automate RSS-connector geeft geen enclosure door, wel categories: daar zit het beeld.
            f"<category>{html.escape(k['beeld'])}</category>"
            f"<enclosure url=\"{html.escape(k['beeld'])}\" type=\"{beeldtype}\" length=\"0\"/>"
            f"<pubDate>{format_datetime(datum)}</pubDate>"
            "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">'
        f"<channel><title>{html.escape(titel)}</title><link>{SITE}/over-ons/nieuws-en-events</link>"
        f"<description>{html.escape(titel)}</description><language>{taal}</language>"
        f"<lastBuildDate>{nu}</lastBuildDate>" + "".join(items) + "</channel></rss>\n"
    )


def main():
    DOCS.mkdir(exist_ok=True)
    eerste_run = not GEZIEN.exists()
    gezien = {} if eerste_run else json.loads(GEZIEN.read_text())
    nu = datetime.now(timezone.utc).replace(microsecond=0)

    for code, (lang, titel, taal) in TALEN.items():
        kaarten = haal_kaarten(lang)
        for k in kaarten:
            if k["href"] not in gezien:
                if eerste_run and k["datum"]:
                    gezien[k["href"]] = datetime.fromisoformat(k["datum"]).replace(tzinfo=timezone.utc).isoformat()
                else:
                    gezien[k["href"]] = nu.isoformat()
        kaarten.sort(key=lambda k: gezien[k["href"]], reverse=True)
        (DOCS / f"feed-{code}.xml").write_text(rss(kaarten, gezien, titel, taal), encoding="utf-8")
        print(f"{code}: {len(kaarten)} artikels")

    GEZIEN.write_text(json.dumps(gezien, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
