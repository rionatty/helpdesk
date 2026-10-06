<template>
  <section v-if="cards.data?.length" class="flex flex-col gap-4">
    <div class="flex items-center justify-between px-4 md:px-8">
      <h3 class="executive-heading text-lg text-ink-gray-9">{{ __("Job cards") }}</h3>
      <span v-if="toSign" class="text-sm font-medium text-blue-700">
        {{ __("{0} waiting for your signature", [toSign]) }}
      </span>
    </div>
    <div class="px-4 md:px-8">
      <ul
        class="executive-card flex flex-col divide-y divide-outline-gray-1 overflow-hidden"
      >
        <li
          v-for="c in cards.data.slice(0, shown)"
          :key="c.name"
          class="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-medium text-ink-gray-9">{{ c.name }}</span>
              <Badge variant="subtle" :label="statusLabel(c.status)" :theme="statusTheme(c.status)" />
            </div>
            <div class="mt-0.5 text-sm text-ink-gray-6">
              {{ longDate(c.date) }} · {{ __(c.service_type) }} · {{ c.technician_name }}
              · {{ __("{0} h", [fmt(c.total_hours)]) }}
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <Button
              :label="__('View or print')"
              variant="subtle"
              @click="printJobCard(c.name, false)"
            >
              <template #prefix><LucidePrinter class="size-4" /></template>
            </Button>
            <Button
              v-if="c.status === 'Completed'"
              variant="solid"
              :label="__('Sign')"
              @click="startSign(c)"
            />
          </div>
        </li>
      </ul>
      <button
        v-if="cards.data.length > shown"
        type="button"
        class="mt-2 text-sm font-medium text-ink-gray-6 hover:text-ink-gray-9 hover:underline"
        @click="shown += 10"
      >
        {{ __("Show more") }}
      </button>
    </div>
    <JobCardSignDialog
      v-if="signing"
      v-model="showSign"
      :card="signing"
      @signed="cards.reload()"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Badge, Button, createResource, dayjs } from "frappe-ui";
import { useAuthStore } from "@/stores/auth";
import { __ } from "@/translation";
import LucidePrinter from "~icons/lucide/printer";
import JobCardSignDialog from "@/components/jobcards/JobCardSignDialog.vue";
import { printJobCard } from "@/components/jobcards/print";

const cards = createResource({
  url: "helpdesk.api.job_card.get_my_job_cards",
  auto: true,
  // Optional section: if it can't load, the home page goes without it.
  onError: (e: any) => console.warn("[helpdesk] job cards:", e),
});

const authStore = useAuthStore();
const shown = ref(5);
const toSign = computed(
  () => (cards.data || []).filter((c: any) => c.status === "Completed").length
);

const showSign = ref(false);
const signing = ref<any>(null);

function startSign(c: any) {
  // The signer is usually the person signed in: start from their name.
  signing.value = { name: c.name, contact_name: authStore.userName || "" };
  showSign.value = true;
}

function statusLabel(status: string) {
  if (status === "Completed") return __("Ready to sign");
  if (status === "Open") return __("In progress");
  return __(status);
}

function statusTheme(status: string) {
  return ({ Signed: "green", Completed: "blue" } as Record<string, string>)[status] || "gray";
}

function fmt(h: number) {
  return String(Math.round((Number(h) || 0) * 100) / 100);
}

function longDate(d: string) {
  return d ? dayjs(d).format("D MMM YYYY") : "";
}
</script>
