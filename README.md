# Nieuwsfeed FÖRCH Belux

Maakt een RSS-feed van Nieuws en Events op foerch.be, voor de koppeling met het intranet (S365-FRCHBeluxIntranet) via Power Automate.

- `maak_feed.py` leest de publieke API van foerch.be en schrijft `docs/feed-nl.xml` en `docs/feed-fr.xml`.
- `docs/gezien.json` onthoudt wanneer elk artikel voor het eerst gezien is. Niet handmatig aanpassen.
- GitHub Actions draait het script op werkdagen om 6.15, 10.15 en 14.15 uur (Belgische wintertijd) en bewaart alleen een wijziging als er een nieuw artikel is.
- GitHub Pages publiceert de map `docs`.

Beheer: marketing FÖRCH Belux (Tobias Verbruggen).
