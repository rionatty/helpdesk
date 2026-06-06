<template>
  <div
    class="mx-6 md:mx-10 md:my-2 flex items-center justify-between text-lg font-medium mb-4 !mt-6 md:h-8 md:text-xl md:font-semibold md:text-ink-gray-8"
  >
    {{ __("Activity") }}
  </div>
  <div class="overflow-auto px-6 md:px-10 grow">
    <div
      v-for="(c, i) in communications"
      :id="c.name"
      :key="c.name"
      class="flex items-between justify-center gap-4 relative"
      :class="i === 0 && 'mt-4'"
    >
      <div
        class="w-full activity grid grid-cols-[30px_minmax(auto,_1fr)] gap-2 sm:gap-4 h-full"
      >
        <div
          class="relative flex justify-center after:absolute after:start-[50%] after:top-3 after:-z-10 after:border-s after:border-outline-gray-1"
          :class="[
            i != communications.length - 1 ? 'after:h-full' : 'after:h-5',
          ]"
        >
          <Avatar
            size="lg"
            :label="c.user.name"
            :image="c.user.image"
            class="mt-1.5 relative"
          />
        </div>
        <TicketCommunication
          :content="c.content"
          :date="c.creation"
          :user="c.user"
          :sender-image="c.sender"
          :cc="c.cc || ''"
          :bcc="c.bcc || ''"
          :attachments="c.attachments"
          :from-customer="isFromCustomer(c)"
        />
      </div>
    </div>
    <div
      v-if="showWaitingPanel"
      class="grid grid-cols-[30px_minmax(auto,_1fr)] gap-2 sm:gap-4 my-2"
    >
      <div class="flex justify-center pt-1">
        <div
          class="flex items-center justify-center size-7 rounded-full bg-surface-amber-2 text-amber-700"
        >
          <LucideClock class="size-4" />
        </div>
      </div>
      <div
        class="flex-1 rounded-md border border-outline-amber-1 bg-surface-amber-1 px-4 py-3"
      >
        <div class="font-medium text-ink-gray-8">
          {{ __("We've received your ticket") }}
        </div>
        <div class="text-sm text-ink-gray-6 mt-0.5">
          {{ waitingText }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { dateFormat, dateTooltipFormat, formatTime, isElementInViewport } from "@/utils";
import { __ } from "@/translation";
import { Avatar, dayjs } from "frappe-ui";
import { computed, inject, nextTick, watch } from "vue";
import { useRoute } from "vue-router";
import TicketCommunication from "./TicketCommunication.vue";
import { ITicket } from "./symbols";

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
