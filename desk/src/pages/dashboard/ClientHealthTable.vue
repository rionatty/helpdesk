<template>
  <div class="border rounded-md p-5 flex flex-col gap-4 bg-surface-white">
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-center gap-2">
        <div
          class="size-7 rounded-lg bg-surface-blue-2 flex items-center justify-center shrink-0"
        >
          <LucideBuilding2 class="size-4 text-blue-700" />
        </div>
        <div>
          <div class="text-base font-semibold text-ink-gray-8">
            {{ __("Client Health") }}
          </div>
          <div class="text-xs text-ink-gray-5">
            {{ __("Tickets per client for the selected period & team") }}
          </div>
        </div>
      </div>
      <Tooltip :text="__('Export CSV')">
        <Button
          variant="ghost"
          class="print:hidden"
          :aria-label="__('Export CSV')"
          @click="exportCsv"
        >
          <template #icon><LucideDownload class="size-4" /></template>
        </Button>
      </Tooltip>
    </div>

    <div v-if="resource.loading" class="flex flex-col gap-2 py-2">
      <div
        v-for="i in 5"
        :key="i"
        class="h-9 rounded bg-surface-gray-2 animate-pulse"
      />
    </div>

    <div v-else-if="!rows.length" class="text-sm text-ink-gray-5 py-6 text-center">
      {{ __("No client tickets for this selection.") }}
    </div>

    <div v-else class="overflow-x-auto">
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr class="border-b border-outline-gray-2">
            <th
              v-for="col in columns"
              :key="col.key"
              class="py-2 px-2 font-medium text-ink-gray-6 whitespace-nowrap select-none cursor-pointer hover:text-ink-gray-8"
              :class="col.key === 'customer' ? 'text-start' : 'text-end'"
              :title="col.hint"
              @click="setSort(col.key)"
            >
              <span
                class="inline-flex items-center gap-1"
                :class="col.key === 'customer' ? '' : 'flex-row-reverse'"
              >
                {{ col.label }}
                <LucideChevronUp
                  v-if="sortKey === col.key && sortDir === 'asc'"
                  class="size-3.5"
                />
                <LucideChevronDown v-else-if="sortKey === col.key" class="size-3.5" />
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in sortedRows"
            :key="r.customer"
            class="border-b border-outline-gray-1 hover:bg-surface-menu-bar transition-colors"
          >
            <td class="py-2 px-2">
              <div class="flex items-center gap-2 min-w-0">
                <Avatar size="sm" :label="r.customer" />
                <span class="truncate text-ink-gray-8">{{ r.customer }}</span>
              </div>
            </td>
            <td class="py-2 px-2 text-end text-ink-gray-8">{{ r.tickets }}</td>
            <td
              class="py-2 px-2 text-end"
              :class="r.open ? 'font-medium text-amber-700' : 'text-ink-gray-5'"
            >
              {{ r.open }}
            </td>
            <td class="py-2 px-2 text-end font-medium" :class="slaColor(r.sla_pct, r.resolved)">
              <template v-if="r.resolved">{{ r.sla_pct }}%</template>
              <span v-else class="text-ink-gray-4">—</span>
            </td>
            <td class="py-2 px-2 text-end text-ink-gray-8">{{ r.avg_first_response }}h</td>
            <td class="py-2 px-2 text-end text-ink-gray-8">{{ r.avg_resolution }}d</td>
            <td class="py-2 px-2 text-end" :class="r.avg_feedback && r.avg_feedback < 3 ? 'text-red-700 font-medium' : 'text-ink-gray-8'">
              <span v-if="r.avg_feedback > 0">{{ r.avg_feedback }}★</span>
              <span v-else class="text-ink-gray-4">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Avatar, Button, Tooltip, createResource } from "frappe-ui";
import { __ } from "@/translation";
import { downloadCsv } from "@/utils";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideDownload from "~icons/lucide/download";
import LucideChevronUp from "~icons/lucide/chevron-up";
import LucideChevronDown from "~icons/lucide/chevron-down";

interface P {
  fromDate?: string | null;
  toDate?: string | null;
  team?: string | null;
  agent?: string | null;
}
const props = withDefaults(defineProps<P>(), {
  fromDate: null,
  toDate: null,
  team: null,
  agent: null,
});

interface ClientRow {
  customer: string;
  tickets: number;
  open: number;
  resolved: number;
  sla_pct: number;
  avg_first_response: number;
  avg_resolution: number;
  avg_feedback: number;
}

const columns = [
  { key: "customer", label: __("Client"), hint: "" },
  { key: "tickets", label: __("Tickets"), hint: __("Tickets raised in the period") },
  { key: "open", label: __("Still open"), hint: __("Of those, how many are still open") },
  { key: "sla_pct", label: __("SLA %"), hint: __("Resolved tickets that met their SLA") },
  { key: "avg_first_response", label: __("Avg 1st Resp"), hint: "" },
  { key: "avg_resolution", label: __("Avg Resolution"), hint: "" },
  { key: "avg_feedback", label: __("CSAT"), hint: __("Average feedback rating") },
] as const;

const resource = createResource({
  url: "helpdesk.api.dashboard.get_dashboard_data",
  makeParams: () => ({
    dashboard_type: "client_health",
    filters: {
      from_date: props.fromDate,
      to_date: props.toDate,
      team: props.team,
      agent: props.agent,
    },
  }),
  auto: true,
});

watch(
  () => [props.fromDate, props.toDate, props.team, props.agent],
  () => resource.reload()
);

const rows = computed<ClientRow[]>(() => resource.data || []);

const sortKey = ref<string>("tickets");
const sortDir = ref<"asc" | "desc">("desc");

function setSort(key: string) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = key;
    // Text column defaults to A to Z, numeric columns to high to low.
    sortDir.value = key === "customer" ? "asc" : "desc";
  }
}

const sortedRows = computed(() => {
  const key = sortKey.value;
  const dir = sortDir.value === "asc" ? 1 : -1;
  return [...rows.value].sort((a, b) => {
    const av = a[key as keyof ClientRow];
    const bv = b[key as keyof ClientRow];
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
    return String(av).localeCompare(String(bv)) * dir;
  });
});

function slaColor(pct: number, resolved: number) {
  if (!resolved) return "";
  if (pct >= 90) return "text-green-700";
  if (pct >= 70) return "text-amber-700";
  return "text-red-700";
}

function exportCsv() {
  downloadCsv(
    "helpdesk-client-health",
    [
      __("Client"),
      __("Tickets"),
      __("Still open"),
      __("Resolved"),
      __("SLA %"),
      __("Avg First Response (h)"),
      __("Avg Resolution (d)"),
      __("CSAT"),
    ],
    sortedRows.value.map((r) => [
      r.customer,
      r.tickets,
      r.open,
      r.resolved,
      r.sla_pct,
      r.avg_first_response,
      r.avg_resolution,
      r.avg_feedback,
    ])
  );
}
</script>
