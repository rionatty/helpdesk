<template>
  <div
    class="executive-card rounded-2xl px-6 py-5 mb-5 bg-gradient-to-br from-blue-50/60 via-surface-white to-surface-white animate-in-fade"
  >
    <div
      class="flex items-start md:items-center justify-between gap-4 flex-col md:flex-row"
    >
      <div class="flex items-center gap-3">
        <Avatar
          size="xl"
          :label="userName"
          :image="userImage"
          class="ring-2 ring-offset-2 ring-outline-gray-2"
        />
        <div>
          <div
            class="executive-heading text-2xl text-ink-gray-9 leading-tight"
          >
            {{ greeting }}, {{ firstName }}
          </div>
          <div class="text-sm text-ink-gray-6 mt-1">
            {{ subtitleLine }}
          </div>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <div
          class="flex items-center gap-2 px-3 py-2 rounded-lg border border-outline-gray-1 bg-surface-white"
        >
          <div class="size-8 rounded-full bg-surface-blue-1 flex items-center justify-center">
            <LucideTicket class="size-4 text-blue-600" />
          </div>
          <div class="leading-tight">
            <div class="text-lg font-semibold text-ink-gray-9">
              {{ assignedCount }}
            </div>
            <div class="text-xs text-ink-gray-5">
              {{ __("Assigned to you") }}
            </div>
          </div>
        </div>
        <RouterLink
          :to="{ name: 'TicketAgentNew' }"
          class="flex items-center gap-2 px-3 py-2 rounded-lg border border-ink-gray-9 bg-ink-gray-9 text-white font-medium hover:bg-ink-gray-8 transition-colors"
        >
          <LucidePlus class="size-4" />
          <span>{{ __("New ticket") }}</span>
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Avatar, createResource, dayjs } from "frappe-ui";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useConfigStore } from "@/stores/config";
import { __ } from "@/translation";

const { userName, userId, userImage } = storeToRefs(useAuthStore());
const config = useConfigStore();

const firstName = computed(() => {
  const n = userName.value || "";
  return n.split(" ")[0] || n || __("there");
});

const greeting = computed(() => {
  const hour = dayjs().hour();
  if (hour < 5) return __("Burning the midnight oil");
  if (hour < 12) return __("Good morning");
  if (hour < 18) return __("Good afternoon");
  return __("Good evening");
});

const todayLabel = computed(() => dayjs().format("dddd, MMM D"));

const brand = computed(() => config.brandName || __("Helpdesk"));

const subtitleLine = computed(() => `${todayLabel.value} · ${brand.value}`);

const assignedTickets = createResource({
  url: "frappe.client.get_count",
  params: {
    doctype: "HD Ticket",
    filters: [
      ["_assign", "like", `%${userId.value}%`],
      ["status_category", "!=", "Resolved"],
    ],
  },
  auto: true,
});

const assignedCount = computed(() => {
  if (assignedTickets.loading) return "—";
  return assignedTickets.data ?? 0;
});
</script>
