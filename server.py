from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import hashlib
import json
import mimetypes
import os
import random
import secrets
import threading
import time
import uuid


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
STORE_PATH = DATA_DIR / "store.json"

DATA_LOCK = threading.Lock()
SESSIONS = {}


BOARD_TYPE_WEIGHTS = [
    ("card", 54),
    ("boost", 14),
    ("break", 14),
    ("social", 10),
    ("surprise", 8),
]

CARD_DECKS = [
    {
        "title": "Seiten-Sprint",
        "description": "Lies 10 Seiten am Stueck.",
        "pages": 10,
        "xp": 20,
        "steps": (1, 3),
        "tag": "Tempo",
    },
    {
        "title": "Kapitel-Jaeger",
        "description": "Lies bis zum naechsten Kapitelende.",
        "pages": 16,
        "xp": 30,
        "steps": (2, 4),
        "tag": "Kapitel",
    },
    {
        "title": "Drei-Kapitel-Quest",
        "description": "Lies 3 Kapitel, egal wie lang sie sind.",
        "pages": 30,
        "xp": 55,
        "steps": (3, 6),
        "tag": "Ausdauer",
    },
    {
        "title": "Leise-Lesung",
        "description": "Lies 15 Minuten ohne Ablenkung.",
        "pages": 8,
        "xp": 18,
        "steps": (1, 2),
        "tag": "Fokus",
    },
    {
        "title": "Cliffhanger-Modus",
        "description": "Lies weiter, bis etwas Ueberraschendes passiert.",
        "pages": 14,
        "xp": 24,
        "steps": (2, 3),
        "tag": "Story",
    },
    {
        "title": "Charakterblick",
        "description": "Lies ein Kapitel und merke dir deinen Lieblingscharakter-Moment.",
        "pages": 12,
        "xp": 22,
        "steps": (1, 3),
        "tag": "Reflexion",
    },
    {
        "title": "Mondschein-Runde",
        "description": "Lies noch 20 Seiten vor dem Schlafen.",
        "pages": 20,
        "xp": 34,
        "steps": (2, 4),
        "tag": "Abend",
    },
    {
        "title": "Mini-Binge",
        "description": "Lies zwei Szenen hintereinander ohne auf die Uhr zu schauen.",
        "pages": 11,
        "xp": 20,
        "steps": (1, 3),
        "tag": "Flow",
    },
    {
        "title": "Plot-Turbo",
        "description": "Lies 25 Seiten und notiere dir innerlich die groesste Wendung.",
        "pages": 25,
        "xp": 40,
        "steps": (3, 5),
        "tag": "Plot",
    },
    {
        "title": "Genre-Sprung",
        "description": "Lies heute etwas, das sich komplett anders anfuehlt als gestern.",
        "pages": 9,
        "xp": 22,
        "steps": (1, 2),
        "tag": "Abwechslung",
    },
]

SPACE_ACTIONS = {
    "boost": [
        {"title": "Buchmagie", "description": "Du findest sofort in den Lesefluss und ziehst 2 Bonusfelder weiter.", "steps": 2, "xp": 12},
        {"title": "Perfekter Platz", "description": "Dein Leseplatz ist ideal. +1 Feld und +8 XP.", "steps": 1, "xp": 8},
        {"title": "Leselaune", "description": "Du bist im Tunnel. +2 Felder.", "steps": 2, "xp": 6},
    ],
    "break": [
        {"title": "Getraenke-Pause", "description": "Hol dir etwas zu trinken und atme durch. Keine Felder, aber +10 XP fuer Konstanz.", "steps": 0, "xp": 10},
        {"title": "Kurz aufstehen", "description": "2 Minuten Strecken und weiter geht's. +1 Feld.", "steps": 1, "xp": 6},
        {"title": "Fensterblick", "description": "Kurze Pause fuer den Kopf. Du verlierst nichts und bekommst +5 XP.", "steps": 0, "xp": 5},
    ],
    "social": [
        {"title": "Buddy-Blick", "description": "Schau, wie dein Lesepartner vorankommt. +1 Feld Motivation.", "steps": 1, "xp": 10},
        {"title": "Buchtipp", "description": "Teile spontan einen Satz ueber dein Buch. +1 Feld.", "steps": 1, "xp": 7},
        {"title": "Gemeinsamer Push", "description": "Euer gemeinsamer Fortschritt motiviert dich. +2 Felder.", "steps": 2, "xp": 9},
    ],
    "surprise": [
        {"title": "Geheimer Leseweg", "description": "Du entdeckst einen versteckten Pfad. +3 Felder.", "steps": 3, "xp": 15},
        {"title": "Kleiner Umweg", "description": "Du suchst deine Stelle, verlierst aber nur kurz den Takt. -1 Feld, +4 XP.", "steps": -1, "xp": 4},
        {"title": "Plot-Blitz", "description": "Das Buch packt dich komplett. +4 Felder.", "steps": 4, "xp": 12},
    ],
}


def load_store():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        initial_data = {"users": {}, "rooms": {}, "feed": []}
        STORE_PATH.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")
    with STORE_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("users", {})
    data.setdefault("rooms", {})
    data.setdefault("feed", [])
    return data


def save_store(data):
    with STORE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def now_ts():
    return int(time.time())


def make_room_code():
    return secrets.token_hex(3).upper()


def make_session():
    return secrets.token_urlsafe(24)


def level_from_xp(xp):
    return max(1, xp // 120 + 1)


def xp_to_next_level(xp):
    level = level_from_xp(xp)
    next_level_total = level * 120
    return next_level_total - xp


def add_feed_event(store, room_id, message):
    event = {
        "id": uuid.uuid4().hex,
        "roomId": room_id,
        "message": message,
        "createdAt": now_ts(),
    }
    store["feed"].append(event)
    store["feed"] = store["feed"][-200:]


def get_room_feed(store, room_id):
    items = [item for item in store["feed"] if item["roomId"] == room_id]
    return list(reversed(items[-16:]))


def seeded_random(*parts):
    seed = "|".join(str(part) for part in parts)
    return random.Random(seed)


def board_type_for(room_code, position):
    rng = seeded_random(room_code, position, "board")
    roll = rng.randint(1, 100)
    total = 0
    for tile_type, weight in BOARD_TYPE_WEIGHTS:
        total += weight
        if roll <= total:
            return tile_type
    return "card"


def generate_board_window(room_code, center, radius=6):
    spaces = []
    for position in range(max(0, center - radius), center + radius + 1):
        tile_type = board_type_for(room_code, position)
        spaces.append(
            {
                "position": position,
                "type": tile_type,
                "label": tile_type.capitalize(),
            }
        )
    return spaces


def public_user(user):
    xp = user["xp"]
    return {
        "id": user["id"],
        "username": user["username"],
        "displayName": user["displayName"],
        "position": user["position"],
        "level": level_from_xp(xp),
        "xp": xp,
        "xpToNextLevel": xp_to_next_level(xp),
        "pagesRead": user["pagesRead"],
        "cardsCompleted": user["cardsCompleted"],
        "activeRoomId": user.get("activeRoomId"),
        "currentCard": user.get("currentCard"),
        "lastActionAt": user.get("lastActionAt"),
    }


def create_room(owner_id, name):
    room_id = uuid.uuid4().hex
    code = make_room_code()
    return {
        "id": room_id,
        "name": name.strip() or "Lesebande",
        "code": code,
        "ownerId": owner_id,
        "memberIds": [owner_id],
        "createdAt": now_ts(),
    }


def create_user(username, password, display_name):
    return {
        "id": uuid.uuid4().hex,
        "username": username,
        "displayName": display_name,
        "passwordHash": hash_password(password),
        "createdAt": now_ts(),
        "position": 0,
        "xp": 0,
        "pagesRead": 0,
        "cardsCompleted": 0,
        "activeRoomId": None,
        "currentCard": None,
        "lastActionAt": now_ts(),
    }


def card_for_user(user, room_code):
    rng = seeded_random(user["id"], user["cardsCompleted"], user["xp"], room_code, now_ts() // 60)
    template = rng.choice(CARD_DECKS)
    steps = rng.randint(template["steps"][0], template["steps"][1])
    return {
        "id": uuid.uuid4().hex,
        "title": template["title"],
        "description": template["description"],
        "pages": template["pages"],
        "xpReward": template["xp"],
        "stepsReward": steps,
        "tag": template["tag"],
        "createdAt": now_ts(),
    }


def resolve_space_effect(room, user):
    tile_type = board_type_for(room["code"], user["position"])
    if tile_type == "card":
        return {
            "tileType": tile_type,
            "event": {
                "title": "Kartenfeld",
                "description": "Hier wartet die naechste Leseaufgabe auf dich.",
                "steps": 0,
                "xp": 0,
            },
        }

    event = random.choice(SPACE_ACTIONS[tile_type])
    user["position"] = max(0, user["position"] + event["steps"])
    user["xp"] += event["xp"]
    user["lastActionAt"] = now_ts()
    return {"tileType": tile_type, "event": event}


def find_user_by_username(store, username):
    for user in store["users"].values():
        if user["username"].lower() == username.lower():
            return user
    return None


def ensure_user_room(store, user):
    room_id = user.get("activeRoomId")
    if not room_id:
        return None
    room = store["rooms"].get(room_id)
    if not room:
        user["activeRoomId"] = None
        return None
    if user["id"] not in room["memberIds"]:
        room["memberIds"].append(user["id"])
    return room


class ReadingBoardHandler(BaseHTTPRequestHandler):
    server_version = "ReadingBoard/1.0"

    def log_message(self, format_string, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.route_api("GET", parsed.path, {})
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b""
        payload = {}
        if raw_body:
            content_type = self.headers.get("Content-Type", "")
            if "application/json" in content_type:
                payload = json.loads(raw_body.decode("utf-8"))
            else:
                payload = {key: values[0] for key, values in parse_qs(raw_body.decode("utf-8")).items()}
        self.route_api("POST", parsed.path, payload)

    def send_json(self, status_code, payload, headers=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if headers:
            for key, value in headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status_code, message):
        self.send_json(status_code, {"error": message})

    def get_session_user(self, store):
        cookie_header = self.headers.get("Cookie", "")
        cookies = {}
        for part in cookie_header.split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                cookies[key] = value
        session_id = cookies.get("reading_board_session")
        user_id = SESSIONS.get(session_id)
        if not user_id:
            return None
        return store["users"].get(user_id)

    def require_user(self, store):
        user = self.get_session_user(store)
        if not user:
            self.send_error_json(401, "Bitte zuerst einloggen.")
            return None
        return user

    def route_api(self, method, path, payload):
        with DATA_LOCK:
            store = load_store()
            if path == "/api/register" and method == "POST":
                self.handle_register(store, payload)
                return
            if path == "/api/login" and method == "POST":
                self.handle_login(store, payload)
                return
            if path == "/api/logout" and method == "POST":
                self.handle_logout()
                return
            if path == "/api/bootstrap" and method == "GET":
                self.handle_bootstrap(store)
                return
            if path == "/api/rooms/create" and method == "POST":
                self.handle_room_create(store, payload)
                return
            if path == "/api/rooms/join" and method == "POST":
                self.handle_room_join(store, payload)
                return
            if path == "/api/cards/draw" and method == "POST":
                self.handle_draw_card(store)
                return
            if path == "/api/cards/complete" and method == "POST":
                self.handle_complete_card(store)
                return
            self.send_error_json(404, "Route nicht gefunden.")

    def handle_register(self, store, payload):
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        display_name = (payload.get("displayName") or "").strip() or username
        if len(username) < 3 or len(password) < 4:
            self.send_error_json(400, "Username mindestens 3 Zeichen, Passwort mindestens 4.")
            return
        if find_user_by_username(store, username):
            self.send_error_json(400, "Dieser Username ist schon vergeben.")
            return

        user = create_user(username, password, display_name)
        room = create_room(user["id"], f"{display_name}s Lesebande")
        user["activeRoomId"] = room["id"]
        store["users"][user["id"]] = user
        store["rooms"][room["id"]] = room
        add_feed_event(store, room["id"], f"{display_name} hat die Lesebande betreten.")
        save_store(store)

        session_id = make_session()
        SESSIONS[session_id] = user["id"]
        self.send_json(
            201,
            {"ok": True, "user": public_user(user)},
            headers={"Set-Cookie": f"reading_board_session={session_id}; HttpOnly; Path=/; SameSite=Lax"},
        )

    def handle_login(self, store, payload):
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        user = find_user_by_username(store, username)
        if not user or user["passwordHash"] != hash_password(password):
            self.send_error_json(401, "Login fehlgeschlagen.")
            return

        session_id = make_session()
        SESSIONS[session_id] = user["id"]
        self.send_json(
            200,
            {"ok": True, "user": public_user(user)},
            headers={"Set-Cookie": f"reading_board_session={session_id}; HttpOnly; Path=/; SameSite=Lax"},
        )

    def handle_logout(self):
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            if part.strip().startswith("reading_board_session="):
                session_id = part.strip().split("=", 1)[1]
                SESSIONS.pop(session_id, None)
                break
        self.send_json(
            200,
            {"ok": True},
            headers={"Set-Cookie": "reading_board_session=deleted; HttpOnly; Path=/; Max-Age=0; SameSite=Lax"},
        )

    def handle_bootstrap(self, store):
        user = self.get_session_user(store)
        if not user:
            self.send_json(200, {"authenticated": False})
            return

        room = ensure_user_room(store, user)
        if room:
            save_store(store)
        payload = {"authenticated": True, "user": public_user(user)}
        if room:
            players = [public_user(store["users"][member_id]) for member_id in room["memberIds"] if member_id in store["users"]]
            center = max([player["position"] for player in players] + [user["position"]])
            payload["room"] = {
                "id": room["id"],
                "name": room["name"],
                "code": room["code"],
                "players": sorted(players, key=lambda item: (-item["position"], -item["xp"], item["displayName"].lower())),
                "board": generate_board_window(room["code"], center),
                "feed": get_room_feed(store, room["id"]),
            }
        self.send_json(200, payload)

    def handle_room_create(self, store, payload):
        user = self.require_user(store)
        if not user:
            return
        room = create_room(user["id"], payload.get("name") or f"{user['displayName']}s Lesebande")
        store["rooms"][room["id"]] = room
        user["activeRoomId"] = room["id"]
        add_feed_event(store, room["id"], f"{user['displayName']} hat den Raum erstellt.")
        save_store(store)
        self.send_json(201, {"ok": True, "roomId": room["id"], "code": room["code"]})

    def handle_room_join(self, store, payload):
        user = self.require_user(store)
        if not user:
            return
        room_code = (payload.get("code") or "").strip().upper()
        room = None
        for existing_room in store["rooms"].values():
            if existing_room["code"] == room_code:
                room = existing_room
                break
        if not room:
            self.send_error_json(404, "Kein Raum mit diesem Code gefunden.")
            return
        if user["id"] not in room["memberIds"]:
            room["memberIds"].append(user["id"])
        user["activeRoomId"] = room["id"]
        add_feed_event(store, room["id"], f"{user['displayName']} ist der Lesebande beigetreten.")
        save_store(store)
        self.send_json(200, {"ok": True, "roomId": room["id"], "code": room["code"]})

    def handle_draw_card(self, store):
        user = self.require_user(store)
        if not user:
            return
        room = ensure_user_room(store, user)
        if not room:
            self.send_error_json(400, "Erstelle oder betrete zuerst einen Raum.")
            return
        if user.get("currentCard"):
            self.send_error_json(400, "Du hast bereits eine aktive Karte.")
            return
        card = card_for_user(user, room["code"])
        user["currentCard"] = card
        user["lastActionAt"] = now_ts()
        add_feed_event(store, room["id"], f"{user['displayName']} hat die Karte '{card['title']}' gezogen.")
        save_store(store)
        self.send_json(200, {"ok": True, "card": card})

    def handle_complete_card(self, store):
        user = self.require_user(store)
        if not user:
            return
        room = ensure_user_room(store, user)
        if not room:
            self.send_error_json(400, "Kein aktiver Raum gefunden.")
            return
        card = user.get("currentCard")
        if not card:
            self.send_error_json(400, "Du hast keine offene Karte.")
            return

        user["pagesRead"] += card["pages"]
        user["xp"] += card["xpReward"]
        user["cardsCompleted"] += 1
        user["position"] += card["stepsReward"]
        user["currentCard"] = None
        user["lastActionAt"] = now_ts()

        add_feed_event(
            store,
            room["id"],
            f"{user['displayName']} hat '{card['title']}' abgeschlossen und ist auf Feld {user['position']} gezogen.",
        )

        effect = resolve_space_effect(room, user)
        if effect["tileType"] != "card":
            add_feed_event(store, room["id"], f"{user['displayName']} landet auf {effect['tileType']} und erlebt: {effect['event']['title']}.")
        save_store(store)
        self.send_json(
            200,
            {
                "ok": True,
                "completedCard": card,
                "spaceEffect": effect,
                "user": public_user(user),
            },
        )

    def serve_static(self, path):
        if path == "/":
            path = "/index.html"
        file_path = (STATIC_DIR / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.exists() or not file_path.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return
        content_type, _ = mimetypes.guess_type(str(file_path))
        payload = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def run():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8123"))
    print(f"Reading Board App laeuft auf http://{host}:{port}")
    server = ThreadingHTTPServer((host, port), ReadingBoardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
