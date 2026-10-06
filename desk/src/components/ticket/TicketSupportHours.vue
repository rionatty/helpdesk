<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <span class="text-base font-semibold text-ink-gray-8">
        {{ __("Support hours") }}
      </span>
      <Button
        size="sm"
        variant="subtle"
        :label="showForm ? __('Close') : __('Log time')"
        @click="toggleForm"
      >
        <template #prefix><LucideTimer class="size-3.5" /></template>
      </Button>
    </div>

    <!-- The client's plan this period -->
    <div
      v-if="data?.usage"
      class="flex flex-col gap-1.5 rounded-md border border-outline-gray-1 p-2.5"
    >
      <div class="flex items-center justify-between gap-2 text-sm">
        <span
          class="truncate font-medium text-ink-gray-8"
          :title="data.contract_name"
        >
          {{ data.contract_name }}
        </span>
        <span class="shrink-0 text-xs text-ink-gray-5">
          {{ data.usage.period_label }}
        </span>
      </div>
      <div class="h-1.5 overflow-hidden rounded-full bg-surface-gray-2">
        <div
          class="h-full rounded-full"
          :class="barClass(data.usage)"
          :style="{ width: barWidth(data.usage) }"
        />
      </div>
      <div class="flex items-center justify-between gap-2 text-xs">
        <span class="text-ink-gray-6">
          {{ __("{0} of {1} h used", [fmt(data.usage.used), fmt(data.usage.included)]) }}
        </span>
        <span :class="leftClass(data.usage)">{{ leftLabel(data.usage) }}</span>
      </div>
    </div>
    <p v-else-if="data?.customer" class="text-xs text-ink-gray-5">
      {{ __("{0} has no support contract in force.", [data.customer]) }}
    </p>

    <!-- Log time -->
    <div
      v-if="showForm"
      class="flex flex-col gap-2 rounded-md bg-surface-gray-1 p-2.5"
    >
      <div class="flex flex-wrap gap-1">
        <button
          v-for="q in QUICK"
          :key="q.hours"
          type="button"
          class="rounded px-2 py-0.5 text-xs ring-1"
          :class="
            Number(form.hours) === q.hours
              ? 'bg-surface-gray-7 text-ink-white ring-transparent'
              : 'bg-surface-white text-ink-gray-7 ring-outline-gray-2 hover:bg-surface-gray-2'
          "
          @click="form.hours = q.hours"
        >
          {{ q.label }}
        </button>
      </div>
      <div class="flex gap-2">
        <FormControl
          v-model="form.hours"
          class="w-24"
          type="number"
          step="0.25"
          min="0.25"
          max="24"
          :placeholder="__('Hours')"
          :aria-label="__('Hours')"
        />
        <FormControl
          v-model="form.day"
          class="flex-1"
          type="date"
          :max="today"
          :aria-label="__('Date')"
        />
      </div>
      <FormControl
        v-model="form.description"
        type="textarea"
        :rows="2"
        :placeholder="__('What was done? The client sees this.')"
        :aria-label="__('Description')"
      />
      <label class="flex cursor-pointer items-center gap-2 text-xs text-ink-gray-7">
        <input
          v-model="form.billable"
          type="checkbox"
          class="size-3.5 accent-blue-600"
        />
        {{ __("Billable: counts against the support contract") }}
      </label>
      <div class="flex justify-end">
        <Button
          size="sm"
          variant="solid"
          :label="__('Log {0} h', [fmt(Number(form.hours) || 0)])"
          :disabled="!validHours"
          :loading="logRes.loading"
          @click="submit"
        />
      </div>
    </div>

    <!-- Time on this ticket -->
    <div v-if="logs.length" class="flex flex-col gap-1">
      <div class="flex items-center justify-between text-xs text-ink-gray-6">
        <span>{{ __("On this ticket") }}</span>
        <span class="font-medium text-ink-gray-8">{{ fmt(data.total) }} h</span>
      </div>
      <ul class="flex flex-col divide-y divide-outline-gray-1">
        <li
          v-for="l in shownLogs"
          :key="l.name"
          class="flex items-start gap-2 py-1.5 text-xs"
        >
          <span class="w-12 shrink-0 text-ink-gray-5">{{ shortDate(l.date) }}</span>
          <span class="w-10 shrink-0 font-medium text-ink-gray-8">{{ fmt(l.hours) }} h</span>
          <div class="min-w-0 flex-1">
            <div class="truncate text-ink-gray-7" :title="lineText(l)">
              {{ lineText(l) }}
            </div>
            <div class="truncate text-ink-gray-5">
              {{ l.logged_by_name }}
              <template v-if="!l.billable"> · {{ __("not billable") }}</template>
              <template v-if="l.job_card"> · {{ l.job_card }}</template>
            </div>
          </div>
          <button
            v-if="l.can_delete"
            type="button"
            class="shrink-0 rounded p-0.5 text-ink-gray-4 hover:bg-surface-gray-2 hover:text-ink-red-3"
            :aria-label="__('Remove this entry')"
            :title="__('Remove this entry')"
            @click="removeLog(l)"
          >
            <LucideTrash2 class="size-3.5" />
          </button>
        </li>
      </ul>
      <button
        v-if="logs.length > SHOWN"
        type="button"
        class="self-start text-xs text-ink-gray-6 hover:text-ink-gray-8 hover:underline"
        @click="showAll = !showAll"
      >
        {{ showAll ? __("Show less") : __("Show all {0}", [logs.length]) }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { Button, FormControl, createResource, dayjs, toast } from "frappe-ui";
import { __ } from "@/translation";
import LucideTimer from "~icons/lucide/timer";
import LucideTrash2 from "~icons/lucide/trash-2";

const props = defineProps<{ ticketId?: string }>();
const emit = defineEmits<{ (e: "changed"): void }>();

const QUICK = [
  { hours: 0.25, label: "15m" },
  { hours: 0.5, label: "30m" },
  { hours: 1, label: "1h" },
  { hours: 2, label: "2h" },
];
const SHOWN = 4;

const today = dayjs().format("YYYY-MM-DD");
const showForm = ref(false);
const showAll = ref(false);
const form = reactive({
  hours: 0.5 as number | string,
  day: today,
  description: "",
  billable: true,
});

const res = createResource({
  url: "helpdesk.api.contracts.get_ticket_time",
  makeParams: () => ({ ticket: props.ticketId }),
  // Auxiliary widget: degrade quietly rather than toasting at the agent.
  onError: (e: any) => console.warn("[helpdesk] support hours:", e),
});
const data = computed(() => res.data);
const logs = computed<any[]>(() => res.data?.logs || []);
const shownLogs = computed(() =>
  showAll.value ? logs.value : logs.value.slice(0, SHOWN)
);

function reload() {
  if (props.ticketId) res.reload();
}

watch(
  () => props.ticketId,
  (id) => {
    showForm.value = false;
    showAll.value = false;
    if (id) res.reload();
  },
  { immediate: true }
);

const validHours = computed(() => {
  const h = Number(form.hours);
  return h > 0 && h <= 24;
});

function toggleForm() {
  showForm.value = !showForm.value;
  if (showForm.value) {
    Object.assign(form, { hours: 0.5, day: today, description: "", billable: true });
  }
}

const logRes = createResource({
  url: "helpdesk.api.contracts.log_time",
  onError: () => {},
});
async function submit() {
  if (!validHours.value) return;
  try {
    await logRes.submit({
      ticket: props.ticketId,
      hours: Number(form.hours),
      day: form.day || today,
      description: form.description.trim(),
      billable: form.billable ? 1 : 0,
    });
    toast.success(__("Logged {0} h", [fmt(Number(form.hours))]));
    showForm.value = false;
    reload();
    emit("changed");
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not log the time"));
  }
}

const deleteRes = createResource({
  url: "helpdesk.api.contracts.delete_time_log",
  onError: () => {},
});
async function removeLog(l: any) {
  try {
    await deleteRes.submit({ name: l.name });
    reload();
    emit("changed");
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not remove the entry"));
  }
}

function lineText(l: any) {
  if (l.description) return l.description;
  if (l.subtask_subject) return __("Subtask: {0}", [l.subtask_subject]);
  return __("Time on this ticket");
}

function fmt(h: number) {
  const n = Math.round((Number(h) || 0) * 100) / 100;
  return String(n);
}

function shortDate(d: string) {
  return dayjs(d).format("D MMM");
}

function barWidth(u: any) {
  return `${Math.min(100, Math.max(0, u.pct || 0))}%`;
}

function barClass(u: any) {
  if (u.pct >= 100) return "bg-red-500";
  if (u.pct >= u.alert_at) return "bg-amber-500";
  return "bg-emerald-500";
}

function leftLabel(u: any) {
  return u.remaining >= 0
    ? __("{0} h left", [fmt(u.remaining)])
    : __("{0} h over", [fmt(-u.remaining)]);
}

function leftClass(u: any) {
  if (u.remaining < 0) return "font-medium text-ink-red-3";
  if (u.pct >= u.alert_at) return "font-medium text-ink-amber-3";
  return "text-ink-gray-6";
}

defineExpose({ reload });
</script>
