<template>
  <div
    class="w-full h-full overflow-hidden cursor-pointer hover:bg-surface-menu-bar transition-colors rounded"
    role="button"
    :aria-label="__('Open tickets for {0}', [title])"
    @click="goToFilteredList"
  >
    <CardBase
      :title="title"
      :text="chartData.average"
      :percentageChange="chartData.percentageChange"
      :chartConfig="chartConfig"
      :currentDuration="currentDuration"
      @changeDuration="changeDuration"
    >
      <template #actions>
        <Tooltip :text="__('Export CSV')" placement="top">
          <button
            class="p-1 text-ink-gray-5 hover:text-ink-gray-8 rounded transition-colors"
            :aria-label="__('Export CSV')"
            @click.stop="exportCsv"
          >
            <LucideDownload class="size-4" />
          </button>
        </Tooltip>
      </template>
    </CardBase>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type PropType } from "vue";
import CardBase from "./CardBase.vue";
import { createResource, dayjsLocal, Tooltip } from "frappe-ui";
import { useRouter } from "vue-router";
import { buildPercentageChange, downloadCsv, formatTime } from "@/utils";
import { __ } from "@/translation";
import { EChartsOption } from "echarts";

const router = useRouter();

interface AverageResponseData {
  percentage_change: number;
  average: number;
  data: { date: string; avg_time: number }[];
}

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  apiUrl: {
    type: String,
    required: true,
  },
  data: {
    type: Object as PropType<AverageResponseData>,
    required: true,
  },
  chartColor: {
    type: Object as PropType<{
      lineColor: string;
      gradientColor: { start: string; end: string };
    }>,
    required: true,
  },
});

const currentDuration = ref(__("Last month"));

const chartData = computed(() => {
  const isDataFetched = resource.fetched;
  const _data: AverageResponseData = isDataFetched ? resource.data : props.data;

  const dates = _data?.data?.map((item) => item.date) || [];
  const avg_time = _data?.data?.map((item) => item.avg_time) || [];
  const _percentageChange = _data?.percentage_change ?? null;
  const percentageChange = buildPercentageChange(_percentageChange);

  const average =
    formatTime(_data?.average || 0, { day: true, hour: true, minute: true }) ||
    "0m";

  return {
    data: avg_time,
    dates,
    percentageChange,
    average,
  };
});

const chartConfig = computed<EChartsOption>(() => {
  const color = props.chartColor.lineColor;
  const gradientColor = props.chartColor.gradientColor;
  return {
    xAxis: {
      type: "category",
      data: chartData.value.dates,
      show: false,
      boundaryGap: false,
    },
    yAxis: {
      type: "value",
      show: false,
    },
    series: [
      {
        data: chartData.value.data,
        type: "line",
        symbol: "none",
        lineStyle: {
          width: 1.25,
        },
        areaStyle: {
          opacity: 0.8,
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0,
                color: gradientColor.start,
              },
              {
                offset: 1,
                color: gradientColor.end,
              },
            ],
            global: false,
          },
        },
      },
    ],
    color: color,
    grid: {
      left: 2,
      right: 2,
      top: 2,
      bottom: 2,
    },
  };
});

const resource = createResource({
  url: props.apiUrl,
  type: "GET",
  makeParams: () => {
    return {
      period: currentDuration.value.toLowerCase(),
    };
  },
});

const changeDuration = (period: string) => {
  currentDuration.value = period;
  resource.submit();
};

function durationToDays(duration: string): number {
  if (duration === __("Last week")) return 7;
  if (duration === __("Last 3 months")) return 90;
  return 30;
}

const goToFilteredList = () => {
  const from = dayjsLocal()
    .subtract(durationToDays(currentDuration.value), "day")
    .format("YYYY-MM-DD HH:mm:ss");
  router.push({
    name: "TicketsAgent",
    query: { filters: JSON.stringify({ creation: [">=", from] }) },
  });
};

const exportCsv = () => {
  const { dates, data } = chartData.value;
  const rows = dates.map((d, i) => [d, data[i] ?? 0]);
  const slug = props.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  downloadCsv(
    `${slug}-${currentDuration.value.toLowerCase().replace(/\s+/g, "-")}`,
    [__("Date"), __("Avg time (seconds)")],
    rows as (string | number)[][]
  );
};

onMounted(() => {
  if (!props.data?.data) {
    resource.submit();
  }
});
</script>
