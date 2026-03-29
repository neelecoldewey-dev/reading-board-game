const state = {
  user: null,
  room: null,
  lastEffect: null,
};

const authPanel = document.getElementById("authPanel");
const gamePanel = document.getElementById("gamePanel");
const heroBadge = document.getElementById("heroBadge");
const toast = document.getElementById("toast");
const profileCard = document.getElementById("profileCard");
const roomCard = document.getElementById("roomCard");
const boardStrip = document.getElementById("boardStrip");
const activeCard = document.getElementById("activeCard");
const playersList = document.getElementById("playersList");
const feedList = document.getElementById("feedList");
const spaceEffect = document.getElementById("spaceEffect");

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Etwas ist schiefgelaufen.");
  }
  return data;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.add("hidden"), 2600);
}

function formatAgo(timestamp) {
  if (!timestamp) return "gerade eben";
  const diff = Math.max(0, Math.floor(Date.now() / 1000) - timestamp);
  if (diff < 60) return "gerade eben";
  if (diff < 3600) return `vor ${Math.floor(diff / 60)} min`;
  return `vor ${Math.floor(diff / 3600)} h`;
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
      button.classList.add("active");
      const target = button.dataset.tab;
      document.getElementById("registerForm").classList.toggle("hidden", target !== "register");
      document.getElementById("loginForm").classList.toggle("hidden", target !== "login");
    });
  });
}

function renderProfile() {
  if (!state.user) return;
  profileCard.innerHTML = `
    <div class="profile-summary">
      <div class="level-ring">
        <div>
          <div class="subtle">${state.user.displayName}</div>
          <strong>Level ${state.user.level}</strong>
        </div>
        <div class="subtle">${state.user.xpToNextLevel} XP bis zum naechsten Level</div>
      </div>
      <div class="stats">
        <div class="stat">
          <span>Feld</span>
          <strong>${state.user.position}</strong>
        </div>
        <div class="stat">
          <span>Seiten</span>
          <strong>${state.user.pagesRead}</strong>
        </div>
        <div class="stat">
          <span>Karten</span>
          <strong>${state.user.cardsCompleted}</strong>
        </div>
      </div>
    </div>
  `;
}

function renderRoom() {
  if (!state.room) {
    roomCard.innerHTML = `<p class="subtle">Du bist noch in keinem Raum. Erstelle einen neuen oder trete mit einem Code bei.</p>`;
    return;
  }
  roomCard.innerHTML = `
    <div class="room-card">
      <div>
        <strong>${state.room.name}</strong>
        <div class="subtle">Teile diesen Code mit anderen Accounts</div>
      </div>
      <div class="room-code">${state.room.code}</div>
      <div class="subtle">${state.room.players.length} Spieler:innen im Raum</div>
    </div>
  `;
}

function renderBoard() {
  if (!state.room) {
    boardStrip.innerHTML = `<p class="subtle">Sobald du in einer Lesebande bist, erscheint hier euer Brett.</p>`;
    return;
  }
  const playerMap = new Map();
  state.room.players.forEach((player) => {
    if (!playerMap.has(player.position)) playerMap.set(player.position, []);
    playerMap.get(player.position).push(player);
  });

  boardStrip.innerHTML = state.room.board
    .map((space) => {
      const players = playerMap.get(space.position) || [];
      const isYou = state.user.position === space.position;
      return `
        <article class="board-space ${space.type} ${isYou ? "you" : ""}">
          <div>
            <div class="subtle">Feld ${space.position}</div>
            <h3>${space.label}</h3>
          </div>
          <div class="space-marker">
            ${players.map((player) => `<span class="player-chip">${player.displayName}</span>`).join("")}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderCard() {
  const card = state.user?.currentCard;
  if (!card) {
    activeCard.innerHTML = `
      <div class="active-card empty">
        <p>Keine aktive Karte. Zieh eine neue Aufgabe und bring dein Buch wieder ins Rollen.</p>
      </div>
    `;
  } else {
    activeCard.innerHTML = `
      <div class="active-card">
        <span class="card-tag">${card.tag}</span>
        <h3>${card.title}</h3>
        <p>${card.description}</p>
        <div class="reward-row">
          <span>${card.pages} Seiten</span>
          <span>+${card.xpReward} XP</span>
          <span>+${card.stepsReward} Felder</span>
        </div>
      </div>
    `;
  }

  const effect = state.lastEffect;
  spaceEffect.innerHTML = effect
    ? `<div class="space-effect"><strong>${effect.event.title}</strong><p>${effect.event.description}</p></div>`
    : "";
  heroBadge.textContent = card ? `Aktive Karte: ${card.title}` : "Bereit fuer die naechste Karte";
}

function renderPlayers() {
  if (!state.room) {
    playersList.innerHTML = `<p class="subtle">Hier taucht eure Rangliste auf.</p>`;
    return;
  }
  playersList.innerHTML = state.room.players
    .map(
      (player, index) => `
        <article class="player-row ${player.id === state.user.id ? "you" : ""}">
          <div>
            <strong>#${index + 1} ${player.displayName}</strong>
            <div class="subtle">@${player.username} · Level ${player.level}</div>
          </div>
          <div class="subtle">Feld ${player.position} · ${player.pagesRead} Seiten</div>
        </article>
      `,
    )
    .join("");
}

function renderFeed() {
  if (!state.room) {
    feedList.innerHTML = `<p class="subtle">Noch kein Feed, weil noch kein Raum aktiv ist.</p>`;
    return;
  }
  feedList.innerHTML = state.room.feed
    .map(
      (item) => `
        <article class="feed-item">
          <strong>${item.message}</strong>
          <div class="subtle">${formatAgo(item.createdAt)}</div>
        </article>
      `,
    )
    .join("");
}

function render() {
  const authenticated = Boolean(state.user);
  authPanel.classList.toggle("hidden", authenticated);
  gamePanel.classList.toggle("hidden", !authenticated);
  renderProfile();
  renderRoom();
  renderBoard();
  renderCard();
  renderPlayers();
  renderFeed();
}

async function refreshState() {
  const data = await api("/api/bootstrap", { method: "GET" });
  if (!data.authenticated) {
    state.user = null;
    state.room = null;
    state.lastEffect = null;
    render();
    return;
  }
  state.user = data.user;
  state.room = data.room || null;
  render();
}

async function handleAuth(form, endpoint) {
  const payload = Object.fromEntries(new FormData(form).entries());
  const data = await api(endpoint, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.user = data.user;
  showToast(endpoint.includes("register") ? "Konto erstellt." : "Eingeloggt.");
  form.reset();
  await refreshState();
}

document.getElementById("registerForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await handleAuth(event.currentTarget, "/api/register");
  } catch (error) {
    showToast(error.message);
  }
});

document.getElementById("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await handleAuth(event.currentTarget, "/api/login");
  } catch (error) {
    showToast(error.message);
  }
});

document.getElementById("logoutButton").addEventListener("click", async () => {
  try {
    await api("/api/logout", { method: "POST", body: "{}" });
    state.user = null;
    state.room = null;
    state.lastEffect = null;
    render();
    showToast("Du bist ausgeloggt.");
  } catch (error) {
    showToast(error.message);
  }
});

document.getElementById("createRoomForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    await api("/api/rooms/create", { method: "POST", body: JSON.stringify(payload) });
    showToast("Neuer Raum erstellt.");
    event.currentTarget.reset();
    await refreshState();
  } catch (error) {
    showToast(error.message);
  }
});

document.getElementById("joinRoomForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    await api("/api/rooms/join", { method: "POST", body: JSON.stringify(payload) });
    showToast("Raum beigetreten.");
    event.currentTarget.reset();
    await refreshState();
  } catch (error) {
    showToast(error.message);
  }
});

document.getElementById("drawButton").addEventListener("click", async () => {
  try {
    await api("/api/cards/draw", { method: "POST", body: "{}" });
    state.lastEffect = null;
    await refreshState();
    showToast("Neue Karte gezogen.");
  } catch (error) {
    showToast(error.message);
  }
});

document.getElementById("completeButton").addEventListener("click", async () => {
  try {
    const data = await api("/api/cards/complete", { method: "POST", body: "{}" });
    state.lastEffect = data.spaceEffect;
    showToast(`Karte geschafft: ${data.completedCard.title}`);
    await refreshState();
  } catch (error) {
    showToast(error.message);
  }
});

bindTabs();
refreshState();
window.setInterval(refreshState, 12000);
