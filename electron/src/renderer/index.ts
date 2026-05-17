import type {
  BackendEnvelope,
  ConfigData,
  DiscoveryData,
  DiscoveryRequest,
  DashboardData,
  FilterKind,
  ListData,
  ListTracksRequest,
  MonthlyTopData,
  RecommendationData,
  RecommendationRequest,
  SyncData,
  TopListenRequest,
  VaultData,
  VaultRequest,
  VaultTreeNode,
} from "../shared/contracts.js";

const statusBadge = document.querySelector<HTMLSpanElement>("#status-badge");
const statusMessage = document.querySelector<HTMLParagraphElement>("#status-message");
const refreshConfigButton = document.querySelector<HTMLButtonElement>("#refresh-config");
const runSyncButton = document.querySelector<HTMLButtonElement>("#run-sync");
const dashboardButton = document.querySelector<HTMLButtonElement>("#dashboard-load");
const dashboardInlineButton = document.querySelector<HTMLButtonElement>("#dashboard-load-inline");
const listSubmitButton = document.querySelector<HTMLButtonElement>("#list-submit");
const monthlyTopButton = document.querySelector<HTMLButtonElement>("#monthly-top-load");
const vaultLoadButton = document.querySelector<HTMLButtonElement>("#vault-load");
const discoveryLoadButton = document.querySelector<HTMLButtonElement>("#discovery-load");
const discoveryClearButton = document.querySelector<HTMLButtonElement>("#discovery-clear");
const discoveryEmpty = document.querySelector<HTMLElement>("#discovery-empty");
const discoveryResults = document.querySelector<HTMLUListElement>("#discovery-results");
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
const vaultEmpty = document.querySelector<HTMLElement>("#vault-empty");
const vaultPath = document.querySelector<HTMLElement>("#vault-path");
const vaultTree = document.querySelector<HTMLElement>("#vault-tree");
const vaultPreview = document.querySelector<HTMLElement>("#vault-preview");
const vaultPreviewMeta = document.querySelector<HTMLElement>("#vault-preview-meta");
const monthlyTopEmpty = document.querySelector<HTMLElement>("#monthly-top-empty");
const mostPlayedResults = document.querySelector<HTMLUListElement>("#most-played-results");
const leastPlayedResults = document.querySelector<HTMLUListElement>("#least-played-results");
const recommendButton = document.querySelector<HTMLButtonElement>("#recommend-load");
const recommendArchived = document.querySelector<HTMLInputElement>("#recommend-archived");
const recommendEmpty = document.querySelector<HTMLElement>("#recommend-empty");
const recommendResults = document.querySelector<HTMLUListElement>("#recommend-results");

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
  if (dashboardInlineButton) {
    dashboardInlineButton.disabled = isBusy;
  }
  if (listSubmitButton) {
    listSubmitButton.disabled = isBusy;
  }
  if (monthlyTopButton) {
    monthlyTopButton.disabled = isBusy;
  }
  if (vaultLoadButton) {
    vaultLoadButton.disabled = isBusy;
  }
  if (recommendButton) {
    recommendButton.disabled = isBusy;
  }
  if (discoveryLoadButton) {
    discoveryLoadButton.disabled = isBusy;
  }
  if (discoveryClearButton) {
    discoveryClearButton.disabled = isBusy;
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

function renderVaultTreeNode(node: VaultTreeNode, selectedPath: string | null): HTMLElement {
  if (node.kind === "file") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `vault-file-button${selectedPath === node.path ? " vault-file-button-active" : ""}`;
    button.textContent = node.name;
    button.addEventListener("click", () => {
      void loadVault(node.path);
    });
    return button;
  }

  const details = document.createElement("details");
  details.open = true;
  const summary = document.createElement("summary");
  summary.textContent = node.name;
  details.appendChild(summary);

  const children = document.createElement("div");
  children.className = "vault-tree-children";
  for (const child of node.children ?? []) {
    children.appendChild(renderVaultTreeNode(child, selectedPath));
  }
  details.appendChild(children);
  return details;
}

function renderMarkdownInline(text: string): string {
  let rendered = escapeHtml(text);
  rendered = rendered.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_match, alt: string, url: string) => {
    const safeUrl = sanitizeUrl(url);
    if (safeUrl === null) {
      return escapeHtml(`![${alt}](${url})`);
    }
    return `<img alt="${alt}" src="${safeUrl}" />`;
  });
  rendered = rendered.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_match, label: string, url: string) => {
    const safeUrl = sanitizeUrl(url);
    if (safeUrl === null) {
      return escapeHtml(`[${label}](${url})`);
    }
    return `<a href="${safeUrl}" target="_blank" rel="noreferrer">${label}</a>`;
  });
  rendered = rendered.replace(/`([^`]+)`/g, "<code>$1</code>");
  rendered = rendered.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  rendered = rendered.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return rendered;
}

function renderMarkdown(content: string): string {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const html: string[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index] ?? "";

    if (line.trim() === "") {
      index += 1;
      continue;
    }

    if (line.startsWith("```")) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !(lines[index] ?? "").startsWith("```")) {
        codeLines.push(lines[index] ?? "");
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      html.push(`<h${level}>${renderMarkdownInline(heading[2])}</h${level}>`);
      index += 1;
      continue;
    }

    if (line.startsWith("> ")) {
      const quoteLines: string[] = [];
      while (index < lines.length && (lines[index] ?? "").startsWith("> ")) {
        quoteLines.push((lines[index] ?? "").slice(2));
        index += 1;
      }
      html.push(`<blockquote>${quoteLines.map((entry) => renderMarkdownInline(entry)).join("<br />")}</blockquote>`);
      continue;
    }

    if (line.match(/^\s*-\s+/)) {
      const items: string[] = [];
      while (index < lines.length && (lines[index] ?? "").match(/^\s*-\s+/)) {
        items.push((lines[index] ?? "").replace(/^\s*-\s+/, ""));
        index += 1;
      }
      html.push(`<ul>${items.map((item) => `<li>${renderMarkdownInline(item)}</li>`).join("")}</ul>`);
      continue;
    }

    const paragraphLines: string[] = [];
    while (index < lines.length) {
      const candidate = lines[index] ?? "";
      if (
        candidate.trim() === "" ||
        candidate.startsWith("```") ||
        candidate.startsWith("> ") ||
        candidate.match(/^\s*-\s+/) ||
        candidate.match(/^#{1,3}\s+/)
      ) {
        break;
      }
      paragraphLines.push(candidate);
      index += 1;
    }
    html.push(`<p>${renderMarkdownInline(paragraphLines.join(" "))}</p>`);
  }

  return html.join("");
}

function renderVault(data: VaultData): void {
  if (vaultPath) {
    vaultPath.textContent = data.vaultPath;
  }
  if (vaultTree) {
    vaultTree.innerHTML = "";
    for (const node of data.tree) {
      vaultTree.appendChild(renderVaultTreeNode(node, data.selectedPath));
    }
  }
  if (vaultPreviewMeta) {
    vaultPreviewMeta.textContent = data.selectedNote ? data.selectedNote.path : "";
  }
  if (vaultPreview) {
    if (data.selectedNote) {
      vaultPreview.classList.remove("empty-state");
      vaultPreview.innerHTML = renderMarkdown(data.selectedNote.content);
    } else {
      vaultPreview.classList.add("empty-state");
      vaultPreview.textContent = "Select a note to preview it here.";
    }
  }
  if (vaultEmpty) {
    if (data.tree.length === 0) {
      vaultEmpty.textContent = "Managed vault folders are available, but there are no browsable Markdown notes yet.";
    } else if (data.selectedNote) {
      vaultEmpty.textContent = `Loaded vault view for ${data.vaultPath}.`;
    } else {
      vaultEmpty.textContent = "Vault loaded. Select a note from the tree to preview it.";
    }
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

function renderRecommendations(data: RecommendationData): void {
  if (!recommendResults || !recommendEmpty) {
    return;
  }

  recommendResults.innerHTML = "";
  if (data.recommendations.length === 0) {
    recommendEmpty.textContent = "No recommendations found for the current local taste profile.";
    return;
  }

  recommendEmpty.textContent = `Loaded ${data.recommendations.length} recommendation(s).`;
  for (const entry of data.recommendations) {
    const item = document.createElement("li");
    item.innerHTML = `
      <span class="track-title">${escapeHtml(entry.title)}</span>
      <span class="track-artists">${escapeHtml(entry.artists.join(", ") || "Unknown Artist")}</span>
      <span class="track-meta">${escapeHtml(`Monthly listens: ${entry.monthlyListens === null ? "-" : entry.monthlyListens} | Archived: ${entry.archived ? "yes" : "no"}`)}</span>
      <span class="track-meta">${escapeHtml(entry.explain)}</span>
    `;
    recommendResults.appendChild(item);
  }
}

function renderDiscovery(data: DiscoveryData, cleared: boolean): void {
  if (!discoveryResults || !discoveryEmpty) {
    return;
  }

  discoveryResults.innerHTML = "";
  if (cleared) {
    discoveryEmpty.textContent = `Cleared ${data.summary.cleared} recommendation(s).`;
    return;
  }

  if (data.recommendations.length === 0) {
    discoveryEmpty.textContent = "No discovery recommendations found for the current taste profile.";
    return;
  }

  discoveryEmpty.textContent = `Loaded ${data.recommendations.length} discovery recommendation(s).`;
  for (const entry of data.recommendations) {
    const item = document.createElement("li");
    item.innerHTML = `
      <span class="track-title">${escapeHtml(entry.title)}</span>
      <span class="track-artists">${escapeHtml(entry.artists.join(", ") || "Unknown Artist")}</span>
      <span class="track-meta">${escapeHtml(`Monthly listens: ${entry.monthlyListens === null ? "-" : entry.monthlyListens} | Sources: ${entry.explain}`)}</span>
    `;
    discoveryResults.appendChild(item);
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

function sanitizeUrl(value: string): string | null {
  try {
    const url = new URL(value);
    if (url.protocol === "http:" || url.protocol === "https:") {
      return escapeHtml(url.toString());
    }
  } catch {
    return null;
  }

  return null;
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

async function loadVault(selectedPath?: string): Promise<void> {
  const request: VaultRequest = {};
  if (selectedPath) {
    request.selectedPath = selectedPath;
  }

  setBusy(true);
  updateStatus("busy", "Vault", "Loading the managed vault tree from the Python backend.");

  const result = await window.musicSync.getVaultView(request);
  if (result.ok) {
    renderVault(result.data);
    updateStatus("success", "Vault", "Vault browser loaded from local note data.");
  } else {
    if (vaultEmpty) {
      vaultEmpty.textContent = "Vault request failed.";
    }
    if (vaultPreview) {
      vaultPreview.classList.add("empty-state");
      vaultPreview.textContent = "Unable to preview the selected note.";
    }
    if (vaultPreviewMeta) {
      vaultPreviewMeta.textContent = "";
    }
    updateStatus("error", "Vault Error", errorSummary(result));
  }

  setBusy(false);
}

async function loadRecommendations(): Promise<void> {
  const request: RecommendationRequest = {
    archived: Boolean(recommendArchived?.checked),
  };

  setBusy(true);
  updateStatus("busy", "Recommend", "Loading local re-listen recommendations from the Python backend.");

  const result = await window.musicSync.getRecommendations(request);
  if (result.ok) {
    renderRecommendations(result.data);
    updateStatus("success", "Recommend", "Recommendation report loaded from local vault data.");
  } else {
    if (recommendEmpty) {
      recommendEmpty.textContent = "Recommendation request failed.";
    }
    if (recommendResults) {
      recommendResults.innerHTML = "";
    }
    updateStatus("error", "Recommend Error", errorSummary(result));
  }

  setBusy(false);
}

async function loadDiscovery(clear: boolean): Promise<void> {
  const request: DiscoveryRequest = { clear };

  setBusy(true);
  updateStatus(
    "busy",
    clear ? "Clearing" : "Discovery",
    clear
      ? "Clearing saved discovery recommendations from the Python backend."
      : "Loading discovery recommendations from the Python backend.",
  );

  const result = await window.musicSync.getDiscoveryRecommendations(request);
  if (result.ok) {
    renderDiscovery(result.data, clear);
    updateStatus(
      "success",
      clear ? "Cleared" : "Discovery",
      clear
        ? "Discovery recommendations cleared."
        : "Discovery recommendations loaded from the Python backend.",
    );
  } else {
    if (discoveryEmpty) {
      discoveryEmpty.textContent = clear ? "Discovery clear request failed." : "Discovery request failed.";
    }
    if (discoveryResults) {
      discoveryResults.innerHTML = "";
    }
    updateStatus("error", "Discovery Error", errorSummary(result));
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

dashboardInlineButton?.addEventListener("click", () => {
  void loadDashboard();
});

listForm?.addEventListener("submit", (event) => {
  void handleList(event);
});

monthlyTopButton?.addEventListener("click", () => {
  void loadMonthlyTop();
});

vaultLoadButton?.addEventListener("click", () => {
  void loadVault();
});

recommendButton?.addEventListener("click", () => {
  void loadRecommendations();
});

discoveryLoadButton?.addEventListener("click", () => {
  void loadDiscovery(false);
});

discoveryClearButton?.addEventListener("click", () => {
  void loadDiscovery(true);
});

void loadConfig();
