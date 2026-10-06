<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between gap-2">
      <span class="text-base font-semibold text-ink-gray-8">{{ __("Job cards") }}</span>
      <Button size="sm" variant="subtle" :label="__('New job card')" @click="openCard(null)">
        <template #prefix><LucideFileText class="size-3.5" /></template>
      </Button>
    </div>
    <p v-if="!cards.length" class="text-xs text-ink-gray-5">
      {{ __("A printable record of the work, for the client to sign.") }}
    </p>
    <ul v-else class="flex flex-col divide-y divide-outline-gray-1">
      <li v-for="c in cards" :key="c.name" class="flex items-center gap-2 py-1.5 text-xs">
        <button
          type="button"
          class="min-w-0 flex-1 rounded text-left hover:bg-surface-gray-1"
          @click="openCard(c.name)"
        >
          <div class="flex items-center gap-1.5">
            <span class="font-medium text-ink-gray-8">{{ c.name }}</span>
            <Badge size="sm" variant="subtle" :label="__(c.status)" :theme="statusTheme(c.status)" />
          </div>
          <div class="truncate text-ink-gray-5">
            {{ shortDate(c.date) }} · {{ fmt(c.total_hours) }} h · {{ __(c.service_type) }}
          </div>
        </button>
        <Button
          size="sm"
          variant="ghost"
          :aria-label="__('Print {0}', [c.name])"
          :title="__('Print')"
          @click="printJobCard(c.name)"
        >
          <LucidePrinter class="size-3.5" />
        </Button>
      </li>
    </ul>
    <JobCardDialog
      v-model="showCard"
      :name="cardName"
      :ticket="ticketId"
      @changed="changed"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Badge, Button, createResource, dayjs } from "frappe-ui";
import { __ } from "@/translation";
import LucideFileText from "~icons/lucide/file-text";
import LucidePrinter from "~icons/lucide/printer";
import JobCardDialog from "@/components/jobcards/JobCardDialog.vue";
import { printJobCard } from "@/components/jobcards/print";

const props = defineProps<{ ticketId?: string }>();
// A card's time lines are logged time: the ticket's time panels refresh.
const emit = defineEmits<{ (e: "changed"): void }>();

const res = createResource({
  url: "helpdesk.api.job_card.list_job_cards",
  makeParams: () => ({ ticket: props.ticketId }),
  onError: (e: any) => console.warn("[helpdesk] job cards:", e),
});
const cards = computed<any[]>(() => res.data || []);

watch(
  () => props.ticketId,
  (id) => id && res.reload(),
  { immediate: true }
);

const showCard = ref(false);
const cardName = ref<string | null>(null);

function openCard(name: string | null) {
  cardName.value = name;
  showCard.value = true;
}

function changed(name: string | null) {
  if (name) cardName.value = name;
  res.reload();
  emit("changed");
}

function statusTheme(status: string) {
  return ({ Signed: "green", Completed: "blue", Cancelled: "red" } as Record<string, string>)[status] || "gray";
}

function fmt(h: number) {
  return String(Math.round((Number(h) || 0) * 100) / 100);
}

function shortDate(d: string) {
  return d ? dayjs(d).format("D MMM") : "";
}

defineExpose({ reload: () => res.reload() });
</script>
