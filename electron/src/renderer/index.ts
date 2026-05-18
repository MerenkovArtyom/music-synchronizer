import type { BackendEnvelope, DiscoveryData, ListData, RecommendationData, SyncData, VaultData } from "../shared/contracts.js";
import {
  createRendererController,
  type AppSection,
  type DashboardView,
  type DiscoveryView,
  type RendererState,
  sectionLayoutMode,
  type TrackView,
} from "./shell-controller.js";

const appShell = document.querySelector<HTMLElement>(".app-shell");
const statusBadge = document.querySelector<HTMLSpanElement>("#status-badge");
const statusMessage = document.querySelector<HTMLParagraphElement>("#status-message");
const navItems = Array.from(document.querySelectorAll<HTMLButtonElement>("[data-section]"));
const listKicker = document.querySelector<HTMLElement>("#list-kicker");
const listHeading = document.querySelector<HTMLElement>("#list-heading");
const listSubtitle = document.querySelector<HTMLElement>("#list-subtitle");
const listEmpty = document.querySelector<HTMLElement>("#list-empty");
const listContent = document.querySelector<HTMLElement>("#list-content");
const viewerPlaceholder = document.querySelector<HTMLElement>("#viewer-placeholder");
const placeholderTitle = document.querySelector<HTMLElement>("#placeholder-title");
const placeholderBody = document.querySelector<HTMLElement>("#placeholder-body");
const metaPlaceholder = document.querySelector<HTMLElement>("#meta-placeholder");

const homeView = document.querySelector<HTMLElement>("#home-view");
const homeSyncButton = document.querySelector<HTMLButtonElement>("#home-sync-button");
const homeRecommendButton = document.querySelector<HTMLButtonElement>("#home-recommend-button");
const homeDiscoveryButton = document.querySelector<HTMLButtonElement>("#home-discovery-button");
const homeDiscoveryClearButton = document.querySelector<HTMLButtonElement>("#home-discovery-clear-button");
const homeListForm = document.querySelector<HTMLFormElement>("#home-list-form");
const homeListKind = document.querySelector<HTMLSelectElement>("#home-list-kind");
const homeListValue = document.querySelector<HTMLInputElement>("#home-list-value");
const homeSyncSummary = document.querySelector<HTMLElement>("#home-sync-summary");
const homeRecommendationsList = document.querySelector<HTMLElement>("#home-recommendations-list");
const homeDiscoverySummary = document.querySelector<HTMLElement>("#home-discovery-summary");
const homeListResult = document.querySelector<HTMLElement>("#home-list-result");

const dashboardView = document.querySelector<HTMLElement>("#dashboard-view");
const dashboardTab = document.querySelector<HTMLElement>("#dashboard-tab");
const dashboardTitle = document.querySelector<HTMLElement>("#dashboard-title");
const dashboardNote = document.querySelector<HTMLElement>("#dashboard-note");
const dashboardMeta = document.querySelector<HTMLElement>("#dashboard-meta");
const dashboardMetaList = document.querySelector<HTMLElement>("#dashboard-meta-list");
const dashboardTopTags = document.querySelector<HTMLElement>("#dashboard-top-tags");
const dashboardTopArtists = document.querySelector<HTMLElement>("#dashboard-top-artists");

const songView = document.querySelector<HTMLElement>("#song-view");
const songTab = document.querySelector<HTMLElement>("#song-tab");
const songTitle = document.querySelector<HTMLElement>("#song-title");
const songFacts = document.querySelector<HTMLElement>("#song-facts");
const songLink = document.querySelector<HTMLAnchorElement>("#song-link");
const songCoverFrame = document.querySelector<HTMLElement>("#song-cover-frame");
const songCover = document.querySelector<HTMLImageElement>("#song-cover");
const songNote = document.querySelector<HTMLElement>("#song-note");
const songMeta = document.querySelector<HTMLElement>("#song-meta");
const songMetaList = document.querySelector<HTMLElement>("#song-meta-list");
const songSystemTags = document.querySelector<HTMLElement>("#song-system-tags");
const songUserTags = document.querySelector<HTMLElement>("#song-user-tags");

const recommendationView = document.querySelector<HTMLElement>("#recommendation-view");
const recommendationTab = document.querySelector<HTMLElement>("#recommendation-tab");
const recommendationTitle = document.querySelector<HTMLElement>("#recommendation-title");
const recommendationSubtitle = document.querySelector<HTMLElement>("#recommendation-subtitle");
const recommendationExplain = document.querySelector<HTMLElement>("#recommendation-explain");
const recommendationLink = document.querySelector<HTMLAnchorElement>("#recommendation-link");
const recommendationCoverFrame = document.querySelector<HTMLElement>("#recommendation-cover-frame");
const recommendationCover = document.querySelector<HTMLImageElement>("#recommendation-cover");
const recommendationNote = document.querySelector<HTMLElement>("#recommendation-note");
const recommendationMeta = document.querySelector<HTMLElement>("#recommendation-meta");
const recommendationMetaList = document.querySelector<HTMLElement>("#recommendation-meta-list");
const recommendationSources = document.querySelector<HTMLElement>("#recommendation-sources");
const recommendationTags = document.querySelector<HTMLElement>("#recommendation-tags");

function errorSummary<T>(result: BackendEnvelope<T>): string {
  if (result.ok) {
    return "Unexpected success result.";
  }
  return `${result.error.code}: ${result.error.message}`;
}

function setBusy(isBusy: boolean): void {
  document.body.dataset.busy = String(isBusy);
  for (const navItem of navItems) {
    navItem.disabled = isBusy;
  }
}

function setStatus(tone: "idle" | "loading" | "success" | "placeholder" | "error", badge: string, message: string): void {
  if (statusBadge) {
    statusBadge.textContent = badge;
    statusBadge.className = `status-badge status-${tone}`;
  }
  if (statusMessage) {
    statusMessage.textContent = message;
  }
}

async function expectVaultData(): Promise<VaultData> {
  const result = await window.musicSync.getVaultView({});
  if (!result.ok) {
    throw new Error(errorSummary(result));
  }
  return result.data;
}

async function expectVaultSelection(selectedPath: string): Promise<VaultData> {
  const result = await window.musicSync.getVaultView({ selectedPath });
  if (!result.ok) {
    throw new Error(errorSummary(result));
  }
  return result.data;
}

async function expectRecommendationsVault(request: { selectedPath?: string } = {}): Promise<VaultData> {
  const result = await window.musicSync.getVaultView(request);
  if (!result.ok) {
    throw new Error(errorSummary(result));
  }
  return result.data;
}

async function expectDashboardData() {
  const result = await window.musicSync.getDashboard();
  if (!result.ok) {
    throw new Error(errorSummary(result));
  }
  return result.data;
}

async function expectSyncData(): Promise<SyncData> {
  const result = await window.musicSync.runSync();
  if (!result.ok) {
    throw new Error(errorSummary(result));
  }
  return result.data;
}

async function expectRecommendationData(): Promise<RecommendationData> {
  const result = await window.musicSync.getRecommendations({ archived: false });
  if (!result.ok) {
    throw new Error(errorSummary(result));
  }
  return result.data;
}

async function expectDiscoveryData(clear: boolean): Promise<DiscoveryData> {
  const result = await window.musicSync.getDiscoveryRecommendations({ clear });
  if (!result.ok) {
    throw new Error(errorSummary(result));
  }
  return result.data;
}

async function expectListData(kind: "tag" | "artist", value: string): Promise<ListData> {
  const result = await window.musicSync.listTracks({ kind, value });
  if (!result.ok) {
    throw new Error(errorSummary(result));
  }
  return result.data;
}

const controller = createRendererController({
  getVaultView: async (request) => {
    if (request.selectedPath) {
      return await expectVaultSelection(request.selectedPath);
    }
    return await expectVaultData();
  },
  getRecommendationsVaultView: async (request) => {
    return await expectRecommendationsVault(request);
  },
  getDashboardData: async () => {
    return await expectDashboardData();
  },
  runSync: async () => {
    return await expectSyncData();
  },
  getRecommendations: async () => {
    return await expectRecommendationData();
  },
  getDiscoveryRecommendations: async (request) => {
    return await expectDiscoveryData(request.clear);
  },
  listTracks: async (request) => {
    return await expectListData(request.kind, request.value);
  },
});

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderMarkdownInline(text: string): string {
  let rendered = escapeHtml(text);
  rendered = rendered.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_match, alt: string, url: string) => {
    return `<img alt="${escapeHtml(alt)}" src="${escapeHtml(url)}" />`;
  });
  rendered = rendered.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_match, label: string, url: string) => {
    return `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`;
  });
  rendered = rendered.replace(/`([^`]+)`/g, "<code>$1</code>");
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
    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      html.push(`<h${level}>${renderMarkdownInline(heading[2])}</h${level}>`);
      index += 1;
      continue;
    }
    if (line.startsWith("![")) {
      html.push(`<p>${renderMarkdownInline(line)}</p>`);
      index += 1;
      continue;
    }
    const paragraph: string[] = [];
    while (index < lines.length && (lines[index] ?? "").trim() !== "") {
      paragraph.push(lines[index] ?? "");
      index += 1;
    }
    html.push(`<p>${renderMarkdownInline(paragraph.join(" "))}</p>`);
  }

  return html.join("");
}

function renderFacts(target: HTMLElement | null, rows: Array<[string, string]>): void {
  if (!target) {
    return;
  }
  target.innerHTML = "";
  for (const [label, value] of rows) {
    const row = document.createElement("div");
    row.className = "fact-row";

    const labelNode = document.createElement("span");
    labelNode.className = "fact-label";
    labelNode.textContent = `${label}:`;

    const valueNode = document.createElement("span");
    valueNode.className = "fact-value";
    valueNode.textContent = value;

    row.append(labelNode, valueNode);
    target.appendChild(row);
  }
}

function renderMetaList(target: HTMLElement | null, items: Array<[string, string]>): void {
  if (!target) {
    return;
  }
  target.innerHTML = "";
  for (const [label, value] of items) {
    const row = document.createElement("div");
    row.className = "meta-row";

    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value;

    row.append(term, detail);
    target.appendChild(row);
  }
}

function renderTagList(target: HTMLElement | null, tags: string[], emptyLabel: string): void {
  if (!target) {
    return;
  }
  target.innerHTML = "";
  const values = tags.length > 0 ? tags : [emptyLabel];
  for (const tag of values) {
    const chip = document.createElement("span");
    chip.className = "tag-pill";
    chip.textContent = tags.length > 0 ? `#${tag}` : emptyLabel;
    target.appendChild(chip);
  }
}

function updateCover(frame: HTMLElement | null, image: HTMLImageElement | null, src: string, alt: string): void {
  if (!frame || !image) {
    return;
  }
  const hasImage = src.trim().length > 0 && src !== "—";
  frame.hidden = !hasImage;
  if (hasImage) {
    image.src = src;
    image.alt = alt;
  } else {
    image.removeAttribute("src");
  }
}

function renderSongView(track: TrackView | null): void {
  if (!track || !songView || !songMeta) {
    return;
  }

  if (songTab) {
    songTab.textContent = track.path.split("/").pop() ?? track.title;
  }
  if (songTitle) {
    songTitle.textContent = track.title;
  }

  renderFacts(songFacts, [
    ["Artists", track.artists.join(", ") || "—"],
    ["Album", track.album],
    ["Year", track.year],
    ["Monthly listens (30d)", track.monthlyListens],
    ["Duration", track.duration],
  ]);

  if (songLink) {
    songLink.href = track.yandexUrl || "#";
    songLink.textContent = track.yandexUrl ? "Открыть в Yandex Music" : "Ссылка недоступна";
    songLink.toggleAttribute("aria-disabled", !track.yandexUrl);
  }
  updateCover(songCoverFrame, songCover, track.coverUrl, track.title);
  if (songNote) {
    songNote.innerHTML = renderMarkdown(track.noteBody);
  }

  renderMetaList(songMetaList, [
    ["Артист", track.artists.join(", ") || "—"],
    ["Альбом", track.album],
    ["Год", track.year],
    ["Длительность", track.duration],
    ["Прослушивания (30д)", track.monthlyListens],
    ["Статус", track.archived ? "Архив" : "Активна"],
    ["Track ID", track.trackId],
    ["Путь", track.path],
  ]);
  renderTagList(songSystemTags, track.systemTags, "Нет системных тегов");
  renderTagList(songUserTags, track.userTags, "Нет пользовательских тегов");
}

function renderRecommendationView(view: DiscoveryView | null): void {
  if (!view || !recommendationView || !recommendationMeta) {
    return;
  }

  if (recommendationTab) {
    recommendationTab.textContent = `${view.title}.md`;
  }
  if (recommendationTitle) {
    recommendationTitle.textContent = view.title;
  }
  if (recommendationSubtitle) {
    recommendationSubtitle.textContent = view.artists.join(", ") || "—";
  }
  if (recommendationExplain) {
    recommendationExplain.textContent = view.explain;
  }
  if (recommendationLink) {
    recommendationLink.href = view.yandexUrl || "#";
  }
  updateCover(recommendationCoverFrame, recommendationCover, view.coverUrl, view.title);
  if (recommendationNote) {
    recommendationNote.innerHTML = renderMarkdown(view.noteBody);
  }

  renderMetaList(recommendationMetaList, [
    ["Артист", view.artists.join(", ") || "—"],
    ["Альбом", view.album],
    ["Год", view.year],
    ["Длительность", view.duration],
    ["Прослушивания (30д)", view.monthlyListens],
    ["Track ID", view.id],
  ]);
  renderTagList(recommendationSources, view.sources, "Нет источников");
  renderTagList(recommendationTags, view.systemTags, "Нет тегов");
}

function renderDashboardView(view: DashboardView | null): void {
  if (!view || !dashboardView || !dashboardMeta) {
    return;
  }

  if (dashboardTab) {
    dashboardTab.textContent = view.path.replace(/\.md$/i, "");
  }
  if (dashboardTitle) {
    dashboardTitle.textContent = view.title || "dashboard";
  }
  if (dashboardNote) {
    dashboardNote.innerHTML = renderMarkdown(view.noteBody);
  }

  renderMetaList(dashboardMetaList, [
    ["Лайкнутые треки", String(view.summary.likedTracks)],
    ["Удалённые треки", String(view.summary.removedTracks)],
    ["Всего треков", String(view.summary.totalTracks)],
    ["Общая длительность", view.summary.totalDuration],
    ["Покрытие прослушиваний", `${view.summary.monthlyListensKnown}/${view.summary.likedTracks} (${view.summary.monthlyListensCoveragePercent.toFixed(2)}%)`],
    ["Среднее за месяц", view.summary.averageMonthlyListens === null ? "—" : view.summary.averageMonthlyListens.toFixed(2)],
    ["Медиана за месяц", view.summary.medianMonthlyListens === null ? "—" : view.summary.medianMonthlyListens.toFixed(2)],
  ]);
  renderTagList(
    dashboardTopTags,
    view.topTags.map((entry) => `${entry.name} (${entry.tracks})`),
    "Нет тегов",
  );
  renderTagList(
    dashboardTopArtists,
    view.topArtists.map((entry) => `${entry.name} (${entry.tracks})`),
    "Нет артистов",
  );
}

function renderSongsList(state: RendererState): void {
  if (!listContent || !listEmpty) {
    return;
  }

  const activeItems = state.songItems.filter((item) => !item.archived);
  const archivedItems = state.songItems.filter((item) => item.archived);
  listContent.innerHTML = "";

  if (state.songItems.length === 0) {
    listEmpty.hidden = false;
    listEmpty.textContent = "В папке `tracks/` пока нет заметок.";
    return;
  }

  listEmpty.hidden = true;
  for (const [title, items] of [
    ["Активные", activeItems],
    ["Архив", archivedItems],
  ] as const) {
    if (items.length === 0) {
      continue;
    }
    const group = document.createElement("section");
    group.className = "list-group";

    const header = document.createElement("h3");
    header.className = "list-group-title";
    header.textContent = title;
    group.appendChild(header);

    for (const item of items) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `list-item${item.path === state.selectedSongPath ? " is-selected" : ""}`;
      button.addEventListener("click", () => {
        void selectSong(item.path);
      });

      const label = document.createElement("span");
      label.className = "list-item-title";
      label.textContent = item.label;
      button.appendChild(label);
      group.appendChild(button);
    }

    listContent.appendChild(group);
  }
}

function renderRecommendationsList(state: RendererState): void {
  if (!listContent || !listEmpty) {
    return;
  }

  listContent.innerHTML = "";
  if (state.recommendationItems.length === 0) {
    listEmpty.hidden = false;
    listEmpty.textContent = "Нет доступных рекомендаций.";
    return;
  }

  listEmpty.hidden = true;
  const group = document.createElement("section");
  group.className = "list-group";

  for (const item of state.recommendationItems) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `list-item${item.id === state.selectedRecommendationId ? " is-selected" : ""}`;
    button.addEventListener("click", () => {
      void openRecommendation(item.id);
    });

    const title = document.createElement("span");
    title.className = "list-item-title";
    title.textContent = item.title;
    const subtitle = document.createElement("span");
    subtitle.className = "list-item-subtitle";
    subtitle.textContent = item.subtitle;

    button.append(title, subtitle);
    group.appendChild(button);
  }

  listContent.appendChild(group);
}

function renderSummaryGrid(target: HTMLElement | null, rows: Array<[string, string]>, emptyLabel: string): void {
  if (!target) {
    return;
  }

  target.innerHTML = "";
  if (rows.length === 0) {
    const empty = document.createElement("p");
    empty.className = "result-empty";
    empty.textContent = emptyLabel;
    target.appendChild(empty);
    return;
  }

  for (const [label, value] of rows) {
    const row = document.createElement("div");
    row.className = "summary-item";

    const labelNode = document.createElement("span");
    labelNode.className = "summary-label";
    labelNode.textContent = label;

    const valueNode = document.createElement("strong");
    valueNode.className = "summary-value";
    valueNode.textContent = value;

    row.append(labelNode, valueNode);
    target.appendChild(row);
  }
}

function renderHomeRecommendations(state: RendererState): void {
  if (!homeRecommendationsList) {
    return;
  }

  homeRecommendationsList.innerHTML = "";
  if (state.home.recommendations.length === 0) {
    const empty = document.createElement("p");
    empty.className = "result-empty";
    empty.textContent = "Список рекомендаций пока пуст.";
    homeRecommendationsList.appendChild(empty);
    return;
  }

  for (const item of state.home.recommendations) {
    const row = document.createElement("article");
    row.className = "result-row";

    const title = document.createElement("h4");
    title.className = "result-title";
    title.textContent = item.title;

    const subtitle = document.createElement("p");
    subtitle.className = "result-subtitle";
    subtitle.textContent = item.artists.join(", ") || "—";

    const note = document.createElement("p");
    note.className = "result-note";
    note.textContent = item.explain;

    row.append(title, subtitle, note);
    homeRecommendationsList.appendChild(row);
  }
}

function renderHomeListResult(state: RendererState): void {
  if (!homeListResult) {
    return;
  }

  homeListResult.innerHTML = "";
  if (!state.home.listResult) {
    const empty = document.createElement("p");
    empty.className = "result-empty";
    empty.textContent = "Выберите фильтр и загрузите список.";
    homeListResult.appendChild(empty);
    return;
  }

  if (state.home.listResult.tracks.length === 0) {
    const empty = document.createElement("p");
    empty.className = "result-empty";
    empty.textContent = "Совпадений по фильтру не найдено.";
    homeListResult.appendChild(empty);
    return;
  }

  for (const item of state.home.listResult.tracks) {
    const row = document.createElement("article");
    row.className = "result-row";

    const title = document.createElement("h4");
    title.className = "result-title";
    title.textContent = item.title;

    const subtitle = document.createElement("p");
    subtitle.className = "result-subtitle";
    subtitle.textContent = item.artists.join(", ") || "—";

    row.append(title, subtitle);
    homeListResult.appendChild(row);
  }
}

function renderHomeView(state: RendererState): void {
  if (homeListKind) {
    homeListKind.value = state.home.listFilter.kind;
  }
  if (homeListValue) {
    homeListValue.value = state.home.listFilter.value;
  }

  renderSummaryGrid(
    homeSyncSummary,
    state.home.syncSummary
      ? [
          ["Добавлено", String(state.home.syncSummary.added)],
          ["Без изменений", String(state.home.syncSummary.unchanged)],
          ["Архивировано", String(state.home.syncSummary.archived)],
          ["Удалено", String(state.home.syncSummary.removed)],
        ]
      : [],
    "Синхронизация ещё не запускалась.",
  );
  renderHomeRecommendations(state);
  renderSummaryGrid(
    homeDiscoverySummary,
    state.home.discoverySummary
      ? [
          ["Добавлено", String(state.home.discoverySummary.added)],
          ["Пропущено", String(state.home.discoverySummary.skipped)],
          ["Уже лайкнуто", String(state.home.discoverySummary.removedLiked)],
          ["Очищено", String(state.home.discoverySummary.cleared)],
          ["Всего", String(state.home.discoverySummary.total)],
        ]
      : [],
    "Discovery summary пока не загружен.",
  );
  renderHomeListResult(state);
}

function renderNavigation(activeSection: AppSection): void {
  for (const navItem of navItems) {
    const isActive = navItem.dataset.section === activeSection;
    navItem.classList.toggle("is-active", isActive);
  }
}

function renderPlaceholder(state: RendererState): void {
  if (placeholderTitle) {
    placeholderTitle.textContent = state.placeholderTitle || "Скоро будет";
  }
  if (placeholderBody) {
    placeholderBody.textContent =
      state.placeholderBody || "Для этого макета сейчас полноценно реализованы Dashboard, Песни и Рекомендации.";
  }
}

function renderLayoutVisibility(state: RendererState): void {
  const homeActive = state.activeSection === "home";
  const dashboardActive = state.activeSection === "dashboard" && state.dashboardView !== null;
  const songActive = state.activeSection === "songs" && state.trackView !== null;
  const recommendationActive =
    state.activeSection === "recommendations" && state.recommendationView !== null;
  const placeholderActive = !homeActive && !dashboardActive && !songActive && !recommendationActive;

  if (homeView) {
    homeView.hidden = !homeActive;
  }

  if (viewerPlaceholder) {
    viewerPlaceholder.hidden = !placeholderActive;
  }
  if (metaPlaceholder) {
    metaPlaceholder.hidden = !placeholderActive;
  }
  if (songView) {
    songView.hidden = !songActive;
  }
  if (dashboardView) {
    dashboardView.hidden = !dashboardActive;
  }
  if (songMeta) {
    songMeta.hidden = !songActive;
  }
  if (dashboardMeta) {
    dashboardMeta.hidden = !dashboardActive;
  }
  if (recommendationView) {
    recommendationView.hidden = !recommendationActive;
  }
  if (recommendationMeta) {
    recommendationMeta.hidden = !recommendationActive;
  }
}

function renderShellMode(section: AppSection): void {
  if (!appShell) {
    return;
  }

  appShell.dataset.layout = sectionLayoutMode(section);
}

function renderSidebarCopy(state: RendererState): void {
  if (!listHeading || !listSubtitle || !listKicker) {
    return;
  }

  if (state.activeSection === "songs") {
    listKicker.textContent = "Коллекция";
    listHeading.textContent = "tracks/";
    listSubtitle.textContent = "Локальные заметки из tracks/ и tracks/_removed/.";
    return;
  }

  if (state.activeSection === "dashboard") {
    listKicker.textContent = "Обзор";
    listHeading.textContent = "dashboard.md";
    listSubtitle.textContent = "Снимок библиотеки и сводные метрики.";
    return;
  }

  if (state.activeSection === "recommendations") {
    listKicker.textContent = "Discovery";
    listHeading.textContent = "recommendations/";
    listSubtitle.textContent = "Сетевые рекомендации из Yandex Music.";
    return;
  }

  if (state.activeSection === "home") {
    listKicker.textContent = "Главная";
    listHeading.textContent = "actions/";
    listSubtitle.textContent = "Быстрые действия, рекомендации и локальные фильтры.";
    return;
  }

  listKicker.textContent = "Раздел";
  listHeading.textContent = state.placeholderTitle || "Скоро будет";
  listSubtitle.textContent = state.placeholderBody || "Этот экран появится позже.";
}

function render(): void {
  const state = controller.getState();
  renderNavigation(state.activeSection);
  renderShellMode(state.activeSection);
  renderSidebarCopy(state);
  renderLayoutVisibility(state);

  if (state.activeSection === "home") {
    if (listContent) {
      listContent.innerHTML = "";
    }
    if (listEmpty) {
      listEmpty.hidden = true;
    }
    renderHomeView(state);
  } else if (state.activeSection === "songs") {
    renderSongsList(state);
    renderSongView(state.trackView);
  } else if (state.activeSection === "dashboard") {
    if (listContent) {
      listContent.innerHTML = "";
      const group = document.createElement("section");
      group.className = "list-group";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "list-item is-selected";
      const title = document.createElement("span");
      title.className = "list-item-title";
      title.textContent = "dashboard.md";
      button.appendChild(title);
      group.appendChild(button);
      listContent.appendChild(group);
    }
    if (listEmpty) {
      listEmpty.hidden = true;
    }
    renderDashboardView(state.dashboardView);
  } else if (state.activeSection === "recommendations") {
    renderRecommendationsList(state);
    renderRecommendationView(state.recommendationView);
  } else {
    if (listContent) {
      listContent.innerHTML = "";
    }
    if (listEmpty) {
      listEmpty.hidden = false;
      listEmpty.textContent = "Этот раздел пока недоступен в текущем редизайне.";
    }
  }

  renderPlaceholder(state);
  setStatus(
    state.status.tone,
    state.activeSection === "home"
      ? "Главная"
      : state.activeSection === "songs"
      ? "Песни"
      : state.activeSection === "dashboard"
        ? "Дэшборд"
      : state.activeSection === "recommendations"
        ? "Рекомы"
        : "Скоро",
    state.status.message,
  );
}

async function activateSection(section: AppSection): Promise<void> {
  const loadingMessage =
    section === "home"
      ? "Открываю главную..."
      : section === "songs"
      ? "Загружаю локальные заметки..."
      : section === "recommendations"
        ? "Загружаю рекомендации..."
        : "Открываю раздел...";
  setBusy(true);
  setStatus("loading", "Загрузка", loadingMessage);
  try {
    await controller.activateSection(section);
    render();
  } catch (error) {
    setStatus("error", "Ошибка", error instanceof Error ? error.message : "Не удалось обновить экран");
  } finally {
    setBusy(false);
  }
}

async function selectSong(path: string): Promise<void> {
  setBusy(true);
  setStatus("loading", "Загрузка", "Открываю заметку...");
  try {
    await controller.selectSong(path);
    render();
  } catch (error) {
    setStatus("error", "Ошибка", error instanceof Error ? error.message : "Не удалось открыть заметку");
  } finally {
    setBusy(false);
  }
}

async function openRecommendation(path: string): Promise<void> {
  setBusy(true);
  setStatus("loading", "Загрузка", "Открываю рекомендацию...");
  try {
    await controller.openRecommendation(path);
    render();
  } catch (error) {
    setStatus("error", "Ошибка", error instanceof Error ? error.message : "Не удалось открыть рекомендацию");
  } finally {
    setBusy(false);
  }
}

async function runHomeSync(): Promise<void> {
  setBusy(true);
  setStatus("loading", "Загрузка", "Запускаю sync...");
  try {
    await controller.runHomeSync();
    render();
  } catch (error) {
    setStatus("error", "Ошибка", error instanceof Error ? error.message : "Не удалось выполнить sync");
  } finally {
    setBusy(false);
  }
}

async function loadHomeRecommendations(): Promise<void> {
  setBusy(true);
  setStatus("loading", "Загрузка", "Получаю рекомендации лайкнутых...");
  try {
    await controller.loadHomeRecommendations();
    render();
  } catch (error) {
    setStatus("error", "Ошибка", error instanceof Error ? error.message : "Не удалось получить рекомендации");
  } finally {
    setBusy(false);
  }
}

async function runHomeDiscovery(clear: boolean): Promise<void> {
  setBusy(true);
  setStatus(
    "loading",
    "Загрузка",
    clear ? "Очищаю discovery рекомендации..." : "Запускаю discovery рекомендации...",
  );
  try {
    if (clear) {
      await controller.clearHomeDiscovery();
    } else {
      await controller.runHomeDiscovery();
    }
    render();
  } catch (error) {
    setStatus(
      "error",
      "Ошибка",
      error instanceof Error
        ? error.message
        : clear
          ? "Не удалось очистить discovery"
          : "Не удалось выполнить discovery",
    );
  } finally {
    setBusy(false);
  }
}

async function runHomeList(): Promise<void> {
  controller.setHomeListFilterKind((homeListKind?.value as "tag" | "artist" | undefined) ?? "tag");
  controller.setHomeListFilterValue(homeListValue?.value.trim() ?? "");
  setBusy(true);
  setStatus("loading", "Загрузка", "Строю список треков...");
  try {
    await controller.runHomeList();
    render();
  } catch (error) {
    setStatus("error", "Ошибка", error instanceof Error ? error.message : "Не удалось построить список");
  } finally {
    setBusy(false);
  }
}

for (const navItem of navItems) {
  navItem.addEventListener("click", () => {
    const section = navItem.dataset.section as AppSection | undefined;
    if (!section) {
      return;
    }
    void activateSection(section);
  });
}

homeSyncButton?.addEventListener("click", () => {
  void runHomeSync();
});

homeRecommendButton?.addEventListener("click", () => {
  void loadHomeRecommendations();
});

homeDiscoveryButton?.addEventListener("click", () => {
  void runHomeDiscovery(false);
});

homeDiscoveryClearButton?.addEventListener("click", () => {
  void runHomeDiscovery(true);
});

homeListForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  void runHomeList();
});

homeListKind?.addEventListener("change", () => {
  controller.setHomeListFilterKind((homeListKind.value as "tag" | "artist") ?? "tag");
});

homeListValue?.addEventListener("input", () => {
  controller.setHomeListFilterValue(homeListValue.value);
});

void activateSection("home");
