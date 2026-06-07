<template>
  <div
    v-if="ticket?.data"
    class="px-4 md:px-10 pt-4 md:pt-6 animate-in-fade"
  >
    <div class="flex flex-col md:flex-row md:flex-wrap md:items-center gap-x-3 gap-y-2">
      <h1
        class="executive-heading text-lg md:text-2xl text-blue-900 font-bold leading-tight"
      >
        {{ ticket.data.subject }}
      </h1>
      <div class="flex flex-wrap items-center gap-2">
        <Badge
          theme="gray"
          variant="subtle"
          :label="`#${ticket.data.name}`"
        />
        <Badge
          v-if="ticket.data.priority"
          :theme="priorityTheme"
          variant="subtle"
          :label="__(ticket.data.priority)"
        />
        <Badge
          v-if="ticket.data.ticket_type"
          theme="gray"
          variant="outline"
          :label="ticket.data.ticket_type"
        />
      </div>
    </div>
    <div
      v-if="visibleSla.length"
      class="flex flex-wrap items-center gap-2 mt-3"
    >
      <Tooltip
        v-for="sla in visibleSla"
        :key="sla.title"
        :text="sla.tooltip"
      >
        <span
          :class="[
            'inline-flex',
            sla.theme === 'green' && '[&_*]:!text-green-900',
            sla.theme === 'orange' && '[&_*]:!text-amber-900',
          ]"
        >
          <Badge
            :theme="sla.theme"
            variant="subtle"
            :label="`${__(sla.title)}: ${sla.label}`"
          />
        </span>
      </Tooltip>
    </div>
    <div
      v-if="lastActivity"
      class="flex items-center gap-1.5 text-xs text-ink-gray-7 font-medium mt-2"
    >
      <Tooltip :text="dateFormat(lastActivity, dateTooltipFormat)">
        <span class="flex items-center gap-1.5">
          <LucideHistory class="size-3.5" />
          {{ __("Last activity") }} {{ timeAgo(lastActivity) }}
        </span>
      </Tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from "vue";
import { Badge, dayjs, Tooltip } from "frappe-ui";
import { ITicket } from "@/pages/ticket/symbols";
import { __ } from "@/translation";
import { dateFormat, dateTooltipFormat, formatTime, timeAgo } from "@/utils";

const ticket = inject(ITicket);

const PRIORITY_THEME: Record<string, string> = {
  Urgent: "red",
  High: "orange",
  Medium: "blue",
  Low: "gray",
};

const priorityTheme = computed(
  () => PRIORITY_THEME[ticket?.data?.priority || ""] || "gray"
);

interface SlaChip {
  title: string;
  show: boolean;
  label: string;
  theme: string;
  tooltip: string;
}

function buildSla(
  title: string,
  fulfilledAt: string | undefined,
  dueAt: string | undefined,
  startedAt: string | undefined
): SlaChip {
  if (!dueAt) {
    return { title, show: false, label: "", theme: "gray", tooltip: "" };
  }
  const now = dayjs();
  const due = dayjs(dueAt);
  const tooltip = dateFormat(dueAt, dateTooltipFormat);

  if (fulfilledAt) {
    const fulfilled = dayjs(fulfilledAt);
    if (fulfilled.isBefore(due)) {
      const span = startedAt
        ? formatTime(fulfilled.diff(dayjs(startedAt), "s"))
        : formatTime(due.diff(fulfilled, "s"));
      return {
        title,
        show: true,
        label: __("Met in {0}", [span]),
        theme: "green",
        tooltip,
      };
    }
    return { title, show: true, label: __("Breached"), theme: "red", tooltip };
  }

  if (now.isAfter(due)) {
    return { title, show: true, label: __("Breached"), theme: "red", tooltip };
  }

  const secondsLeft = due.diff(now, "s");
  const fraction = startedAt
    ? secondsLeft / Math.max(1, due.diff(dayjs(startedAt), "s"))
    : 1;
  let theme = "green";
  if (fraction < 0.25) theme = "red";
  else if (fraction < 0.5) theme = "orange";

  return {
    title,
    show: true,
    label: `${__("Due in")} ${formatTime(secondsLeft)}`,
    theme,
    tooltip,
  };
}

const visibleSla = computed<SlaChip[]>(() => {
  const t = ticket?.data;
  if (!t) return [];
  return [
    buildSla("First Response", t.first_responded_on, t.response_by, t.creation),
    buildSla("Resolution", t.resolution_date, t.resolution_by, t.creation),
  ].filter((s) => s.show);
});

const lastActivity = computed<string | undefined>(() => {
  const t = ticket?.data;
  if (!t) return undefined;
  const latestComm = (t.communications || []).reduce(
    (max: string | null, c: any) =>
      !max || dayjs(c.creation).isAfter(dayjs(max)) ? c.creation : max,
    null as string | null
  );
  return latestComm || t.modified || t.creation;
});
</script>
