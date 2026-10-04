<template>
  <section v-if="plans.data?.length" class="flex flex-col gap-4">
    <div class="flex items-center justify-between px-4 md:px-8">
      <h3 class="executive-heading text-lg text-ink-gray-9">
        {{ plans.data.length > 1 ? __("Your support plans") : __("Your support plan") }}
      </h3>
    </div>
    <div class="grid grid-cols-1 gap-4 px-4 md:px-8 lg:grid-cols-2">
      <div
        v-for="p in plans.data"
        :key="p.name"
        class="executive-card flex flex-col gap-4 p-5"
      >
        <div class="flex items-start gap-3">
          <div
            class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 shadow-md"
          >
            <LucideTimer class="size-5 text-white" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="truncate font-semibold text-ink-gray-9" :title="p.contract_name">
              {{ p.contract_name }}
            </div>
            <div class="text-sm text-ink-gray-6">{{ periodText(p) }}</div>
          </div>
        </div>

        <div class="flex flex-col gap-2">
          <div class="flex items-baseline justify-between gap-2">
            <span class="text-2xl font-bold text-ink-gray-9">
              {{ fmt(p.used) }}
              <span class="text-base font-medium text-ink-gray-6">
                / {{ __("{0} hours", [fmt(p.included)]) }}
              </span>
            </span>
            <span class="text-sm font-medium" :class="leftClass(p)">
              {{ leftLabel(p) }}
            </span>
          </div>
          <div
            class="h-2.5 overflow-hidden rounded-full bg-surface-gray-2"
            role="progressbar"
            :aria-valuenow="Math.min(100, p.pct)"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="__('Support hours used')"
          >
            <div
              class="h-full rounded-full"
              :class="barClass(p)"
              :style="{ width: `${Math.min(100, Math.max(0, p.pct))}%` }"
            />
          </div>
          <div v-if="renewText(p)" class="text-xs text-ink-gray-5">
            {{ renewText(p) }}
          </div>
        </div>

        <div v-if="p.entries.length">
          <button
            type="button"
            class="flex items-center gap-1 text-sm font-medium text-ink-gray-7 hover:text-ink-gray-9"
            :aria-expanded="!!open[p.name]"
            @click="open[p.name] = !open[p.name]"
          >
            <LucideChevronRight
              class="size-4 transition-transform"
              :class="open[p.name] && 'rotate-90'"
            />
            {{ __("Work this period ({0})", [p.entries.length]) }}
          </button>
          <ul
            v-if="open[p.name]"
            class="mt-2 flex flex-col divide-y divide-outline-gray-1"
          >
            <li
              v-for="(e, i) in p.entries"
              :key="i"
              class="flex items-start gap-3 py-2 text-sm"
            >
              <span class="w-16 shrink-0 text-ink-gray-5">{{ shortDate(e.date) }}</span>
              <span class="min-w-0 flex-1 break-words text-ink-gray-8">{{ e.what }}</span>
              <span class="shrink-0 font-medium text-ink-gray-8">{{ fmt(e.hours) }} h</span>
            </li>
          </ul>
        </div>
        <p v-else class="text-sm text-ink-gray-5">
          {{ __("No support time used yet this period.") }}
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive } from "vue";
import { createResource, dayjs } from "frappe-ui";
import { __ } from "@/translation";
import LucideTimer from "~icons/lucide/timer";
import LucideChevronRight from "~icons/lucide/chevron-right";

const plans = createResource({
  url: "helpdesk.api.contracts.get_my_support_plans",
  auto: true,
  // Optional card: if it can't load, the home page simply goes without it.
  onError: (e: any) => console.warn("[helpdesk] support plan:", e),
});

const open = reactive<Record<string, boolean>>({});

function fmt(h: number) {
  return String(Math.round((Number(h) || 0) * 100) / 100);
}

function shortDate(d: string) {
  return dayjs(d).format("D MMM");
}

function longDate(d: string) {
  return dayjs(d).format("D MMM YYYY");
}

function periodText(p: any) {
  if (p.period === "Whole contract") return __("Hours for the whole contract");
  return p.period_label;
}

function renewText(p: any) {
  if (p.period === "Whole contract") {
    return p.end_date ? __("Valid until {0}", [longDate(p.end_date)]) : "";
  }
  const renews = dayjs(p.period_to).add(1, "day");
  if (p.end_date && renews.isAfter(dayjs(p.end_date))) {
    return __("Plan ends {0}", [longDate(p.end_date)]);
  }
  return __("Hours renew on {0}", [longDate(renews.format("YYYY-MM-DD"))]);
}

function leftLabel(p: any) {
  return p.remaining >= 0
    ? __("{0} h left", [fmt(p.remaining)])
    : __("{0} h over your plan", [fmt(-p.remaining)]);
}

function leftClass(p: any) {
  if (p.remaining < 0) return "text-ink-red-3";
  if (p.pct >= p.alert_at) return "text-ink-amber-3";
  return "text-ink-green-3";
}

function barClass(p: any) {
  if (p.pct >= 100) return "bg-red-500";
  if (p.pct >= p.alert_at) return "bg-amber-500";
  return "bg-blue-500";
}
</script>
