<template>
  <div class="border rounded-md p-5 flex flex-col gap-4 bg-surface-white">
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-center gap-2">
        <div
          class="size-7 rounded-lg bg-surface-amber-2 flex items-center justify-center shrink-0"
        >
          <LucideLayers class="size-4 text-amber-700" />
        </div>
        <div>
          <div class="text-base font-semibold text-ink-gray-8">
            {{ __("Backlog & Aging") }}
          </div>
          <div class="text-xs text-ink-gray-5">
            {{ __("Currently open — {0} tickets", [total]) }}
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

    <div v-if="resource.loading" class="flex flex-col gap-2.5 py-2">
      <div
        v-for="i in 4"
        :key="i"
        class="h-5 rounded bg-surface-gray-2 animate-pulse"
      />
    </div>

    <template v-else>
      <!-- Age buckets -->
      <div class="flex flex-col gap-2.5">
        <div
          v-for="b in buckets"
          :key="b.label"
          class="flex items-center gap-3"
        >
          <span class="w-20 text-xs font-medium text-ink-gray-6 shrink-0">
            {{ b.label }}
          </span>
          <div class="flex-1 h-5 rounded bg-surface-gray-2 overflow-hidden">
            <div
              class="h-full rounded transition-all duration-500"
              :class="b.color"
              :style="{ width: barWidth(b.count) }"
            />
          </div>
          <span
            class="w-8 text-sm font-semibold text-ink-gray-8 text-right shrink-0"
          >
            {{ b.count }}
          </span>
        </div>
      </div>

      <!-- Oldest open tickets -->
      <div v-if="oldest.length" class="mt-1">
        <div
          class="text-xs font-semibold uppercase tracking-wide text-ink-gray-5 mb-1"
        >
          {{ __("Oldest open tickets") }}
        </div>
        <div class="flex flex-col divide-y divide-outline-gray-1">
          <button
            v-for="t in oldest"
            :key="t.name"
            type="button"
            class="flex items-center justify-between gap-3 py-2 px-1 text-start rounded hover:bg-surface-menu-bar transition-colors"
            @click="open(t.name)"
          >
            <div class="min-w-0">
              <div class="text-sm text-ink-gray-8 truncate">
                #{{ t.name }} · {{ t.subject || __("(no subject)") }}
              </div>
              <div class="text-xs text-ink-gray-5 truncate">
                {{ t.agent || __("Unassigned") }} · {{ t.priority || "—" }}
              </div>
            </div>
            <Badge
              :label="ageLabel(t.age_days)"
              :theme="ageTheme(t.age_days)"
              variant="subtle"
            />
          </button>
        </div>
      </div>

      <div
        v-if="total === 0"
        class="text-sm text-ink-gray-5 py-4 text-center"
      >
        {{ __("No open tickets — backlog is clear.") }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { Badge, Button, Tooltip, createResource } from "frappe-ui";
import { useRouter } from "vue-router";
import { __ } from "@/translation";
import { downloadCsv } from "@/utils";
import LucideLayers from "~icons/lucide/layers";
import LucideDownload from "~icons/lucide/download";

interface P {
  team?: string | null;
  agent?: string | null;
}
const props = withDefaults(defineProps<P>(), { team: null, agent: null });
const router = useRouter();

interface Bucket {
  label: string;
  count: number;
}
interface OldestTicket {
  name: string;
  subject: string;
  status: string;
  priority: string;
  age_days: number;
  agent: string | null;
}

const resource = createResource({
  url: "helpdesk.api.dashboard.get_dashboard_data",
  makeParams: () => ({
    dashboard_type: "backlog",
    filters: { team: props.team, agent: props.agent },
  }),
  auto: true,
});

watch(
  () => [props.team, props.agent],
  () => resource.reload()
);

const buckets = computed(() => {
  const raw: Bucket[] = resource.data?.buckets || [];
  const colorByLabel: Record<string, string> = {
    "< 1 day": "bg-green-500",
    "1–3 days": "bg-blue-500",
    "3–7 days": "bg-amber-500",
    "> 7 days": "bg-red-500",
  };
  return raw.map((b) => ({ ...b, color: colorByLabel[b.label] || "bg-gray-400" }));
});
const oldest = computed<OldestTicket[]>(() => resource.data?.oldest || []);
const total = computed<number>(() => resource.data?.total || 0);
const maxCount = computed(() =>
  Math.max(1, ...buckets.value.map((b) => b.count))
);

function barWidth(count: number) {
  return `${Math.round((count / maxCount.value) * 100)}%`;
}

function ageLabel(days: number) {
  if (days <= 0) return __("today");
  return __("{0}d", [days]);
}
function ageTheme(days: number) {
  if (days < 1) return "green";
  if (days < 3) return "blue";
  if (days < 7) return "orange";
  return "red";
}

function open(name: string) {
  router.push({ name: "TicketAgent", params: { ticketId: name } });
}

function exportCsv() {
  const rows: (string | number)[][] = buckets.value.map((b) => [
    b.label,
    b.count,
  ]);
  rows.push(["", ""]);
  rows.push([__("Oldest open tickets"), ""]);
  oldest.value.forEach((t) =>
    rows.push([`#${t.name} ${t.subject || ""}`.trim(), `${t.age_days}d`])
  );
  downloadCsv("helpdesk-backlog", [__("Age"), __("Count")], rows);
}
</script>
