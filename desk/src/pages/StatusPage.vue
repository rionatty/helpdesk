<template>
  <div class="min-h-full bg-surface-menu-bar">
    <div class="max-w-3xl mx-auto px-4 py-10 md:py-16 flex flex-col gap-6">
      <header class="flex flex-col items-center text-center gap-3">
        <div
          class="flex items-center gap-2 px-3 py-1 rounded-full border border-outline-green-1 bg-surface-green-2"
        >
          <span class="size-2 rounded-full bg-green-500 animate-pulse" />
          <span class="text-sm font-medium text-green-800">
            {{ __("All systems operational") }}
          </span>
        </div>
        <h1 class="text-2xl md:text-3xl font-semibold text-ink-gray-9">
          {{ brandName }} {{ __("status") }}
        </h1>
        <div class="text-sm text-ink-gray-5">
          {{ __("Last updated") }}
          {{ now }}
        </div>
      </header>

      <section
        class="rounded-lg border border-outline-gray-2 bg-surface-white overflow-hidden"
      >
        <div
          v-for="(svc, i) in services"
          :key="svc.name"
          class="flex items-center justify-between px-4 py-3"
          :class="i > 0 ? 'border-t border-outline-gray-1' : ''"
        >
          <div>
            <div class="font-medium text-ink-gray-8">{{ __(svc.name) }}</div>
            <div class="text-xs text-ink-gray-5">{{ __(svc.description) }}</div>
          </div>
          <div class="flex items-center gap-2">
            <span class="size-2 rounded-full bg-green-500" />
            <span class="text-sm text-green-700 font-medium">
              {{ __("Operational") }}
            </span>
          </div>
        </div>
      </section>

      <footer class="flex flex-col items-center gap-2 text-sm text-ink-gray-5">
        <div>
          {{ __("Something not working as expected?") }}
        </div>
        <RouterLink
          :to="{ name: 'TicketNew' }"
          class="text-ink-gray-9 underline hover:text-ink-gray-8"
        >
          {{ __("Open a support ticket") }}
        </RouterLink>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { usePageMeta, dayjs } from "frappe-ui";
import { useConfigStore } from "@/stores/config";
import { __ } from "@/translation";

const config = useConfigStore();

const brandName = computed(() => config.brandName || __("Service"));

const now = computed(() =>
  dayjs().format("MMM D, YYYY [at] h:mm A")
);

const services = [
  {
    name: "Customer Portal",
    description: "Submitting and tracking tickets",
  },
  {
    name: "Knowledge Base",
    description: "Browsing and searching articles",
  },
  {
    name: "Email Ingestion",
    description: "Tickets sent via email reach the queue",
  },
  {
    name: "Notifications",
    description: "Email and in-app updates",
  },
];

usePageMeta(() => ({
  title: __("System status"),
}));
</script>
