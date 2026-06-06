<template>
  <div
    v-if="visibleSteps.length"
    class="px-6 md:px-10 pt-6"
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
          <span class="text-sm font-medium" :class="labelClass(i)">
            {{ __(step.label_customer || step.label_agent) }}
          </span>
        </div>
        <div
          v-if="i < visibleSteps.length - 1"
          class="h-px flex-1 mx-3 min-w-4"
          :class="i < currentIndex ? 'bg-surface-gray-7' : 'bg-outline-gray-2'"
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
import { ITicket } from "@/pages/ticket/symbols";
import { useTicketStatusStore } from "@/stores/ticketStatus";
import { HDTicketStatus } from "@/types/doctypes";
import { __ } from "@/translation";

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

function circleClass(_step: HDTicketStatus, i: number) {
  if (i < currentIndex.value) return "bg-surface-gray-7 text-white";
  if (i === currentIndex.value)
    return "bg-ink-gray-9 text-white ring-2 ring-offset-2 ring-ink-gray-3";
  return "bg-surface-gray-2 text-ink-gray-5";
}

function labelClass(i: number) {
  if (i === currentIndex.value) return "text-ink-gray-9";
  if (i < currentIndex.value) return "text-ink-gray-7";
  return "text-ink-gray-5";
}
</script>
