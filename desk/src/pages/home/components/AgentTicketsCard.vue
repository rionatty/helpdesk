<template>
  <div
    class="w-full h-full overflow-hidden cursor-pointer hover:bg-surface-menu-bar transition-colors rounded"
    role="button"
    :aria-label="__('Open my tickets list')"
    @click="goToFilteredList"
  >
    <CardBase
      :title="__('My Tickets')"
      :text="chartData.total"
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
import { __ } from "@/translation";
import { EChartsOption } from "echarts";
import { buildPercentageChange, downloadCsv } from "@/utils";

const router = useRouter();

interface Data {
  percentage_change: number;
  total: number;
  data: { date: string; count: number }[];
}

const props = defineProps({
  data: {
    type: Object as PropType<Data>,
    required: true,
  },
});

const currentDuration = ref(__("Last month"));

const chartColor = {
  lineColor: "#5597F3",
  gradientColor: { start: "#abccfc", end: "rgba(229,240,254,0)" },
};

const chartData = computed(() => {
  const _data: Data = getAgentTicketsResource.fetched
    ? getAgentTicketsResource.data
    : props.data;

  const _percentageChange = _data?.percentage_change ?? null;
  const total = _data?.total || 0;
  const dates = _data?.data?.map((item) => item.date) || [];
  const counts = _data?.data?.map((item) => item.count) || [];
  const percentageChange = buildPercentageChange(_percentageChange);

  return {
    data: counts,
    percentageChange,
    total,
    counts,
    dates,
  };
});

const chartConfig = computed<EChartsOption>(() => {
  const color = chartColor.lineColor;
  const gradientColor = chartColor.gradientColor;
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

const getAgentTicketsResource = createResource({
  url: "helpdesk.api.agent_home.agent_home.get_agent_tickets",
  type: "GET",
  makeParams: () => {
    return {
      period: currentDuration.value.toLowerCase(),
    };
  },
});

const changeDuration = (period: string) => {
  currentDuration.value = period;
  getAgentTicketsResource.submit();
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
  const filters = {
    _assign: ["LIKE", "%@me%"],
    creation: [">=", from],
  };
  router.push({
    name: "TicketsAgent",
    query: { filters: JSON.stringify(filters) },
  });
};

const exportCsv = () => {
  const { dates, counts } = chartData.value;
  const rows = dates.map((d, i) => [d, counts[i] ?? 0]);
  const slug = currentDuration.value.toLowerCase().replace(/\s+/g, "-");
  downloadCsv(
    `my-tickets-${slug}`,
    [__("Date"), __("Tickets")],
    rows as (string | number)[][]
  );
};

onMounted(() => {
  if (!props.data?.data) {
    getAgentTicketsResource.submit();
  }
});
</script>
