<template>
  <div class="flex w-full md:w-[382px] flex-col md:border-s hd-chrome-bg">
    <!-- Header -->
    <div
      class="flex items-center gap-2 border-b px-5 py-4 bg-gradient-to-r from-blue-100/60 to-blue-50/40 shadow-sm"
    >
      <div
        class="size-7 rounded-lg hd-icon-blue flex items-center justify-center shadow-sm ring-1 ring-inset ring-white/40"
      >
        <LucideClipboardList class="size-4 text-white" />
      </div>
      <span class="text-lg font-semibold text-ink-gray-9">
        {{ __("Ticket details") }}
      </span>
    </div>
    <!-- Contact card -->
    <div class="flex flex-col gap-4 px-5 py-4 border-b">
      <div class="flex items-center gap-3">
        <Avatar
          size="2xl"
          :image="ticket.data.contact.image"
          :label="ticket.data.contact.name"
        />
        <div class="flex-1 min-w-0">
          <Tooltip :text="ticket.data.contact.name">
            <div class="truncate text-lg font-semibold text-ink-gray-9">
              {{ ticket.data.contact.name }}
            </div>
          </Tooltip>
          <div class="text-xs text-ink-gray-6 font-medium truncate">
            {{ ticket.data.contact.email_id }}
          </div>
        </div>
        <div v-if="!ticket.data.feedback_rating">
          <Tooltip :text="__('Email contact')">
            <Button class="h-7 w-7" @click="emit('open')">
              <template #icon>
                <EmailIcon class="h-4 w-4" />
              </template>
            </Button>
          </Tooltip>
        </div>
      </div>
    </div>
    <!-- Overview section -->
    <div class="px-5 py-4 border-b flex flex-col gap-3">
      <div
        class="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-blue-700 px-3 py-2 -mx-3 rounded-md bg-blue-50"
      >
        <span class="h-3 w-1 rounded-full bg-blue-500" />
        {{ __("Overview") }}
      </div>
      <div
        v-for="field in ticketBasicInfo"
        :key="field.label"
        class="flex items-center gap-3 text-base"
      >
        <component
          :is="iconFor(field.label)"
          class="size-4 text-ink-gray-5 shrink-0"
        />
        <span class="w-[96px] text-sm font-medium text-ink-gray-7">{{
          __(field.label)
        }}</span>
        <span
          class="text-base text-ink-gray-8 flex-1 truncate"
          :class="!field.value && 'text-ink-gray-4'"
        >
          {{ field.value || "—" }}
        </span>
      </div>
      <!-- Attachment count -->
      <div
        v-if="attachmentCount > 0"
        class="flex items-center gap-3 text-base"
      >
        <LucidePaperclip class="size-4 text-ink-gray-5 shrink-0" />
        <span class="w-[96px] text-sm font-medium text-ink-gray-7">
          {{ __("Attachments") }}
        </span>
        <span class="text-base text-ink-gray-8 flex-1">
          {{ attachmentCount }}
        </span>
      </div>
      <!-- Subscribe toggle -->
      <div class="flex items-center gap-3 text-base">
        <LucideBell class="size-4 text-ink-gray-5 shrink-0" />
        <span class="w-[96px] text-sm font-medium text-ink-gray-7">
          {{ __("Email updates") }}
        </span>
        <Tooltip :text="subscribeTooltip">
          <button
            type="button"
            class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
            :class="isSubscribed ? 'bg-green-500' : 'bg-surface-gray-4'"
            @click="toggleSubscribe"
            :aria-pressed="isSubscribed"
          >
            <span
              class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform shadow-sm"
              :class="isSubscribed ? 'translate-x-5' : 'translate-x-1'"
            />
          </button>
        </Tooltip>
      </div>
    </div>
    <!-- SLA section -->
    <div class="px-5 py-4 border-b flex flex-col gap-3">
      <div
        class="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-amber-700 px-3 py-2 -mx-3 rounded-md bg-amber-50"
      >
        <span class="h-3 w-1 rounded-full bg-amber-500" />
        {{ __("SLA") }}
      </div>
      <div
        v-for="data in slaData"
        :key="data.label"
        class="flex items-center gap-3 text-base"
      >
        <component
          :is="iconFor(data.title)"
          class="size-4 text-ink-gray-5 shrink-0"
        />
        <div class="w-[96px] text-sm font-medium text-ink-gray-7">
          {{ __(data.title) }}
        </div>
        <div class="flex items-center gap-2 flex-1">
          <Tooltip :text="dateFormat(data.value, dateTooltipFormat)">
            <span
              :class="[
                data.theme === 'green' && '[&_*]:!text-green-900',
                data.theme === 'orange' && '[&_*]:!text-amber-900',
              ]"
            >
              <Badge :label="data.label" :theme="data.theme" variant="subtle" />
            </span>
          </Tooltip>
          <Tooltip
            v-if="
              dayjs(data.value).diff(dayjs(), 'day', true) > 4 &&
              data.title === 'Resolution'
            "
            :text="
              __(
                'This date is calculated based on configured SLAs, working hours, and holidays.'
              )
            "
          >
            <lucide-circle-question-mark
              class="h-4 w-4 text-ink-gray-6 cursor-pointer"
            />
          </Tooltip>
        </div>
      </div>
    </div>
    <!-- Progress / subtasks (read-only for customers) -->
    <div class="px-5 py-4 border-b">
      <TicketSubtasks :ticket-id="ticket.data.name" :editable="false" />
    </div>
    <!-- Participants — customer can CC colleagues -->
    <div class="px-5 py-4 border-b">
      <TicketParticipants :ticket-id="ticket.data.name" />
    </div>
    <!-- feedback component -->
    <TicketFeedback
      v-if="ticket.data.feedback_rating"
      class="border-b text-base text-ink-gray-5"
      :ticket="ticket.data"
    />
    <div class="flex flex-col gap-3 px-5 py-4 md:overflow-y-scroll">
      <div
        class="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-violet-700 px-3 py-2 -mx-3 rounded-md bg-violet-50"
      >
        <span class="h-3 w-1 rounded-full bg-violet-500" />
        {{ __("Details") }}
      </div>
      <div
        v-for="field in ticketAdditionalInfo"
        :key="field.fieldname"
        class="flex items-center gap-3 text-base"
      >
        <component
          :is="iconFor(field.label)"
          class="size-4 text-ink-gray-5 shrink-0"
        />
        <span class="w-[96px] text-sm font-medium text-ink-gray-7">{{
          __(field.label)
        }}</span>
        <span
          class="text-base text-ink-gray-8 flex-1 truncate"
          :class="!field.value && 'text-ink-gray-4'"
        >
          <template
            v-if="
              field.value &&
              (field.fieldtype === 'Date' || field.fieldtype === 'Datetime') &&
              dayjs(field.value).isValid()
            "
          >
            {{ dateFormat(field.value, dateTooltipFormat) }}
          </template>
          <template v-else>
            {{ field.value || "—" }}
          </template>
        </span>
      </div>
      <!-- Other open tickets by the same customer -->
      <div
        v-if="otherOpenTickets.data && otherOpenTickets.data.length"
        class="flex flex-col gap-2 mt-2 pt-3 border-t border-outline-gray-1"
      >
        <div class="text-sm font-medium text-ink-gray-7 mb-1">
          {{ __("Your other open tickets") }}
        </div>
        <button
          v-for="t in otherOpenTickets.data"
          :key="t.name"
          type="button"
          class="text-start rounded-md border border-outline-gray-1 hover:border-outline-gray-3 px-3 py-2 transition-colors"
          @click="openTicket(t.name)"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs text-ink-gray-5">#{{ t.name }}</span>
            <Badge
              v-if="t.status"
              :label="t.status"
              theme="gray"
              variant="subtle"
            />
          </div>
          <div class="text-sm text-ink-gray-8 truncate mt-0.5">
            {{ t.subject }}
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ITicket } from "@/pages/ticket/symbols";
import { Field } from "@/types";
import { dateFormat, dateTooltipFormat, formatTime } from "@/utils";
import { __ } from "@/translation";
import {
  Avatar,
  Badge,
  createListResource,
  dayjs,
  toast,
  Tooltip,
} from "frappe-ui";
import { computed, inject, ref, watch } from "vue";
import { useRouter } from "vue-router";
import TicketSubtasks from "@/components/ticket/TicketSubtasks.vue";
import TicketParticipants from "@/components/ticket/TicketParticipants.vue";

const router = useRouter();

const emit = defineEmits(["open"]);

const ticket = inject(ITicket);

const otherOpenTickets = createListResource({
  doctype: "HD Ticket",
  fields: ["name", "subject", "status"],
  filters: computed(() => ({
    raised_by: ticket.data?.raised_by,
    status_category: ["!=", "Resolved"],
    name: ["!=", ticket.data?.name],
  })),
  orderBy: "modified desc",
  pageLength: 5,
  auto: true,
});

function openTicket(name: string) {
  router.push({ name: "TicketCustomer", params: { ticketId: name } });
}

const attachmentCount = computed(() => {
  const comms = ticket.data?.communications || [];
  return comms.reduce(
    (total: number, c: any) => total + (c.attachments?.length || 0),
    0
  );
});

const isSubscribed = ref(true);
watch(
  () => ticket.data?.name,
  (name) => {
    if (!name) return;
    const stored = localStorage.getItem(`helpdesk:subscribed:${name}`);
    isSubscribed.value = stored === null ? true : stored === "1";
  },
  { immediate: true }
);

const subscribeTooltip = computed(() =>
  isSubscribed.value
    ? __("Subscribed to email updates")
    : __("Email updates are muted")
);

function toggleSubscribe() {
  isSubscribed.value = !isSubscribed.value;
  const name = ticket.data?.name;
  if (name) {
    localStorage.setItem(
      `helpdesk:subscribed:${name}`,
      isSubscribed.value ? "1" : "0"
    );
  }
  toast.success(
    isSubscribed.value
      ? __("Email updates enabled for this ticket")
      : __("Email updates muted for this ticket")
  );
}

import LucideHash from "~icons/lucide/hash";
import LucideCircleDot from "~icons/lucide/circle-dot";
import LucideFileText from "~icons/lucide/file-text";
import LucideUsers from "~icons/lucide/users";
import LucideZap from "~icons/lucide/zap";
import LucideTimer from "~icons/lucide/timer";
import LucideCheckCircle from "~icons/lucide/check-circle";
import LucideInfo from "~icons/lucide/info";
import LucidePaperclip from "~icons/lucide/paperclip";
import LucideBell from "~icons/lucide/bell";
import LucideClipboardList from "~icons/lucide/clipboard-list";

const ICON_MAP: Record<string, any> = {
  "Ticket ID": LucideHash,
  Status: LucideCircleDot,
  Subject: LucideFileText,
  Team: LucideUsers,
  Priority: LucideZap,
  "First Response": LucideTimer,
  Resolution: LucideCheckCircle,
};

function iconFor(label: string): any {
  return ICON_MAP[label] || LucideInfo;
}

const slaData = computed(() => {
  const firstResponse = firstResponseData();
  const resolution = resolutionData();
  return [
    {
      title: "First Response",
      value: ticket.data.first_responded_on || ticket.data.response_by,
      label: firstResponse.label,
      theme: firstResponse.color,
    },
    {
      title: "Resolution",
      value: ticket.data.resolution_date || ticket.data.resolution_by,
      label: resolution.label,
      theme: resolution.color,
    },
  ];
});

function firstResponseData() {
  let firstResponse = null;
  if (
    !ticket.data.first_responded_on &&
    dayjs().isBefore(dayjs(ticket.data.response_by))
  ) {
    firstResponse = {
      label: __("Due in {0}", [
        formatTime(dayjs(ticket.data.response_by).diff(dayjs(), "s")),
      ]),
      color: "orange",
    };
  } else if (
    dayjs(ticket.data.first_responded_on).isBefore(
      dayjs(ticket.data.response_by)
    )
  ) {
    firstResponse = {
      label: __("Fulfilled in {0}", [
        formatTime(
          dayjs(ticket.data.first_responded_on).diff(
            dayjs(ticket.data.creation),
            "s"
          )
        ),
      ]),
      color: "green",
    };
  } else {
    firstResponse = {
      label: __("Failed"),
      color: "red",
    };
  }
  return firstResponse;
}

function resolutionData() {
  let resolution = null;
  if (
    !ticket.data.resolution_date &&
    dayjs().isBefore(ticket.data.resolution_by)
  ) {
    resolution = {
      label: __("Due in {0}", [
        formatTime(dayjs(ticket.data.resolution_by).diff(dayjs(), "s")),
      ]),
      color: "orange",
    };
  } else if (ticket.data.agreement_status === "Fulfilled") {
    resolution = {
      // resolution_time is already a duration in seconds — format it directly.
      label: __("Fulfilled in {0}", [formatTime(ticket.data.resolution_time)]),
      color: "green",
    };
  } else {
    resolution = {
      label: __("Failed"),
      color: "red",
    };
  }
  return resolution;
}

const ticketBasicInfo = computed(() => [
  {
    label: "Ticket ID",
    value: ticket.data.name,
  },
  {
    label: "Status",
    value: ticket.data.status,
    bold: true,
  },
]);

const ticketAdditionalInfo = computed(() => {
  const fields = [
    {
      fieldname: "subject",
      label: "Subject",
      value: ticket.data.subject,
    },
    {
      fieldname: "team",
      label: "Team",
      value: ticket.data.agent_group || "-",
    },
    {
      fieldname: "priority",
      label: "Priority",
      value: ticket.data.priority,
    },
  ];
  const custom_fields = ticket.data.template.fields
    .filter(
      (field: Field) =>
        !field.hide_from_customer &&
        ["subject", "team", "priority"].indexOf(field.fieldname) === -1
    )
    .map((field: Field) => {
      const option = {
        label: field.label,
        value: ticket.data[field.fieldname],
      };
      if (field.fieldtype === "Date") {
        option.value = dayjs(option.value).format(
          window.date_format.toUpperCase()
        );
      }
      if (field.fieldtype === "Datetime") {
        // window.time_format
        option.value = dayjs(option.value).format(
          `${window.date_format.toUpperCase()} ${window.time_format}`
        );
      }
      return option;
    });

  return [...fields, ...custom_fields];
});
</script>

<style scoped></style>
