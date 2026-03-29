# Reading Board

Eine kleine Lese-App mit Brettspiel-Feeling:

- Nutzer koennen eigene Konten erstellen.
- Jeder Nutzer levelt ueber XP und Fortschritt.
- Das Spielbrett ist endlos und erzeugt immer neue Felder.
- Karten stehen im Mittelpunkt: lesen, Kapitel schaffen, Fokus-Sprints, kreative Aufgaben.
- Ueber Raum-Codes kann man das Spiel mit anderen teilen und gegenseitig den Fortschritt sehen.

## Starten

```bash
cd /tmp/reading-board-app
python3 server.py
```

Dann im Browser `http://127.0.0.1:8123` oeffnen.

## Online stellen

Am einfachsten ist es mit einem Python-Webhoster wie Render oder Railway.

Wichtig:

- Die App ist jetzt so vorbereitet, dass sie online auf dem vom Hoster vorgegebenen Port startet.
- Aktuell speichert sie Daten in `data/store.json`.
- Sessions liegen noch im Arbeitsspeicher. Wenn der Server neu startet, muss man sich neu einloggen.

### Einfache Variante mit GitHub + Render

1. Lege auf GitHub ein neues Repository an.
2. Lade den Ordner `/tmp/reading-board-app` dort hoch.
3. Erstelle bei Render einen neuen `Web Service`.
4. Verbinde dein GitHub-Repository.
5. Stelle als Start Command ein:

```bash
python3 server.py
```

6. Wenn Render fertig ist, bekommst du eine Internet-Adresse wie `https://deine-app.onrender.com`.
7. Diese Adresse kannst du dann an andere schicken.

### Wichtiger Hinweis

Fuer einen ersten Online-Prototyp reicht das gut. Fuer eine "richtige" App waeren als naechstes sinnvoll:

- echte Datenbank statt `store.json`
- persistente Logins statt nur In-Memory-Sessions
- spaeter eventuell Passwort-Reset und Einladungslinks

## Hinweise

- Die Daten werden in `data/store.json` gespeichert.
- Die Mehrspieler-Sicht funktioniert, wenn mehrere Browser oder Inkognito-Fenster denselben Raum-Code verwenden.
