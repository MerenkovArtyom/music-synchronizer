import assert from "node:assert/strict";
import test from "node:test";

import type { DashboardData, VaultData } from "../src/shared/contracts.js";
import {
  createRendererController,
  extractTrackView,
  formatDuration,
  sectionLayoutMode,
} from "../src/renderer/shell-controller.js";

function makeVaultData(overrides: Partial<VaultData> = {}): VaultData {
  return {
    vaultPath: "/tmp/vault",
    tree: [
      {
        name: "tracks",
        path: "tracks",
        kind: "directory",
        children: [
          {
            name: "_removed",
            path: "tracks/_removed",
            kind: "directory",
            children: [
              {
                name: "Old Song.md",
                path: "tracks/_removed/Old Song.md",
                kind: "file",
                children: null,
              },
            ],
          },
          {
            name: "Blinding Lights.md",
            path: "tracks/Blinding Lights.md",
            kind: "file",
            children: null,
          },
        ],
      },
    ],
    selectedPath: "tracks/Blinding Lights.md",
    selectedNote: {
      name: "Blinding Lights.md",
      path: "tracks/Blinding Lights.md",
      title: "Blinding Lights",
      content: `---
track_id: "101"
artists: ["The Weeknd"]
album: "After Hours"
year: 2020
system_tags: ["synthwave", "pop"]
user_tags: ["80s"]
cover_url: "https://example.com/cover.jpg"
duration_seconds: 200
monthly_listens: 4250000
yandex_url: "https://music.yandex.ru/album/10453120/track/78589472"
---

# Blinding Lights

- Artists: The Weeknd
- Album: After Hours
- Year: 2020
- Monthly listens (30d): 4250000
- Duration: 3:20
- Yandex Music: https://music.yandex.ru/album/10453120/track/78589472

![Album cover](https://example.com/cover.jpg)
`,
    },
    ...overrides,
  };
}

function makeDashboardData(): DashboardData {
  return {
    path: "/tmp/vault/dashboard.md",
    summary: {
      likedTracks: 76,
      removedTracks: 6,
      totalTracks: 82,
      totalDuration: "290:55",
      monthlyListensKnown: 49,
      monthlyListensCoveragePercent: 64.47,
      averageMonthlyListens: 1.55,
      medianMonthlyListens: 1,
      mostListenedTrack: {
        title: "Cheri cheri lady",
        artists: ["Modern Group"],
        monthlyListens: 4,
      },
      mostListenedArtist: {
        name: "Rammstein",
        monthlyListens: 13,
        tracks: 8,
      },
      mostUsedTag: {
        name: "pop",
        tracks: 12,
      },
      longestTrack: {
        title: "A Brand New Day",
        artists: ["Fabian Nesti"],
        duration: "6:13",
      },
    },
    topTags: [
      {
        name: "pop",
        tracks: 12,
      },
    ],
    topArtists: [
      {
        name: "Rammstein",
        monthlyListens: 13,
        tracks: 8,
      },
    ],
  };
}

test("extractTrackView parses frontmatter, note body, and tags for the songs screen", () => {
  const track = extractTrackView(makeVaultData().selectedNote);

  assert.equal(track.title, "Blinding Lights");
  assert.deepEqual(track.artists, ["The Weeknd"]);
  assert.equal(track.album, "After Hours");
  assert.equal(track.year, "2020");
  assert.equal(track.monthlyListens, "4,250,000");
  assert.equal(track.duration, "3:20");
  assert.equal(track.yandexUrl, "https://music.yandex.ru/album/10453120/track/78589472");
  assert.equal(track.coverUrl, "https://example.com/cover.jpg");
  assert.deepEqual(track.systemTags, ["synthwave", "pop"]);
  assert.deepEqual(track.userTags, ["80s"]);
});

test("createRendererController loads vault data when songs tab becomes active", async () => {
  const calls: string[] = [];
  const controller = createRendererController({
    getVaultView: async (request) => {
      calls.push(`vault:${request.selectedPath ?? ""}`);
      return makeVaultData();
    },
    getRecommendationsVaultView: async () => {
      throw new Error("unexpected recommendations call");
    },
    getDashboardData: async () => {
      throw new Error("unexpected dashboard call");
    },
  });

  await controller.activateSection("songs");

  assert.deepEqual(calls, ["vault:"]);
  assert.equal(controller.getState().activeSection, "songs");
  assert.equal(controller.getState().selectedSongPath, "tracks/Blinding Lights.md");
  assert.equal(controller.getState().songItems[0]?.label, "Blinding Lights.md");
});

test("createRendererController filters songs tab down to tracks paths only", async () => {
  const controller = createRendererController({
    getVaultView: async () =>
      makeVaultData({
        tree: [
          {
            name: "dashboard.md",
            path: "dashboard.md",
            kind: "file",
            children: null,
          },
          {
            name: "artists",
            path: "artists",
            kind: "directory",
            children: [
              {
                name: "Artist A.md",
                path: "artists/Artist A.md",
                kind: "file",
                children: null,
              },
            ],
          },
          {
            name: "tracks",
            path: "tracks",
            kind: "directory",
            children: [
              {
                name: "Song A.md",
                path: "tracks/Song A.md",
                kind: "file",
                children: null,
              },
            ],
          },
        ],
        selectedPath: "tracks/Song A.md",
        selectedNote: {
          name: "Song A.md",
          path: "tracks/Song A.md",
          title: "Song A",
          content: "# Song A\n\nArtists: Artist A\nAlbum: Album A\nYear: 2024\nDuration: 3:00\n",
        },
      }),
    getRecommendationsVaultView: async () => {
      throw new Error("unexpected recommendations call");
    },
    getDashboardData: async () => {
      throw new Error("unexpected dashboard call");
    },
  });

  await controller.activateSection("songs");

  assert.deepEqual(
    controller.getState().songItems.map((item) => item.path),
    ["tracks/Song A.md"],
  );
});

test("createRendererController reloads vault data for a selected song", async () => {
  const calls: string[] = [];
  const controller = createRendererController({
    getVaultView: async (request) => {
      calls.push(`vault:${request.selectedPath ?? ""}`);
      return makeVaultData({
        selectedPath: request.selectedPath ?? "tracks/Blinding Lights.md",
      });
    },
    getRecommendationsVaultView: async () => {
      throw new Error("unexpected recommendations call");
    },
    getDashboardData: async () => {
      throw new Error("unexpected dashboard call");
    },
  });

  await controller.activateSection("songs");
  await controller.selectSong("tracks/_removed/Old Song.md");

  assert.deepEqual(calls, ["vault:", "vault:tracks/_removed/Old Song.md"]);
  assert.equal(controller.getState().selectedSongPath, "tracks/_removed/Old Song.md");
});

test("createRendererController loads recommendation notes from the vault when recommendations tab becomes active", async () => {
  const calls: string[] = [];
  const controller = createRendererController({
    getVaultView: async () => {
      throw new Error("unexpected songs vault call");
    },
    getRecommendationsVaultView: async (request) => {
      calls.push(`vault:${request.selectedPath ?? ""}`);
      return {
        ...makeVaultData({
          tree: [
            {
              name: "recommendations",
              path: "recommendations",
              kind: "directory",
              children: [
                {
                  name: "Popular One.md",
                  path: "recommendations/Popular One.md",
                  kind: "file",
                  children: null,
                },
              ],
            },
          ],
          selectedPath: "recommendations/Popular One.md",
          selectedNote: {
            name: "Popular One.md",
            path: "recommendations/Popular One.md",
            title: "Popular One",
            content: "# Popular One\n\nArtists: Artist A\nAlbum: Album A\nYear: 2024\nMonthly listens (30d): 12\nDuration: 3:01\nYandex Music: https://music.yandex.ru/track/501\nDiscovery sources: artist-popular, recent-likes\n\n![Album cover](https://example.com/reco.jpg)\n",
          },
        }),
      };
    },
    getDashboardData: async () => {
      throw new Error("unexpected dashboard call");
    },
  });

  await controller.activateSection("recommendations");

  assert.deepEqual(calls, ["vault:"]);
  assert.equal(controller.getState().activeSection, "recommendations");
  assert.equal(controller.getState().selectedRecommendationId, "recommendations/Popular One.md");
  assert.equal(controller.getState().recommendationItems[0]?.title, "Popular One");
});

test("createRendererController keeps placeholder sections local and avoids backend calls", async () => {
  const controller = createRendererController({
    getVaultView: async () => {
      throw new Error("unexpected vault call");
    },
    getRecommendationsVaultView: async () => {
      throw new Error("unexpected recommendations call");
    },
    getDashboardData: async () => {
      throw new Error("unexpected dashboard call");
    },
  });

  await controller.activateSection("home");

  assert.equal(controller.getState().activeSection, "home");
  assert.equal(controller.getState().status.message, "Раздел в разработке");
});

test("createRendererController loads dashboard note and summary when dashboard tab becomes active", async () => {
  const calls: string[] = [];
  const controller = createRendererController({
    getVaultView: async (request) => {
      calls.push(`vault:${request.selectedPath ?? ""}`);
      return makeVaultData({
        tree: [
          {
            name: "dashboard.md",
            path: "dashboard.md",
            kind: "file",
            children: null,
          },
        ],
        selectedPath: "dashboard.md",
        selectedNote: {
          name: "dashboard.md",
          path: "dashboard.md",
          title: "dashboard",
          content: "# Music Dashboard\n\n## Overview\n- Liked tracks: 76\n",
        },
      });
    },
    getRecommendationsVaultView: async () => {
      throw new Error("unexpected recommendations call");
    },
    getDashboardData: async () => {
      calls.push("dashboard");
      return makeDashboardData();
    },
  });

  await controller.activateSection("dashboard");

  assert.deepEqual(calls, ["vault:dashboard.md", "dashboard"]);
  assert.equal(controller.getState().activeSection, "dashboard");
  assert.equal(controller.getState().dashboardView?.path, "dashboard.md");
  assert.equal(controller.getState().dashboardView?.summary.likedTracks, 76);
});

test("extractTrackView keeps note body text available for rendering", () => {
  const track = extractTrackView(makeVaultData().selectedNote);

  assert.match(track.noteBody, /Artists: The Weeknd/);
  assert.match(track.noteBody, /Album cover/);
});

test("formatDuration returns a compact minute-second label", () => {
  assert.equal(formatDuration(181), "3:01");
  assert.equal(formatDuration(0), "0:00");
});

test("sectionLayoutMode hides secondary chrome only for dashboard", () => {
  assert.equal(sectionLayoutMode("dashboard"), "dashboard");
  assert.equal(sectionLayoutMode("songs"), "default");
  assert.equal(sectionLayoutMode("recommendations"), "default");
});
