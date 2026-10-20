<template>
  <div v-if="data && data.status_category !== 'Resolved'" class="px-4 md:px-10 pt-3 print:hidden">
    <div
      class="flex flex-wrap items-center gap-x-6 gap-y-3 rounded-lg border border-outline-gray-2 bg-surface-white px-4 py-3"
    >
      <div class="flex min-w-0 items-center gap-3">
        <Avatar
          size="lg"
          :label="data.assignee_name || '?'"
          :image="data.assignee_image || undefined"
        />
        <div class="min-w-0">
          <div class="truncate text-sm font-semibold text-ink-gray-9">
            {{
              data.assignee_name
                ? __("{0} is handling your ticket", [data.assignee_name])
                : __("Waiting for an agent")
            }}
          </div>
          <div class="text-xs text-ink-gray-6">
            {{
              data.assignee_name
                ? __("You'll get their replies here and by email.")
                : __("An agent will pick this up shortly.")
            }}
          </div>
        </div>
      </div>
      <div v-if="data.resolution_eta" class="flex items-center gap-2">
        <LucideCalendarClock
          class="size-4 shrink-0"
          :class="overdue ? 'text-amber-600' : 'text-ink-gray-5'"
        />
        <div class="leading-tight">
          <div class="text-xs text-ink-gray-5">
            {{ overdue ? __("Was expected by") : __("Expected resolution") }}
          </div>
          <div class="text-sm font-medium" :class="overdue ? 'text-amber-700' : 'text-ink-gray-9'">
            {{ label }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from "vue";
import { Avatar, dayjs } from "frappe-ui";
import { ITicket } from "@/pages/ticket/symbols";
import { __ } from "@/translation";
import LucideCalendarClock from "~icons/lucide/calendar-clock";

// The customer's view of who is on their ticket and when it should be done.
const ticket = inject(ITicket);
const data = computed<any>(() => ticket?.data);
const overdue = computed(
  () => !!data.value?.resolution_eta && dayjs(data.value.resolution_eta).isBefore(dayjs())
);
const label = computed(() =>
  data.value?.resolution_eta ? dayjs(data.value.resolution_eta).format("ddd D MMM, HH:mm") : ""
);
</script>
