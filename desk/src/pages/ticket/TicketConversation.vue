<template>
  <div
    class="mx-6 md:mx-10 md:my-2 flex items-center justify-between text-lg font-medium mb-4 !mt-6 md:h-8 md:text-xl md:font-semibold md:text-ink-gray-8"
  >
    {{ __("Activity") }}
  </div>
  <div class="overflow-auto px-6 md:px-10 grow">
    <template v-for="(item, i) in itemsWithDividers" :key="item.key">
      <div
        v-if="item.type === 'divider'"
        class="flex items-center gap-3 my-4 animate-in-soft"
      >
        <div class="flex-1 h-px bg-outline-gray-2" />
        <span
          class="text-xs font-semibold uppercase tracking-wide text-ink-gray-7 bg-white px-2"
        >
          {{ dayLabel(item.date) }}
        </span>
        <div class="flex-1 h-px bg-outline-gray-2" />
      </div>
      <div
        v-else
        :id="item.name"
        class="animate-in-fade mb-4"
        :class="i === 0 && 'mt-4'"
      >
        <!-- Chat row: customer messages lean right, support left -->
        <div
          class="flex items-end gap-2 sm:gap-3"
          :class="item.fromCustomer ? 'flex-row-reverse' : ''"
        >
          <Avatar
            size="lg"
            :label="item.user.name"
            :image="item.user.image"
            class="shrink-0 mb-1"
          />
          <TicketCommunication
            class="max-w-[85%] sm:max-w-[78%]"
            :content="item.content"
            :date="item.creation"
            :user="item.user"
            :cc="item.cc || ''"
            :bcc="item.bcc || ''"
            :attachments="item.attachments"
            :from-customer="item.fromCustomer"
            :is-self="item.isSelf"
          />
        </div>
      </div>
    </template>
    <div
      v-if="showWaitingPanel"
      class="grid grid-cols-[30px_minmax(auto,_1fr)] gap-2 sm:gap-4 my-2 animate-in-fade"
    >
      <div class="flex justify-center pt-1">
        <div
          class="flex items-center justify-center size-7 rounded-full bg-amber-500/20 text-amber-700 font-bold"
        >
          <LucideClock class="size-4" />
        </div>
      </div>
      <div
        class="flex-1 rounded-md border border-outline-amber-1 bg-surface-amber-1 px-4 py-3"
      >
        <div class="font-bold text-amber-900">
          {{ __("We've received your ticket") }}
        </div>
        <div class="text-sm text-ink-gray-6 mt-0.5">
          {{ waitingText }}
        </div>
      </div>
    </div>
    <div
      v-if="!communications || communications.length === 0"
      class="flex flex-col items-center justify-center h-full text-center py-12"
    >
      <LucideMessageSquare class="size-12 text-ink-gray-4 mb-3" />
      <p class="text-ink-gray-6 font-medium">{{ __("No messages yet") }}</p>
      <p class="text-sm text-ink-gray-5 mt-1">
        {{ __("Your reply will appear here") }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { dateFormat, dateTooltipFormat, formatTime, isElementInViewport } from "@/utils";
import { __ } from "@/translation";
import { useAuthStore } from "@/stores/auth";
import { Avatar, dayjs } from "frappe-ui";
import { computed, inject, nextTick, watch } from "vue";
import { useRoute } from "vue-router";
import TicketCommunication from "./TicketCommunication.vue";
import { ITicket } from "./symbols";
import LucideMessageSquare from "~icons/lucide/message-square";

const authStore = useAuthStore();

interface P {
  focus?: string;
}

const props = withDefaults(defineProps<P>(), {
  focus: "",
});
const route = useRoute();
const ticket = inject(ITicket);
const communications = computed(() => {
  const _communications = ticket.data.communications || [];
  return _communications.sort(
    (a, b) => new Date(a.creation) - new Date(b.creation)
  );
});

function isFromCustomer(c: any): boolean {
  const raisedBy = ticket.data?.raised_by;
  if (!raisedBy) return true;
  return c.sender === raisedBy;
}

function dayLabel(d: string): string {
  const day = dayjs(d).startOf("day");
  const today = dayjs().startOf("day");
  const diff = today.diff(day, "day");
  if (diff === 0) return __("Today");
  if (diff === 1) return __("Yesterday");
  if (diff < 7) return day.format("dddd");
  return day.format("MMM D, YYYY");
}

const itemsWithDividers = computed(() => {
  const out: any[] = [];
  let lastDay: string | null = null;
  const arr = communications.value;
  arr.forEach((c: any, i: number) => {
    const day = dayjs(c.creation).format("YYYY-MM-DD");
    if (day !== lastDay) {
      out.push({ type: "divider", date: c.creation, key: `d-${day}` });
      lastDay = day;
    }
    out.push({
      type: "message",
      ...c,
      key: c.name,
      isLast: i === arr.length - 1,
      fromCustomer: isFromCustomer(c),
      isSelf: c.sender === authStore.userId,
    });
  });
  return out;
});

const hasAgentReply = computed(() =>
  communications.value.some((c: any) => !isFromCustomer(c))
);

const showWaitingPanel = computed(
  () =>
    communications.value.length > 0 &&
    !hasAgentReply.value &&
    ticket.data?.status !== "Closed"
);

const waitingText = computed(() => {
  const responseBy = ticket.data?.response_by;
  if (!responseBy) return __("A support agent will reply shortly.");
  const due = dayjs(responseBy);
  if (due.isBefore(dayjs())) {
    return __("A support agent will reply shortly.");
  }
  const human = formatTime(due.diff(dayjs(), "s"));
  const exact = dateFormat(responseBy, dateTooltipFormat);
  return __("Expected first reply within {0} (by {1}).", [human, exact]);
});

function scroll(id: string) {
  const e = document.getElementById(id);
  if (!isElementInViewport(e)) {
    e.scrollIntoViewIfNeeded();
  }
}

watch(
  () => props.focus,
  (id: string) => scroll(id)
);
nextTick(() => {
  const hash = route.hash.slice(1);
  const id = hash || communications.value.slice(-1).pop()?.name;
  if (id) setTimeout(() => scroll(id), 1000);
});
</script>
