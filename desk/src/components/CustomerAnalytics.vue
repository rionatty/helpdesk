<template>
  <section class="px-4 md:px-8 mt-6 flex flex-col gap-4">
    <div class="flex items-center gap-2">
      <div
        class="size-7 rounded-lg hd-icon-violet flex items-center justify-center shadow-sm ring-1 ring-inset ring-white/40"
      >
        <LucideBarChart3 class="size-4 text-white" />
      </div>
      <h2 class="executive-heading text-lg text-ink-gray-9">
        {{ __("Your analytics") }}
      </h2>
    </div>

    <div v-if="tickets.length === 0 && !resource.loading">
      <div
        class="executive-card flex flex-col items-center justify-center text-center py-10 gap-2"
      >
        <div
          class="size-12 rounded-full bg-gradient-to-br from-blue-100 via-violet-100 to-amber-100 flex items-center justify-center"
        >
          <LucideBarChart3 class="size-6 text-violet-700" />
        </div>
        <p class="font-medium text-ink-gray-8">{{ __("No data yet") }}</p>
        <p class="text-sm text-ink-gray-5">
          {{ __("Charts will appear once you have a few tickets.") }}
        </p>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- 1. Ticket volume over time -->
      <div class="executive-card hd-color-card p-5 pt-6" data-accent="blue">
        <div class="flex items-center gap-2 mb-3">
          <LucideTrendingUp class="size-4 text-blue-600" />
          <span class="text-sm font-semibold text-ink-gray-8">
            {{ __("Ticket volume") }}
          </span>
          <span class="text-xs text-ink-gray-5">{{ __("last 6 months") }}</span>
        </div>
        <ECharts :options="volumeOption" class="w-full h-56" />
      </div>

      <!-- 2. Status breakdown donut -->
      <div class="executive-card hd-color-card p-5 pt-6" data-accent="emerald">
        <div class="flex items-center gap-2 mb-3">
          <LucidePieChart class="size-4 text-emerald-600" />
          <span class="text-sm font-semibold text-ink-gray-8">
            {{ __("Status breakdown") }}
          </span>
        </div>
        <ECharts :options="statusOption" class="w-full h-56" />
      </div>

      <!-- 3. Avg resolution time trend -->
      <div class="executive-card hd-color-card p-5 pt-6" data-accent="amber">
        <div class="flex items-center gap-2 mb-3">
          <LucideTimer class="size-4 text-amber-600" />
          <span class="text-sm font-semibold text-ink-gray-8">
            {{ __("Avg resolution time") }}
          </span>
          <span class="text-xs text-ink-gray-5">{{ __("last 6 months") }}</span>
        </div>
        <ECharts
          v-if="hasResolved"
          :options="resolutionOption"
          class="w-full h-56"
        />
        <div
          v-else
          class="h-56 flex flex-col items-center justify-center text-center gap-2 text-ink-gray-5"
        >
          <LucideTimer class="size-8 text-ink-gray-4" />
          <p class="text-sm">{{ __("No resolved tickets yet") }}</p>
        </div>
      </div>

      <!-- 4. CSAT ratings -->
      <div class="executive-card hd-color-card p-5 pt-6" data-accent="rose">
        <div class="flex items-center gap-2 mb-3">
          <LucideStar class="size-4 text-rose-500" />
          <span class="text-sm font-semibold text-ink-gray-8">
            {{ __("Your ratings") }}
          </span>
          <span v-if="hasRatings" class="text-xs text-ink-gray-5">
            {{ __("avg") }} {{ avgRating }}★
          </span>
        </div>
        <ECharts v-if="hasRatings" :options="ratingOption" class="w-full h-56" />
        <div
          v-else
          class="h-56 flex flex-col items-center justify-center text-center gap-2 text-ink-gray-5"
        >
          <LucideStar class="size-8 text-ink-gray-4" />
          <p class="text-sm">{{ __("No ratings submitted yet") }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { createListResource, dayjs, ECharts } from "frappe-ui";
import { useAuthStore } from "@/stores/auth";
import { dataTheme, formatTime } from "@/utils";
import { __ } from "@/translation";
import type { EChartsOption } from "echarts";
import LucideBarChart3 from "~icons/lucide/bar-chart-3";
import LucideTrendingUp from "~icons/lucide/trending-up";
import LucidePieChart from "~icons/lucide/pie-chart";
import LucideTimer from "~icons/lucide/timer";
import LucideStar from "~icons/lucide/star";

interface TicketRow {
  name: string;
  creation?: string;
  status?: string;
  resolution_date?: string;
  resolution_time?: number;
  feedback_rating?: number;
}

const authStore = useAuthStore();

const resource = createListResource({
  doctype: "HD Ticket",
  fields: [
    "name",
    "creation",
    "status",
    "resolution_date",
    "resolution_time",
    "feedback_rating",
  ],
  filters: computed(() => ({ raised_by: authStore.userId })),
  orderBy: "creation desc",
  pageLength: 500,
  auto: true,
});

const tickets = computed<TicketRow[]>(() => resource.data || []);

const cssVar = (name: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const last6Months = computed(() => {
  const arr: ReturnType<typeof dayjs>[] = [];
  const start = dayjs().startOf("month");
  for (let i = 5; i >= 0; i--) arr.push(start.subtract(i, "month"));
  return arr;
});

// ---- 1. Ticket volume ----
const volumeOption = computed<EChartsOption>(() => {
  void dataTheme.value;
  const months = last6Months.value;
  const labels = months.map((m) => m.format("MMM"));
  const counts = months.map(
    (m) =>
      tickets.value.filter(
        (t) => t.creation && dayjs(t.creation).isSame(m, "month")
      ).length
  );
  return {
    grid: { left: 36, right: 12, top: 16, bottom: 24 },
    xAxis: {
      type: "category",
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: cssVar("--outline-gray-2") } },
      axisLabel: { color: cssVar("--ink-gray-6") },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: cssVar("--ink-gray-5") },
      splitLine: { lineStyle: { color: cssVar("--outline-gray-1") } },
    },
    tooltip: { trigger: "axis" },
    series: [
      {
        type: "line",
        data: counts,
        smooth: true,
        symbol: "circle",
        symbolSize: 7,
        lineStyle: { width: 2.5, color: "#3b82f6" },
        itemStyle: { color: "#3b82f6" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(59,130,246,0.35)" },
              { offset: 1, color: "rgba(59,130,246,0)" },
            ],
          },
        },
      },
    ],
  };
});

// ---- 2. Status breakdown ----
const statusPalette = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ec4899",
  "#8b5cf6",
  "#06b6d4",
  "#f43f5e",
  "#64748b",
];
const statusOption = computed<EChartsOption>(() => {
  void dataTheme.value;
  const map: Record<string, number> = {};
  tickets.value.forEach((t) => {
    const s = t.status || __("Unknown");
    map[s] = (map[s] || 0) + 1;
  });
  const data = Object.entries(map).map(([name, value], i) => ({
    name,
    value,
    itemStyle: { color: statusPalette[i % statusPalette.length] },
  }));
  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: {
      bottom: 0,
      textStyle: { color: cssVar("--ink-gray-6"), fontSize: 11 },
      icon: "circle",
    },
    series: [
      {
        type: "pie",
        radius: ["45%", "70%"],
        center: ["50%", "44%"],
        avoidLabelOverlap: true,
        label: { show: false },
        data,
      },
    ],
  };
});

// ---- 3. Avg resolution time trend ----
const hasResolved = computed(() =>
  tickets.value.some((t) => t.resolution_date && t.resolution_time)
);
const resolutionOption = computed<EChartsOption>(() => {
  void dataTheme.value;
  const months = last6Months.value;
  const labels = months.map((m) => m.format("MMM"));
  const avgs = months.map((m) => {
    const resolved = tickets.value.filter(
      (t) =>
        t.resolution_date &&
        t.resolution_time &&
        dayjs(t.resolution_date).isSame(m, "month")
    );
    if (!resolved.length) return 0;
    const total = resolved.reduce(
      (sum, t) => sum + (t.resolution_time || 0),
      0
    );
    return Math.round(total / resolved.length);
  });
  return {
    grid: { left: 48, right: 12, top: 16, bottom: 24 },
    xAxis: {
      type: "category",
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: cssVar("--outline-gray-2") } },
      axisLabel: { color: cssVar("--ink-gray-6") },
    },
    yAxis: {
      type: "value",
      axisLabel: {
        color: cssVar("--ink-gray-5"),
        formatter: (v: number) => {
          if (v <= 0) return "0";
          if (v < 3600) return Math.round(v / 60) + "m";
          if (v < 86400) return Math.round(v / 3600) + "h";
          return Math.round(v / 86400) + "d";
        },
      },
      splitLine: { lineStyle: { color: cssVar("--outline-gray-1") } },
    },
    tooltip: {
      trigger: "axis",
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params;
        const secs = p.value || 0;
        const human =
          secs > 0
            ? formatTime(secs, { day: true, hour: true, minute: true })
            : __("No data");
        return `${p.axisValue}<br/><b>${human}</b>`;
      },
    },
    series: [
      {
        type: "bar",
        data: avgs,
        barWidth: "45%",
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "#f59e0b" },
              { offset: 1, color: "#fbbf24" },
            ],
          },
        },
      },
    ],
  };
});

// ---- 4. CSAT ratings ----
const ratingCounts = computed(() => {
  const counts = [0, 0, 0, 0, 0]; // 1★..5★
  tickets.value.forEach((t) => {
    const r = t.feedback_rating;
    if (typeof r === "number" && r > 0 && r <= 1) {
      const stars = Math.min(5, Math.max(1, Math.round(r * 5)));
      counts[stars - 1] += 1;
    }
  });
  return counts;
});
const hasRatings = computed(() =>
  ratingCounts.value.some((c) => c > 0)
);
const avgRating = computed(() => {
  const counts = ratingCounts.value;
  const total = counts.reduce((s, c) => s + c, 0);
  if (!total) return "0";
  const weighted = counts.reduce((s, c, i) => s + c * (i + 1), 0);
  return (weighted / total).toFixed(1);
});
const ratingOption = computed<EChartsOption>(() => {
  void dataTheme.value;
  const counts = ratingCounts.value;
  const max = Math.max(...counts);
  return {
    grid: { left: 30, right: 12, top: 16, bottom: 24 },
    xAxis: {
      type: "category",
      data: ["1★", "2★", "3★", "4★", "5★"],
      axisTick: { show: false },
      axisLine: { lineStyle: { color: cssVar("--outline-gray-2") } },
      axisLabel: { color: cssVar("--ink-gray-6") },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: cssVar("--ink-gray-5") },
      splitLine: { lineStyle: { color: cssVar("--outline-gray-1") } },
    },
    tooltip: { trigger: "axis" },
    series: [
      {
        type: "bar",
        data: counts.map((value) => ({
          value,
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: value > 0 && value === max ? "#f43f5e" : "#fda4af",
          },
        })),
        barWidth: "55%",
      },
    ],
  };
});
</script>
