async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function setPill(el, kind, text) {
  el.className = `pill ${kind}`;
  el.innerHTML = `<i class="dot"></i> ${text}`;
}

async function refreshStatus() {
  const apiRow = document.querySelector("#status-grid .status-row:first-child strong");
  const dbPill = document.getElementById("db-pill");
  const version = document.getElementById("version");
  const areasCount = document.getElementById("areas-count");

  try {
    const health = await fetchJson("/api/health");
    setPill(apiRow, "ok", health.status || "ok");
    const db = String(health.database || "unknown").toLowerCase();
    if (db.includes("ok") || db.includes("connected") || db === "up") {
      setPill(dbPill, "ok", health.database);
    } else if (db.includes("unavail") || db.includes("down") || db.includes("error")) {
      setPill(dbPill, "warn", health.database);
    } else {
      setPill(dbPill, "warn", health.database);
    }
    version.textContent = health.version || "0.1.0";
  } catch (err) {
    setPill(apiRow, "bad", "offline");
    setPill(dbPill, "bad", "unknown");
    version.textContent = "—";
  }

  try {
    const areas = await fetchJson("/api/study-areas");
    areasCount.textContent = `${areas.areas?.length ?? 0} areas`;
  } catch {
    areasCount.textContent = "—";
  }
}

function tickClock() {
  const el = document.getElementById("clock");
  if (!el) return;
  el.textContent = new Date().toLocaleString("fa-IR");
}

refreshStatus();
tickClock();
setInterval(refreshStatus, 15000);
setInterval(tickClock, 1000);
