import type {
  DashboardData,
  DiscoveryData,
  DiscoveryRequest,
  ListData,
  ListTracksRequest,
  RecommendationData,
  RecommendationRequest,
  SyncData,
  VaultData,
  VaultRequest,
  VaultTreeNode,
} from "../shared/contracts.js";

export type AppSection =
  | "home"
  | "dashboard"
  | "songs"
  | "tags"
  | "artists"
  | "recommendations";

export type SectionLayoutMode = "default" | "dashboard" | "home";

export interface RendererStatus {
  tone: "idle" | "loading" | "success" | "placeholder";
  message: string;
}

export interface SongListItem {
  path: string;
  label: string;
  archived: boolean;
}

export interface RecommendationListItem {
  id: string;
  title: string;
  subtitle: string;
}

export interface VaultNoteListItem {
  path: string;
  label: string;
}

export interface TrackView {
  title: string;
  trackId: string;
  path: string;
  noteBody: string;
  artists: string[];
  album: string;
  year: string;
  monthlyListens: string;
  duration: string;
  yandexUrl: string;
  coverUrl: string;
  systemTags: string[];
  userTags: string[];
  archived: boolean;
}

export interface DiscoveryView {
  id: string;
  title: string;
  path: string;
  noteBody: string;
  artists: string[];
  album: string;
  year: string;
  monthlyListens: string;
  duration: string;
  yandexUrl: string;
  coverUrl: string;
  explain: string;
  sources: string[];
  systemTags: string[];
}

export interface DashboardView {
  path: string;
  title: string;
  noteBody: string;
  summary: DashboardData["summary"];
  topTags: DashboardData["topTags"];
  topArtists: DashboardData["topArtists"];
}

export interface VaultNoteView {
  path: string;
  title: string;
  noteBody: string;
}

export interface HomeListFilter {
  kind: ListTracksRequest["kind"];
  value: string;
}

export interface HomeState {
  syncSummary: SyncData["summary"] | null;
  recommendations: RecommendationData["recommendations"];
  discoverySummary: DiscoveryData["summary"] | null;
  listFilter: HomeListFilter;
  listResult: ListData | null;
}

export interface RendererState {
  activeSection: AppSection;
  status: RendererStatus;
  home: HomeState;
  songItems: SongListItem[];
  selectedSongPath: string | null;
  trackView: TrackView | null;
  artistItems: VaultNoteListItem[];
  selectedArtistPath: string | null;
  artistView: VaultNoteView | null;
  tagItems: VaultNoteListItem[];
  selectedTagPath: string | null;
  tagView: VaultNoteView | null;
  recommendationItems: RecommendationListItem[];
  selectedRecommendationId: string | null;
  recommendationView: DiscoveryView | null;
  dashboardView: DashboardView | null;
  placeholderTitle: string;
  placeholderBody: string;
}

type VaultNoteLike = NonNullable<VaultData["selectedNote"]>;

interface ControllerDeps {
  getVaultView: (request: VaultRequest) => Promise<VaultData>;
  getRecommendationsVaultView: (request: VaultRequest) => Promise<VaultData>;
  getDashboardData: () => Promise<DashboardData>;
  runSync: () => Promise<SyncData>;
  getRecommendations: (request: RecommendationRequest) => Promise<RecommendationData>;
  getDiscoveryRecommendations: (request: DiscoveryRequest) => Promise<DiscoveryData>;
  listTracks: (request: ListTracksRequest) => Promise<ListData>;
}

export function sectionLayoutMode(section: AppSection): SectionLayoutMode {
  if (section === "home") {
    return "home";
  }
  return section === "dashboard" ? "dashboard" : "default";
}

export function formatDuration(durationSeconds: number): string {
  const safeValue = Number.isFinite(durationSeconds) ? Math.max(0, Math.floor(durationSeconds)) : 0;
  const minutes = Math.floor(safeValue / 60);
  const seconds = safeValue % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return new Intl.NumberFormat("en-US").format(value);
}

function cleanText(value: string | null | undefined): string {
  const normalized = value?.trim() ?? "";
  return normalized.length > 0 ? normalized : "—";
}

function parseFrontmatter(content: string): Record<string, unknown> {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) {
    return {};
  }

  const result: Record<string, unknown> = {};
  for (const rawLine of match[1].split("\n")) {
    const line = rawLine.trim();
    if (line.length === 0 || !line.includes(":")) {
      continue;
    }

    const separatorIndex = line.indexOf(":");
    const key = line.slice(0, separatorIndex).trim();
    const rawValue = line.slice(separatorIndex + 1).trim();
    result[key] = parseFrontmatterValue(rawValue);
  }

  return result;
}

function parseFrontmatterValue(rawValue: string): unknown {
  if (rawValue === "null") {
    return null;
  }
  if (rawValue === "true") {
    return true;
  }
  if (rawValue === "false") {
    return false;
  }
  if (/^-?\d+$/.test(rawValue)) {
    return Number.parseInt(rawValue, 10);
  }
  if (rawValue.startsWith("[") && rawValue.endsWith("]")) {
    return parseArrayValue(rawValue);
  }
  if ((rawValue.startsWith('"') && rawValue.endsWith('"')) || (rawValue.startsWith("'") && rawValue.endsWith("'"))) {
    return rawValue.slice(1, -1);
  }
  return rawValue;
}

function parseArrayValue(rawValue: string): string[] {
  const body = rawValue.slice(1, -1).trim();
  if (body.length === 0) {
    return [];
  }

  const matches = body.match(/"([^"]*)"|'([^']*)'|([^,\s][^,]*)/g) ?? [];
  return matches
    .map((entry) => entry.trim().replace(/^['"]|['"]$/g, ""))
    .filter((entry) => entry.length > 0);
}

function stripFrontmatter(content: string): string {
  return content.replace(/^---\n[\s\S]*?\n---\n?/, "");
}

function findBodyValue(content: string, label: string): string | null {
  const expression = new RegExp(`^(?:-\\s*)?${label}:\\s*(.+)$`, "im");
  const match = stripFrontmatter(content).match(expression);
  return match?.[1]?.trim() ?? null;
}

function findHeading(content: string): string | null {
  return stripFrontmatter(content).match(/^#\s+(.+)$/m)?.[1]?.trim() ?? null;
}

function findMarkdownImage(content: string): string | null {
  return stripFrontmatter(content).match(/!\[[^\]]*\]\(([^)\s]+)\)/)?.[1]?.trim() ?? null;
}

function toStringValue(frontmatter: Record<string, unknown>, key: string): string | null {
  const value = frontmatter[key];
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    return String(value);
  }
  return null;
}

function toNumberValue(frontmatter: Record<string, unknown>, key: string): number | null {
  const value = frontmatter[key];
  return typeof value === "number" ? value : null;
}

function toListValue(frontmatter: Record<string, unknown>, key: string): string[] {
  const value = frontmatter[key];
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];
}

function splitArtists(value: string | null): string[] {
  return (value ?? "")
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
}

function dedupe(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    const normalized = value.trim();
    if (normalized.length === 0 || seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    result.push(normalized);
  }
  return result;
}

export function extractTrackView(note: VaultNoteLike | null): TrackView {
  if (!note) {
    return {
      title: "—",
      trackId: "—",
      path: "",
      noteBody: "",
      artists: [],
      album: "—",
      year: "—",
      monthlyListens: "—",
      duration: "—",
      yandexUrl: "",
      coverUrl: "",
      systemTags: [],
      userTags: [],
      archived: false,
    };
  }

  const frontmatter = parseFrontmatter(note.content);
  const artists = dedupe([
    ...toListValue(frontmatter, "artists"),
    ...splitArtists(findBodyValue(note.content, "Artists")),
  ]);
  const durationSeconds = toNumberValue(frontmatter, "duration_seconds");
  const bodyDuration = findBodyValue(note.content, "Duration");
  const monthlyListensNumber = toNumberValue(frontmatter, "monthly_listens");
  const bodyMonthlyListens = findBodyValue(note.content, "Monthly listens \\(30d\\)");
  const title = cleanText(
    toStringValue(frontmatter, "title") ?? findHeading(note.content) ?? note.title,
  );

  return {
    title,
    trackId: cleanText(toStringValue(frontmatter, "track_id")),
    path: note.path,
    noteBody: note.content,
    artists,
    album: cleanText(toStringValue(frontmatter, "album") ?? findBodyValue(note.content, "Album")),
    year: cleanText(toStringValue(frontmatter, "year") ?? findBodyValue(note.content, "Year")),
    monthlyListens:
      monthlyListensNumber !== null
        ? formatCount(monthlyListensNumber)
        : cleanText(bodyMonthlyListens),
    duration:
      durationSeconds !== null
        ? formatDuration(durationSeconds)
        : cleanText(bodyDuration),
    yandexUrl: cleanText(toStringValue(frontmatter, "yandex_url") ?? findBodyValue(note.content, "Yandex Music")),
    coverUrl: cleanText(toStringValue(frontmatter, "cover_url") ?? findMarkdownImage(note.content)) === "—"
      ? ""
      : cleanText(toStringValue(frontmatter, "cover_url") ?? findMarkdownImage(note.content)),
    systemTags: dedupe(toListValue(frontmatter, "system_tags")),
    userTags: dedupe(toListValue(frontmatter, "user_tags")),
    archived: note.path.includes("/_removed/"),
  };
}

function extractRecommendationView(note: VaultNoteLike | null): DiscoveryView | null {
  if (!note) {
    return null;
  }

  const frontmatter = parseFrontmatter(note.content);
  const artists = dedupe([
    ...toListValue(frontmatter, "artists"),
    ...splitArtists(findBodyValue(note.content, "Artists")),
  ]);
  const durationSeconds = toNumberValue(frontmatter, "duration_seconds");
  const bodyDuration = findBodyValue(note.content, "Duration");
  const monthlyListensNumber = toNumberValue(frontmatter, "monthly_listens");
  const bodyMonthlyListens = findBodyValue(note.content, "Monthly listens \\(30d\\)");
  const sources = dedupe([
    ...toListValue(frontmatter, "discovery_sources"),
    ...splitArtists(findBodyValue(note.content, "Discovery sources")),
  ]);

  return {
    id: cleanText(toStringValue(frontmatter, "track_id")),
    path: note.path,
    noteBody: note.content,
    title: cleanText(toStringValue(frontmatter, "title") ?? findHeading(note.content) ?? note.title),
    artists,
    album: cleanText(toStringValue(frontmatter, "album") ?? findBodyValue(note.content, "Album")),
    year: cleanText(toStringValue(frontmatter, "year") ?? findBodyValue(note.content, "Year")),
    monthlyListens:
      monthlyListensNumber !== null ? formatCount(monthlyListensNumber) : cleanText(bodyMonthlyListens),
    duration:
      durationSeconds !== null ? formatDuration(durationSeconds) : cleanText(bodyDuration),
    yandexUrl: cleanText(toStringValue(frontmatter, "yandex_url") ?? findBodyValue(note.content, "Yandex Music")),
    coverUrl: cleanText(toStringValue(frontmatter, "cover_url") ?? findMarkdownImage(note.content)) === "—"
      ? ""
      : cleanText(toStringValue(frontmatter, "cover_url") ?? findMarkdownImage(note.content)),
    explain: cleanText(findBodyValue(note.content, "Discovery sources")),
    sources,
    systemTags: dedupe(toListValue(frontmatter, "system_tags")),
  };
}

function flattenVaultFiles(tree: VaultTreeNode[]): SongListItem[] {
  const items: SongListItem[] = [];

  const visit = (node: VaultTreeNode): void => {
    if (node.kind === "file") {
      items.push({
        path: node.path,
        label: node.name,
        archived: node.path.includes("/_removed/"),
      });
      return;
    }

    for (const child of node.children ?? []) {
      visit(child);
    }
  };

  for (const node of tree) {
    visit(node);
  }

  return items.sort((left, right) => {
    if (left.archived !== right.archived) {
      return left.archived ? 1 : -1;
    }
    return left.label.localeCompare(right.label, "en");
  });
}

function songItemsFromVault(tree: VaultTreeNode[]): SongListItem[] {
  return flattenVaultFiles(tree).filter((item) => item.path === "tracks" || item.path.startsWith("tracks/"));
}

function recommendationItemsFromVault(tree: VaultTreeNode[]): RecommendationListItem[] {
  return flattenVaultFiles(tree)
    .filter((item) => item.path.startsWith("recommendations/"))
    .map((item) => ({
      id: item.path,
      title: item.label.replace(/\.md$/i, ""),
      subtitle: "Локальная рекомендация",
    }));
}

function noteItemsFromVault(tree: VaultTreeNode[], directory: "artists" | "tags"): VaultNoteListItem[] {
  return flattenVaultFiles(tree)
    .filter((item) => item.path.startsWith(`${directory}/`))
    .map((item) => ({
      path: item.path,
      label: item.label,
    }));
}

function extractVaultNoteView(note: VaultNoteLike | null): VaultNoteView | null {
  if (!note) {
    return null;
  }

  return {
    path: note.path,
    title: cleanText(findHeading(note.content) ?? note.title),
    noteBody: note.content,
  };
}

export function resolveInternalTrackLink(currentPath: string, href: string): string | null {
  const trimmedHref = href.trim();
  if (
    trimmedHref.length === 0
    || trimmedHref.startsWith("#")
    || /^[a-z]+:/i.test(trimmedHref)
    || trimmedHref.startsWith("//")
  ) {
    return null;
  }

  const sanitizedHref = trimmedHref.split("#", 1)[0]?.split("?", 1)[0] ?? "";
  if (sanitizedHref.length === 0) {
    return null;
  }
  if (sanitizedHref.startsWith("tracks/") && sanitizedHref.endsWith(".md")) {
    return sanitizedHref;
  }

  const currentSegments = currentPath.split("/").slice(0, -1);
  const rawSegments = sanitizedHref.split("/");
  const resolvedSegments = sanitizedHref.startsWith("/") ? [] : [...currentSegments];

  for (const segment of rawSegments) {
    if (segment.length === 0 || segment === ".") {
      continue;
    }
    if (segment === "..") {
      resolvedSegments.pop();
      continue;
    }
    resolvedSegments.push(segment);
  }

  const resolvedPath = resolvedSegments.join("/");
  if (resolvedPath.startsWith("tracks/") && resolvedPath.endsWith(".md")) {
    return resolvedPath;
  }
  return null;
}

export function parseWikiLink(rawLink: string): { target: string; label: string } | null {
  const match = rawLink.match(/^\[\[([\s\S]+)\]\]$/);
  if (!match) {
    return null;
  }

  const body = match[1]?.trim() ?? "";
  if (body.length === 0) {
    return null;
  }

  const separatorIndex = body.indexOf("|");
  const target = (separatorIndex >= 0 ? body.slice(0, separatorIndex) : body).trim();
  const rawLabel = (separatorIndex >= 0 ? body.slice(separatorIndex + 1) : "").trim();
  if (target.length === 0) {
    return null;
  }

  const targetName = target.split("/").pop() ?? target;
  const label = rawLabel || targetName.replace(/\.md$/i, "");
  if (label.length === 0) {
    return null;
  }

  return { target, label };
}

function placeholderCopy(section: AppSection): { title: string; body: string } {
  const titles: Record<Exclude<AppSection, "songs" | "recommendations">, string> = {
    home: "Главная",
    dashboard: "Dashboard",
    tags: "Теги",
    artists: "Артисты",
  };

  return {
    title: titles[section as Exclude<AppSection, "songs" | "recommendations">] ?? "Скоро будет",
    body: "Раздел в разработке",
  };
}

export function createRendererController(deps: ControllerDeps) {
  const state: RendererState = {
    activeSection: "home",
    status: {
      tone: "idle",
      message: "Готово к загрузке библиотеки",
    },
    home: {
      syncSummary: null,
      recommendations: [],
      discoverySummary: null,
      listFilter: {
        kind: "tag",
        value: "",
      },
      listResult: null,
    },
    songItems: [],
    selectedSongPath: null,
    trackView: null,
    artistItems: [],
    selectedArtistPath: null,
    artistView: null,
    tagItems: [],
    selectedTagPath: null,
    tagView: null,
    recommendationItems: [],
    selectedRecommendationId: null,
    recommendationView: null,
    dashboardView: null,
    placeholderTitle: "",
    placeholderBody: "",
  };

  async function loadSongs(selectedPath?: string): Promise<void> {
    let payload = await deps.getVaultView(selectedPath ? { selectedPath } : {});
    let items = songItemsFromVault(payload.tree);
    let resolvedPath = payload.selectedPath ?? selectedPath ?? items[0]?.path ?? null;

    if (resolvedPath && !resolvedPath.startsWith("tracks/")) {
      resolvedPath = items[0]?.path ?? null;
    }

    if (!payload.selectedNote && resolvedPath && resolvedPath !== selectedPath) {
      payload = await deps.getVaultView({ selectedPath: resolvedPath });
      items = songItemsFromVault(payload.tree);
      resolvedPath = payload.selectedPath ?? resolvedPath;
    }

    if (resolvedPath && !resolvedPath.startsWith("tracks/")) {
      resolvedPath = items[0]?.path ?? null;
    }

    state.songItems = items;
    state.selectedSongPath = resolvedPath;
    state.trackView = payload.selectedNote ? extractTrackView(payload.selectedNote) : null;
    state.status = {
      tone: "success",
      message:
        items.length > 0 ? "Музыкальная библиотека загружена" : "В папке tracks пока нет заметок",
    };
  }

  async function loadRecommendations(): Promise<void> {
    let payload = await deps.getRecommendationsVaultView({});
    let items = recommendationItemsFromVault(payload.tree);
    let resolvedPath = payload.selectedPath ?? items[0]?.id ?? null;

    if (resolvedPath && !resolvedPath.startsWith("recommendations/")) {
      resolvedPath = items[0]?.id ?? null;
    }

    if (!payload.selectedNote && resolvedPath) {
      payload = await deps.getRecommendationsVaultView({ selectedPath: resolvedPath });
      items = recommendationItemsFromVault(payload.tree);
      resolvedPath = payload.selectedPath ?? resolvedPath;
    }

    state.recommendationItems = items;
    state.selectedRecommendationId = resolvedPath;
    state.recommendationView = payload.selectedNote ? extractRecommendationView(payload.selectedNote) : null;
    state.status = {
      tone: "success",
      message:
        items.length > 0 ? "Рекомендации загружены" : "В папке recommendations пока нет заметок",
    };
  }

  async function loadVaultSection(section: "artists" | "tags", selectedPath?: string): Promise<void> {
    let payload = await deps.getVaultView(selectedPath ? { selectedPath } : {});
    let items = noteItemsFromVault(payload.tree, section);
    let resolvedPath = payload.selectedPath ?? selectedPath ?? items[0]?.path ?? null;

    if (resolvedPath && !resolvedPath.startsWith(`${section}/`)) {
      resolvedPath = items[0]?.path ?? null;
    }

    if (!payload.selectedNote && resolvedPath && resolvedPath !== selectedPath) {
      payload = await deps.getVaultView({ selectedPath: resolvedPath });
      items = noteItemsFromVault(payload.tree, section);
      resolvedPath = payload.selectedPath ?? resolvedPath;
    }

    if (resolvedPath && !resolvedPath.startsWith(`${section}/`)) {
      resolvedPath = items[0]?.path ?? null;
    }

    const view = payload.selectedNote ? extractVaultNoteView(payload.selectedNote) : null;
    if (section === "artists") {
      state.artistItems = items;
      state.selectedArtistPath = resolvedPath;
      state.artistView = view;
      state.status = {
        tone: "success",
        message: items.length > 0 ? "Заметки артистов загружены" : "В папке artists пока нет заметок",
      };
      return;
    }

    state.tagItems = items;
    state.selectedTagPath = resolvedPath;
    state.tagView = view;
    state.status = {
      tone: "success",
      message: items.length > 0 ? "Заметки тегов загружены" : "В папке tags пока нет заметок",
    };
  }

  async function loadDashboard(): Promise<void> {
    const [vaultPayload, dashboardPayload] = await Promise.all([
      deps.getVaultView({ selectedPath: "dashboard.md" }),
      deps.getDashboardData(),
    ]);

    state.dashboardView = {
      path: vaultPayload.selectedPath ?? "dashboard.md",
      title: vaultPayload.selectedNote?.title ?? "dashboard",
      noteBody: vaultPayload.selectedNote?.content ?? "",
      summary: dashboardPayload.summary,
      topTags: dashboardPayload.topTags,
      topArtists: dashboardPayload.topArtists,
    };
    state.status = {
      tone: "success",
      message: "Дэшборд загружен",
    };
  }

  function activateHome(): void {
    state.status = {
      tone: "idle",
      message: "Быстрые действия и локальные инструменты.",
    };
  }

  return {
    getState(): RendererState {
      return state;
    },
    async activateSection(section: AppSection): Promise<void> {
      state.activeSection = section;
      if (section === "home") {
        activateHome();
        return;
      }
      if (section === "songs") {
        await loadSongs();
        return;
      }
      if (section === "dashboard") {
        await loadDashboard();
        return;
      }
      if (section === "recommendations") {
        await loadRecommendations();
        return;
      }
      if (section === "artists") {
        await loadVaultSection("artists");
        return;
      }
      if (section === "tags") {
        await loadVaultSection("tags");
        return;
      }

      const placeholder = placeholderCopy(section);
      state.placeholderTitle = placeholder.title;
      state.placeholderBody = placeholder.body;
      state.status = {
        tone: "placeholder",
        message: placeholder.body,
      };
    },
    async runHomeSync(): Promise<void> {
      state.activeSection = "home";
      const payload = await deps.runSync();
      state.home.syncSummary = payload.summary;
      state.status = {
        tone: "success",
        message: "Синхронизация завершена",
      };
    },
    async loadHomeRecommendations(): Promise<void> {
      state.activeSection = "home";
      const payload = await deps.getRecommendations({ archived: false });
      state.home.recommendations = payload.recommendations;
      state.status = {
        tone: "success",
        message:
          payload.recommendations.length > 0
            ? "Рекомендации лайкнутых загружены"
            : "Рекомендации лайкнутых не найдены",
      };
    },
    async runHomeDiscovery(): Promise<void> {
      state.activeSection = "home";
      const payload = await deps.getDiscoveryRecommendations({ clear: false });
      state.home.discoverySummary = payload.summary;
      state.status = {
        tone: "success",
        message: "Discovery рекомендации обновлены",
      };
    },
    async clearHomeDiscovery(): Promise<void> {
      state.activeSection = "home";
      const payload = await deps.getDiscoveryRecommendations({ clear: true });
      state.home.discoverySummary = payload.summary;
      state.status = {
        tone: "success",
        message: "Discovery рекомендации очищены",
      };
    },
    setHomeListFilterKind(kind: ListTracksRequest["kind"]): void {
      state.home.listFilter.kind = kind;
    },
    setHomeListFilterValue(value: string): void {
      state.home.listFilter.value = value;
    },
    async runHomeList(): Promise<void> {
      state.activeSection = "home";
      const payload = await deps.listTracks({
        kind: state.home.listFilter.kind,
        value: state.home.listFilter.value,
      });
      state.home.listResult = payload;
      state.status = {
        tone: "success",
        message:
          payload.tracks.length > 0
            ? "Список треков загружен"
            : "Совпадений по фильтру не найдено",
      };
    },
    async selectSong(path: string): Promise<void> {
      state.activeSection = "songs";
      await loadSongs(path);
    },
    async selectArtist(path: string): Promise<void> {
      state.activeSection = "artists";
      await loadVaultSection("artists", path);
    },
    async selectTag(path: string): Promise<void> {
      state.activeSection = "tags";
      await loadVaultSection("tags", path);
    },
    selectRecommendation(trackId: string): void {
      state.selectedRecommendationId = trackId;
    },
    async openRecommendation(path: string): Promise<void> {
      state.activeSection = "recommendations";
      const payload = await deps.getRecommendationsVaultView({ selectedPath: path });
      state.selectedRecommendationId = payload.selectedPath ?? path;
      state.recommendationView = payload.selectedNote ? extractRecommendationView(payload.selectedNote) : null;
      state.status = {
        tone: "success",
        message: "Рекомендация открыта",
      };
    },
  };
}
