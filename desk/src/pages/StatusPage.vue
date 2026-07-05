<template>
  <div class="min-h-full bg-customer-portal">
    <LayoutHeader />
    <div class="max-w-3xl mx-auto px-4 py-10 md:py-16 flex flex-col gap-6">
      <header class="flex flex-col items-center text-center gap-3">
        <div
          class="flex items-center gap-2 px-3 py-1 rounded-full border"
          :class="overall.pill"
        >
          <span
            class="size-2 rounded-full"
            :class="[overall.dot, state === 'checking' ? 'animate-pulse' : '']"
          />
          <span class="text-sm font-medium" :class="overall.text">
            {{ overall.label }}
          </span>
        </div>
        <h1 class="executive-heading text-2xl md:text-3xl text-ink-gray-9">
          {{ brandName }} {{ __("status") }}
        </h1>
        <div v-if="checkedAt" class="text-sm text-ink-gray-5">
          {{ __("Last checked") }} {{ checkedAt }}
        </div>
      </header>

      <section class="executive-card overflow-hidden">
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
            <span class="size-2 rounded-full" :class="svc.status.dot" />
            <span class="text-sm font-medium" :class="svc.status.text">
              {{ svc.status.label }}
            </span>
          </div>
        </div>
      </section>

      <footer class="flex flex-col items-center gap-2 text-sm text-ink-gray-5">
        <div>{{ __("Something not working as expected?") }}</div>
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
import { computed, onMounted, ref } from "vue";
import { usePageMeta, dayjs } from "frappe-ui";
import { useConfigStore } from "@/stores/config";
import { __ } from "@/translation";
import { LayoutHeader } from "@/components";

const config = useConfigStore();
const brandName = computed(() => config.brandName || __("Service"));

// "checking" until the backend ping resolves; then "operational" or "degraded".
const state = ref<"checking" | "operational" | "degraded">("checking");
const checkedAt = ref("");

const OK = {
  dot: "bg-green-500",
  text: "text-green-700",
  label: __("Operational"),
};
const DOWN = { dot: "bg-red-500", text: "text-red-700", label: __("Unreachable") };
const WAIT = {
  dot: "bg-amber-400",
  text: "text-amber-700",
  label: __("Checking…"),
};

const overall = computed(() => {
  if (state.value === "operational")
    return {
      pill: "border-outline-green-1 bg-surface-green-2",
      dot: "bg-green-500",
      text: "text-green-800",
      label: __("All systems operational"),
    };
  if (state.value === "degraded")
    return {
      pill: "border-red-200 bg-red-50",
      dot: "bg-red-500",
      text: "text-red-800",
      label: __("We're having trouble reaching the service"),
    };
  return {
    pill: "border-outline-gray-2 bg-surface-gray-2",
    dot: "bg-amber-400",
    text: "text-ink-gray-7",
    label: __("Checking status…"),
  };
});

// Only report what we can actually verify: the portal (you loaded it) and the
// backend API (a live ping). No fabricated per-service uptime.
const services = computed(() => [
  {
    name: "Customer Portal",
    description: "Submitting and tracking tickets",
    status: OK, // you're viewing it, so it's up
  },
  {
    name: "Support API",
    description: "The backend that powers the portal",
    status: state.value === "operational" ? OK : state.value === "degraded" ? DOWN : WAIT,
  },
]);

onMounted(async () => {
  try {
    const res = await fetch("/api/method/frappe.ping", {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    state.value = res.ok ? "operational" : "degraded";
  } catch (e) {
    state.value = "degraded";
  }
  checkedAt.value = dayjs().format("MMM D, YYYY [at] h:mm A");
});

usePageMeta(() => ({ title: __("System status") }));
</script>
