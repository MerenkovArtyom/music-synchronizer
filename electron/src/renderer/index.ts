import type {
  BackendEnvelope,
  ConfigData,
  FilterKind,
  ListData,
  ListTracksRequest,
  SyncData,
} from "../shared/contracts.js";

const statusBadge = document.querySelector<HTMLSpanElement>("#status-badge");
const statusMessage = document.querySelector<HTMLParagraphElement>("#status-message");
const refreshConfigButton = document.querySelector<HTMLButtonElement>("#refresh-config");
const runSyncButton = document.querySelector<HTMLButtonElement>("#run-sync");
const listSubmitButton = document.querySelector<HTMLButtonElement>("#list-submit");
const configDetails = document.querySelector<HTMLElement>("#config-details");
const syncSummary = document.querySelector<HTMLElement>("#sync-summary");
const listForm = document.querySelector<HTMLFormElement>("#list-form");
const filterKind = document.querySelector<HTMLSelectElement>("#filter-kind");
const filterValue = document.querySelector<HTMLInputElement>("#filter-value");
const listEmpty = document.querySelector<HTMLElement>("#list-empty");
const trackResults = document.querySelector<HTMLUListElement>("#track-results");

function updateStatus(
  state: "idle" | "busy" | "success" | "error",
  badgeText: string,
  message: string,
): void {
  if (!statusBadge || !statusMessage) {
    return;
  }

  statusBadge.textContent = badgeText;
  statusBadge.className = `badge badge-${state}`;
  statusMessage.textContent = message;
}

function setBusy(isBusy: boolean): void {
  if (refreshConfigButton) {
    refreshConfigButton.disabled = isBusy;
  }
  if (runSyncButton) {
    runSyncButton.disabled = isBusy;
  }
  if (listSubmitButton) {
    listSubmitButton.disabled = isBusy;
  }
}

function setConfigDetails(data: ConfigData["config"]): void {
  if (!configDetails) {
    return;
  }

  configDetails.innerHTML = [
    ["Token", data.yandexMusicTokenPresent ? "Present" : "Missing"],
    ["Vault", data.obsidianVaultPath],
    ["Log level", data.logLevel],
  ]
    .map(
      ([label, value]) =>
        `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(String(value))}</dd></div>`,
    )
    .join("");
}

function setSyncSummary(summary: SyncData["summary"]): void {
  if (!syncSummary) {
    return;
  }

  syncSummary.innerHTML = [
    ["Fetched", summary.fetched],
    ["Written", summary.written],
    ["Archived", summary.archived],
    ["Restored", summary.restored],
    ["Removed", summary.removed],
  ]
    .map(
      ([label, value]) =>
        `<div><dt>${escapeHtml(String(label))}</dt><dd>${escapeHtml(String(value))}</dd></div>`,
    )
    .join("");
}

function renderTracks(data: ListData): void {
  if (!trackResults || !listEmpty) {
    return;
  }

  trackResults.innerHTML = "";

  if (data.tracks.length === 0) {
    listEmpty.textContent = `No active tracks found for ${data.filter.kind} "${data.filter.value}".`;
    return;
  }

  listEmpty.textContent = `${data.tracks.length} active track(s) matched ${data.filter.kind} "${data.filter.value}".`;
  for (const track of data.tracks) {
    const item = document.createElement("li");
    item.innerHTML = `
      <span class="track-title">${escapeHtml(track.title)}</span>
      <span class="track-artists">${escapeHtml(track.artists.join(", ") || "Unknown Artist")}</span>
    `;
    trackResults.appendChild(item);
  }
}

function errorSummary<T>(result: BackendEnvelope<T>): string {
  if (result.ok) {
    return "Unexpected success result.";
  }

  return `${result.error.code}: ${result.error.message}`;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function loadConfig(): Promise<void> {
  setBusy(true);
  updateStatus("busy", "Loading", "Reading Python backend configuration.");

  const result = await window.musicSync.showConfig();
  if (result.ok) {
    setConfigDetails(result.data.config);
    updateStatus("success", "Ready", "Configuration loaded from the Python backend.");
  } else {
    updateStatus("error", "Config Error", errorSummary(result));
  }

  setBusy(false);
}

async function runSync(): Promise<void> {
  setBusy(true);
  updateStatus("busy", "Syncing", "Running synchronization through the Python backend.");

  const result = await window.musicSync.runSync();
  if (result.ok) {
    setSyncSummary(result.data.summary);
    updateStatus("success", "Synced", `Fetched ${result.data.summary.fetched} tracks.`);
  } else {
    updateStatus("error", "Sync Error", errorSummary(result));
  }

  setBusy(false);
}

async function handleList(event: SubmitEvent): Promise<void> {
  event.preventDefault();

  if (!filterKind || !filterValue) {
    return;
  }

  const request: ListTracksRequest = {
    kind: filterKind.value as FilterKind,
    value: filterValue.value.trim(),
  };

  setBusy(true);
  updateStatus("busy", "Listing", "Querying active notes through the Python backend.");

  const result = await window.musicSync.listTracks(request);
  if (result.ok) {
    renderTracks(result.data);
    updateStatus("success", "Listed", `Loaded ${result.data.tracks.length} track result(s).`);
  } else {
    if (listEmpty) {
      listEmpty.textContent = "List request failed.";
    }
    if (trackResults) {
      trackResults.innerHTML = "";
    }
    updateStatus("error", "List Error", errorSummary(result));
  }

  setBusy(false);
}

refreshConfigButton?.addEventListener("click", () => {
  void loadConfig();
});

runSyncButton?.addEventListener("click", () => {
  void runSync();
});

listForm?.addEventListener("submit", (event) => {
  void handleList(event);
});

void loadConfig();
