import type {
  BackendEnvelope,
  ConfigData,
  DashboardData,
  FilterKind,
  ListData,
  ListTracksRequest,
  MonthlyTopData,
  SyncData,
  TopListenRequest,
} from "../shared/contracts.js";

const statusBadge = document.querySelector<HTMLSpanElement>("#status-badge");
const statusMessage = document.querySelector<HTMLParagraphElement>("#status-message");
const refreshConfigButton = document.querySelector<HTMLButtonElement>("#refresh-config");
const runSyncButton = document.querySelector<HTMLButtonElement>("#run-sync");
const dashboardButton = document.querySelector<HTMLButtonElement>("#dashboard-load");
const listSubmitButton = document.querySelector<HTMLButtonElement>("#list-submit");
const monthlyTopButton = document.querySelector<HTMLButtonElement>("#monthly-top-load");
const configDetails = document.querySelector<HTMLElement>("#config-details");
const syncSummary = document.querySelector<HTMLElement>("#sync-summary");
const dashboardEmpty = document.querySelector<HTMLElement>("#dashboard-empty");
const dashboardPath = document.querySelector<HTMLElement>("#dashboard-path");
const dashboardSummary = document.querySelector<HTMLElement>("#dashboard-summary");
const dashboardTopTags = document.querySelector<HTMLUListElement>("#dashboard-top-tags");
const dashboardTopArtists = document.querySelector<HTMLUListElement>("#dashboard-top-artists");
const listForm = document.querySelector<HTMLFormElement>("#list-form");
const filterKind = document.querySelector<HTMLSelectElement>("#filter-kind");
const filterValue = document.querySelector<HTMLInputElement>("#filter-value");
const listEmpty = document.querySelector<HTMLElement>("#list-empty");
const trackResults = document.querySelector<HTMLUListElement>("#track-results");
const monthlyTopEmpty = document.querySelector<HTMLElement>("#monthly-top-empty");
const mostPlayedResults = document.querySelector<HTMLUListElement>("#most-played-results");
const leastPlayedResults = document.querySelector<HTMLUListElement>("#least-played-results");

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
  if (dashboardButton) {
    dashboardButton.disabled = isBusy;
  }
  if (listSubmitButton) {
    listSubmitButton.disabled = isBusy;
  }
  if (monthlyTopButton) {
    monthlyTopButton.disabled = isBusy;
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
    ["Added", summary.added],
    ["Unchanged", summary.unchanged],
    ["Archived", summary.archived],
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

function renderMonthlyTopList(
  target: HTMLUListElement | null,
  entries: MonthlyTopData["mostPlayed"],
): void {
  if (!target) {
    return;
  }

  target.innerHTML = "";

  for (const entry of entries) {
    const item = document.createElement("li");
    item.innerHTML = `
      <span class="track-title">${escapeHtml(entry.title)}</span>
      <span class="track-artists">${escapeHtml(entry.artists.join(", ") || "Unknown Artist")}</span>
      <span class="track-meta">${escapeHtml(`Monthly listens: ${entry.monthlyListens} | Like position: ${entry.position}`)}</span>
    `;
    target.appendChild(item);
  }
}

function renderMonthlyTop(data: MonthlyTopData): void {
  renderMonthlyTopList(mostPlayedResults, data.mostPlayed);
  renderMonthlyTopList(leastPlayedResults, data.leastPlayed);

  if (!monthlyTopEmpty) {
    return;
  }

  if (data.mostPlayed.length === 0 && data.leastPlayed.length === 0) {
    monthlyTopEmpty.textContent = "No liked tracks available for the monthly top report.";
    return;
  }

  monthlyTopEmpty.textContent = `Loaded ${data.mostPlayed.length} most-played and ${data.leastPlayed.length} least-played tracks.`;
}

function renderDashboardStatList(
  target: HTMLUListElement | null,
  items: string[],
): void {
  if (!target) {
    return;
  }

  target.innerHTML = "";
  for (const itemText of items) {
    const item = document.createElement("li");
    item.innerHTML = `<span class="track-title">${escapeHtml(itemText)}</span>`;
    target.appendChild(item);
  }
}

function renderDashboard(data: DashboardData): void {
  if (dashboardPath) {
    dashboardPath.textContent = data.path;
  }

  if (dashboardSummary) {
    const { summary } = data;
    dashboardSummary.innerHTML = [
      ["Liked tracks", summary.likedTracks],
      ["Removed tracks", summary.removedTracks],
      ["Total tracks", summary.totalTracks],
      ["Total duration", summary.totalDuration],
      ["Known monthly listens", summary.monthlyListensKnown],
      ["Coverage", `${summary.monthlyListensCoveragePercent.toFixed(2)}%`],
      [
        "Average monthly listens",
        summary.averageMonthlyListens === null ? "-" : summary.averageMonthlyListens.toFixed(2),
      ],
      [
        "Median monthly listens",
        summary.medianMonthlyListens === null ? "-" : summary.medianMonthlyListens.toFixed(2),
      ],
      [
        "Most listened track",
        summary.mostListenedTrack
          ? `${summary.mostListenedTrack.title} - ${summary.mostListenedTrack.artists.join(", ") || "Unknown Artist"} (${summary.mostListenedTrack.monthlyListens})`
          : "-",
      ],
      [
        "Most listened artist",
        summary.mostListenedArtist
          ? `${summary.mostListenedArtist.name} (${summary.mostListenedArtist.monthlyListens} listens, ${summary.mostListenedArtist.tracks} track${summary.mostListenedArtist.tracks === 1 ? "" : "s"})`
          : "-",
      ],
      [
        "Most used tag",
        summary.mostUsedTag
          ? `${summary.mostUsedTag.name} (${summary.mostUsedTag.tracks} track${summary.mostUsedTag.tracks === 1 ? "" : "s"})`
          : "-",
      ],
      [
        "Longest track",
        summary.longestTrack
          ? `${summary.longestTrack.title} - ${summary.longestTrack.artists.join(", ") || "Unknown Artist"} (${summary.longestTrack.duration})`
          : "-",
      ],
    ]
      .map(
        ([label, value]) =>
          `<div><dt>${escapeHtml(String(label))}</dt><dd>${escapeHtml(String(value))}</dd></div>`,
      )
      .join("");
  }

  renderDashboardStatList(
    dashboardTopTags,
    data.topTags.map((entry) => `${entry.name} (${entry.tracks} track${entry.tracks === 1 ? "" : "s"})`),
  );
  renderDashboardStatList(
    dashboardTopArtists,
    data.topArtists.map(
      (entry) =>
        `${entry.name} (${entry.monthlyListens} listens, ${entry.tracks} track${entry.tracks === 1 ? "" : "s"})`,
    ),
  );

  if (dashboardEmpty) {
    dashboardEmpty.textContent = `Loaded dashboard for ${data.summary.totalTracks} known track(s).`;
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
    updateStatus("success", "Synced", `Added ${result.data.summary.added} tracks.`);
  } else {
    updateStatus("error", "Sync Error", errorSummary(result));
  }

  setBusy(false);
}

async function loadDashboard(): Promise<void> {
  setBusy(true);
  updateStatus("busy", "Dashboard", "Loading the local dashboard from the Python backend.");

  const result = await window.musicSync.getDashboard();
  if (result.ok) {
    renderDashboard(result.data);
    updateStatus("success", "Dashboard", "Dashboard loaded from local vault data.");
  } else {
    if (dashboardEmpty) {
      dashboardEmpty.textContent = "Dashboard request failed.";
    }
    if (dashboardPath) {
      dashboardPath.textContent = "";
    }
    if (dashboardSummary) {
      dashboardSummary.innerHTML = "";
    }
    if (dashboardTopTags) {
      dashboardTopTags.innerHTML = "";
    }
    if (dashboardTopArtists) {
      dashboardTopArtists.innerHTML = "";
    }
    updateStatus("error", "Dashboard Error", errorSummary(result));
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

async function loadMonthlyTop(): Promise<void> {
  setBusy(true);
  updateStatus("busy", "Ranking", "Loading monthly listening leaders from the Python backend.");

  const mostRequest: TopListenRequest = { mode: "most" };
  const leastRequest: TopListenRequest = { mode: "least" };
  const [mostResult, leastResult] = await Promise.all([
    window.musicSync.getTopListen(mostRequest),
    window.musicSync.getTopListen(leastRequest),
  ]);

  if (mostResult.ok && leastResult.ok) {
    renderMonthlyTop({
      mostPlayed: mostResult.data.mostPlayed,
      leastPlayed: leastResult.data.leastPlayed,
    });
    updateStatus("success", "Ranked", "Monthly top report loaded from the Python backend.");
  } else {
    if (monthlyTopEmpty) {
      monthlyTopEmpty.textContent = "Monthly top request failed.";
    }
    if (mostPlayedResults) {
      mostPlayedResults.innerHTML = "";
    }
    if (leastPlayedResults) {
      leastPlayedResults.innerHTML = "";
    }
    updateStatus(
      "error",
      "Ranking Error",
      errorSummary(mostResult.ok ? leastResult : mostResult),
    );
  }

  setBusy(false);
}

refreshConfigButton?.addEventListener("click", () => {
  void loadConfig();
});

runSyncButton?.addEventListener("click", () => {
  void runSync();
});

dashboardButton?.addEventListener("click", () => {
  void loadDashboard();
});

listForm?.addEventListener("submit", (event) => {
  void handleList(event);
});

monthlyTopButton?.addEventListener("click", () => {
  void loadMonthlyTop();
});

void loadConfig();
