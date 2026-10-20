<template>
  <div
    v-if="ticket?.doc && (assigned.length || eta)"
    class="mt-3 flex flex-col gap-2 rounded-md border p-2.5"
    :class="needsEta ? 'border-amber-300 bg-amber-50' : 'border-outline-gray-2'"
  >
    <div class="flex items-center justify-between gap-2">
      <span class="flex items-center gap-1.5 text-xs font-medium text-ink-gray-7">
        <LucideCalendarClock class="size-3.5" />
        {{ __("Expected resolution") }}
      </span>
      <button
        v-if="canSet && eta && !editing"
        type="button"
        class="text-xs text-ink-gray-6 hover:text-ink-gray-9 hover:underline"
        @click="editing = true"
      >
        {{ __("Change") }}
      </button>
    </div>

    <div v-if="eta && !editing" class="flex flex-col">
      <span class="text-sm font-medium" :class="overdue ? 'text-ink-red-3' : 'text-ink-gray-9'">
        {{ longLabel(eta) }}
      </span>
      <span class="text-xs" :class="overdue ? 'text-ink-red-3' : 'text-ink-gray-5'">
        {{ overdue ? __("Overdue {0}. Update the customer.", [fromNow(eta)]) : fromNow(eta) }}
      </span>
      <span class="mt-0.5 text-xs text-ink-gray-5">{{ __("The customer sees this.") }}</span>
    </div>

    <template v-else-if="canSet">
      <p class="text-xs text-ink-gray-7">{{ prompt }}</p>
      <div class="flex flex-wrap gap-1">
        <button
          v-for="q in QUICK"
          :key="q.hours"
          type="button"
          class="rounded bg-surface-white px-2 py-0.5 text-xs text-ink-gray-7 ring-1 ring-outline-gray-2 hover:bg-surface-gray-2 disabled:opacity-50"
          :disabled="setRes.loading"
          @click="save({ hours: q.hours })"
        >
          {{ q.label }}
        </button>
      </div>
      <div class="flex items-end gap-1.5">
        <FormControl
          v-model="custom"
          class="flex-1"
          type="datetime-local"
          :min="minLocal"
          :aria-label="__('Exact date and time')"
        />
        <Button
          size="sm"
          :label="__('Set')"
          :disabled="!custom"
          :loading="setRes.loading"
          @click="save({ eta: custom })"
        />
      </div>
      <label class="flex cursor-pointer items-center gap-1.5 text-xs text-ink-gray-7">
        <input v-model="notify" type="checkbox" class="size-3.5 accent-blue-600" />
        {{ ticket.doc.whatsapp_number ? __("Tell the customer on WhatsApp") : __("Email the customer") }}
      </label>
      <div v-if="eta" class="flex items-center justify-between">
        <button
          type="button"
          class="text-xs text-ink-gray-6 hover:text-ink-gray-9 hover:underline"
          @click="editing = false"
        >
          {{ __("Cancel") }}
        </button>
        <button
          type="button"
          class="text-xs text-ink-gray-6 hover:text-ink-red-3 hover:underline"
          @click="save({})"
        >
          {{ __("Clear") }}
        </button>
      </div>
    </template>

    <p v-else class="text-xs text-ink-gray-5">
      {{ __("Not set yet. The assigned agent sets it, and the customer sees it.") }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch } from "vue";
import { Button, FormControl, createResource, dayjs, toast } from "frappe-ui";
import { AssigneeSymbol, TicketSymbol } from "@/types";
import { useAuthStore } from "@/stores/auth";
import { __ } from "@/translation";
import LucideCalendarClock from "~icons/lucide/calendar-clock";

const ticket = inject(TicketSymbol)!;
const assigneeList = inject(AssigneeSymbol, null);
const authStore = useAuthStore();

const QUICK = [
  { hours: 1, label: __("1 hour") },
  { hours: 4, label: __("4 hours") },
  { hours: 8, label: __("8 hours") },
  { hours: 24, label: __("1 day") },
  { hours: 48, label: __("2 days") },
  { hours: 72, label: __("3 days") },
  { hours: 168, label: __("1 week") },
];

const editing = ref(false);
const custom = ref("");
const notify = ref(true);

// Who is assigned: the page's live assignee list, else the ticket's _assign.
const assigned = computed<string[]>(() => {
  const live = assigneeList?.value?.data;
  if (Array.isArray(live)) return live.map((a: any) => a.name).filter(Boolean);
  try {
    const value = JSON.parse(ticket.value?.doc?._assign || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
});
const eta = computed<string | null>(() => ticket.value?.doc?.resolution_eta || null);
const resolved = computed(() => ticket.value?.doc?.status_category === "Resolved");
const mine = computed(() => assigned.value.includes(authStore.userId));
const canSet = computed(() => !resolved.value && (mine.value || !!authStore.isManager));
const needsEta = computed(() => canSet.value && !eta.value && assigned.value.length > 0);
const overdue = computed(() => !!eta.value && !resolved.value && dayjs(eta.value).isBefore(dayjs()));

const prompt = computed(() =>
  mine.value
    ? __("You're handling this ticket. How long will it take to resolve? The customer sees this.")
    : __("No expected resolution yet. Set one for the customer.")
);

const minLocal = computed(() => dayjs().add(10, "minute").format("YYYY-MM-DDTHH:mm"));

watch(
  () => ticket.value?.doc?.name,
  () => {
    editing.value = false;
    custom.value = "";
    notify.value = true;
  }
);

const setRes = createResource({
  url: "helpdesk.api.assignment.set_resolution_eta",
  onError: () => {},
});

async function save(args: { hours?: number; eta?: string }) {
  try {
    const result = await setRes.submit({
      ticket: ticket.value.doc.name,
      hours: args.hours ?? null,
      eta: args.eta ?? null,
      notify: notify.value ? 1 : 0,
    });
    editing.value = false;
    custom.value = "";
    if (!result?.label) {
      toast.success(__("Expected resolution cleared"));
    } else if (result.customer_told) {
      toast.success(__("Expected resolution {0}. The customer will be told.", [result.label]));
    } else {
      toast.success(__("Expected resolution {0}", [result.label]));
    }
    ticket.value.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not set the expected resolution"));
  }
}

function longLabel(value: string) {
  return dayjs(value).format("ddd D MMM YYYY, HH:mm");
}

function fromNow(value: string) {
  return dayjs(value).fromNow();
}
</script>
