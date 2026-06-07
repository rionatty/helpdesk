<template>
  <div
    v-if="visibleSteps.length"
    class="px-4 md:px-10 pt-4 md:pt-6"
    role="group"
    :aria-label="__('Ticket progress')"
  >
    <ol class="flex items-center w-full overflow-x-auto pb-1">
      <li
        v-for="(step, i) in visibleSteps"
        :key="step.label_agent"
        class="flex items-center"
        :class="i === visibleSteps.length - 1 ? '' : 'flex-1 min-w-fit'"
      >
        <div
          class="flex items-center gap-2 whitespace-nowrap"
          :aria-current="i === currentIndex ? 'step' : undefined"
        >
          <div
            class="flex items-center justify-center rounded-full size-6 transition-colors"
            :class="circleClass(step, i)"
          >
            <LucideCheck v-if="i < currentIndex" class="size-3.5" />
            <span
              v-else
              class="size-2 rounded-full"
              :class="i === currentIndex ? 'bg-white' : 'bg-ink-gray-4'"
            />
          </div>
          <div class="flex flex-col leading-tight">
            <span class="text-sm font-medium" :class="labelClass(i)">
              {{ __(step.label_customer || step.label_agent) }}
            </span>
            <Tooltip
              v-if="stepTimestamp(step, i)"
              :text="dateFormat(stepTimestamp(step, i)!, dateTooltipFormat)"
            >
              <span class="text-xs text-ink-gray-5 whitespace-nowrap">
                {{ timeAgo(stepTimestamp(step, i)!) }}
              </span>
            </Tooltip>
          </div>
        </div>
        <div
          v-if="i < visibleSteps.length - 1"
          class="h-0.5 flex-1 mx-3 min-w-4 rounded-full"
          :class="i < currentIndex ? 'bg-green-500' : 'bg-outline-gray-2'"
          aria-hidden="true"
        />
      </li>
    </ol>
    <div
      v-if="currentIndex === -1 && ticket?.data?.status"
      class="mt-2 text-xs text-ink-gray-5"
    >
      {{ __("Current status") }}: {{ ticket.data.status }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from "vue";
import { Tooltip } from "frappe-ui";
import { ITicket } from "@/pages/ticket/symbols";
import { useTicketStatusStore } from "@/stores/ticketStatus";
import { HDTicketStatus } from "@/types/doctypes";
import { __ } from "@/translation";
import { dateFormat, dateTooltipFormat, timeAgo } from "@/utils";

const ticket = inject(ITicket);
const { statuses } = useTicketStatusStore();

const visibleSteps = computed<HDTicketStatus[]>(() => {
  const all = (statuses.data || []) as HDTicketStatus[];
  return all
    .filter((s) => s.enabled)
    .slice()
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
});

const currentIndex = computed(() => {
  const label = ticket?.data?.status;
  if (!label) return -1;
  return visibleSteps.value.findIndex(
    (s) => s.label_customer === label || s.label_agent === label
  );
});

const RING_COLOR: Record<string, string> = {
  Green: "ring-green-300",
  Blue: "ring-blue-300",
  Red: "ring-red-300",
  Orange: "ring-orange-300",
  Amber: "ring-amber-300",
  Yellow: "ring-yellow-300",
  Cyan: "ring-cyan-300",
  Teal: "ring-teal-300",
  Violet: "ring-violet-300",
  Purple: "ring-purple-300",
  Pink: "ring-pink-300",
  Gray: "ring-gray-300",
  Black: "ring-ink-gray-4",
};

const activeRingClass = computed(() => {
  const step = visibleSteps.value[currentIndex.value];
  const key = step?.color
    ? step.color.charAt(0).toUpperCase() + step.color.slice(1).toLowerCase()
    : "";
  return RING_COLOR[key] || "ring-ink-gray-3";
});

function circleClass(_step: HDTicketStatus, i: number) {
  if (i < currentIndex.value) return "bg-green-600 text-white";
  if (i === currentIndex.value)
    return `bg-blue-600 text-white ring-2 ring-offset-2 ${activeRingClass.value}`;
  return "bg-surface-white border-2 border-outline-gray-3 text-ink-gray-5";
}

function labelClass(i: number) {
  if (i === currentIndex.value) return "text-ink-gray-9 font-bold";
  if (i < currentIndex.value) return "text-ink-gray-8 font-semibold";
  return "text-ink-gray-6 font-medium";
}

function stepTimestamp(step: HDTicketStatus, i: number): string | undefined {
  const d = ticket?.data;
  if (!d || i > currentIndex.value) return undefined;
  if (step.category === "Open" && i === 0) return d.creation;
  if (step.category === "Paused") return d.first_responded_on || undefined;
  if (step.category === "Resolved") {
    const resolvedSteps = visibleSteps.value.filter(
      (s) => s.category === "Resolved"
    );
    const isFirstResolved =
      resolvedSteps[0]?.label_agent === step.label_agent;
    if (isFirstResolved) return d.resolution_date || undefined;
    if (i === currentIndex.value) return d.modified;
    return undefined;
  }
  return undefined;
}
</script>
