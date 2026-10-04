<template>
  <SettingsLayoutBase>
    <template #title>
      <div class="flex items-center">
        <div
          class="ps-5 pe-2 relative text-ink-gray-7 hover:opacity-70 min-h-8 flex items-center"
        >
          <button
            type="button"
            class="absolute top-0 -start-[0.375rem] w-full h-full"
            @click="props.onBack"
          >
            <span class="sr-only">{{ __("back to email event list") }}</span>
            <LucideChevronLeft class="w-4.5 h-4.5 rtl:rotate-180" />
          </button>
          <h1 class="font-semibold text-xl">{{ props.notification.label }}</h1>
        </div>
      </div>
    </template>
    <template #header-actions>
      <div
        class="flex items-center gap-x-4 pt-[0.125rem]"
        :class="{ invisible: !data.data }"
      >
        <Switch
          v-model="enabled"
          size="sm"
          :label="__('Enabled')"
          :style="{ background: 'transparent', padding: '0px' }"
          class="flex-row-reverse gap-x-2 ps-0"
        />
        <Button
          type="button"
          theme="gray"
          variant="solid"
          :label="__('Save')"
          :disabled="!dirty"
          :loading="save.loading"
          @click="submit"
        />
      </div>
    </template>
    <template #content>
      <div class="flex max-w-2xl flex-col gap-4 pb-8 text-sm text-ink-gray-7">
        <p>
          {{ __("Every Monday at 07:00, each active project emails its client a short update:") }}
        </p>
        <ul class="flex list-disc flex-col gap-1.5 ps-5">
          <li>
            <b>{{ __("Waiting on you") }}</b>:
            {{ __("tasks owned by the client or by both sides, milestones to sign off, and tasks to review. Overdue items are marked.") }}
          </li>
          <li>
            <b>{{ __("Done this week") }}</b>:
            {{ __("milestones and tasks completed in the last 7 days.") }}
          </li>
          <li>
            <b>{{ __("Coming up") }}</b>:
            {{ __("milestones and tasks due in the next 14 days.") }}
          </li>
          <li>
            <b>{{ __("Your open tickets") }}</b>:
            {{ __("the client's open tickets for that project.") }}
          </li>
        </ul>
        <p>
          {{ __("It goes to the recipients set on each project, or to the client's primary contact when none are set. A project with nothing to report sends nothing that week.") }}
        </p>
        <p>
          {{ __("Only what the client can already see in their portal is included: internal tasks and hidden milestones never appear.") }}
        </p>
        <p class="text-ink-gray-5">
          {{ __("To preview a project's update, change its recipients, or switch it off for one project, open the project and click Client update.") }}
        </p>
      </div>
    </template>
  </SettingsLayoutBase>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Button, Switch, createResource, toast } from "frappe-ui";
import SettingsLayoutBase from "@/components/layouts/SettingsLayoutBase.vue";
import { __ } from "@/translation";
import LucideChevronLeft from "~icons/lucide/chevron-left";
import type { Notification } from "./types";

const props = defineProps<{
  onBack: () => void;
  notification: Notification;
}>();

const enabled = ref(false);
const saved = ref(false);
const dirty = computed(() => enabled.value !== saved.value);

const data = createResource({
  url: "helpdesk.api.settings.email_notifications.get_data",
  method: "GET",
  params: { notification: "weekly_client_update" },
  auto: true,
  onSuccess: (d: any) => {
    enabled.value = saved.value = !!d?.enabled;
  },
});

const save = createResource({
  url: "helpdesk.api.settings.email_notifications.update_weekly_client_update",
  method: "PUT",
  onSuccess: (d: any) => {
    enabled.value = saved.value = !!d?.enabled;
    toast.success(__("Settings updated successfully."));
  },
  onError: (e: any) => toast.error(e?.messages?.[0] || __("Could not save the setting")),
});

function submit() {
  save.submit({ enabled: enabled.value });
}
</script>
