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
        <p>{{ __("The customer who raised a ticket is told:") }}</p>
        <ul class="flex list-disc flex-col gap-1.5 ps-5">
          <li>
            <b>{{ __("Who is handling it") }}</b>:
            {{ __("when an agent is assigned, by hand, by auto-assignment or by an assignment rule. A ticket assigned as it arrives names the agent in its acknowledgement instead of a second email.") }}
          </li>
          <li>
            <b>{{ __("When it should be resolved") }}</b>:
            {{ __("when the assigned agent sets or changes the expected resolution in the ticket's sidebar.") }}
          </li>
        </ul>
        <p>
          {{ __("WhatsApp tickets are told on WhatsApp. Customers who turned off email updates, automated senders and your own inboxes are never emailed, and a ticket can only send a few of these an hour.") }}
        </p>
        <p class="text-ink-gray-5">
          {{ __("Switched off, nothing is sent, but customers still see the agent and the expected resolution on their ticket in the portal.") }}
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
  params: { notification: "assignment_notice" },
  auto: true,
  onSuccess: (d: any) => {
    enabled.value = saved.value = !!d?.enabled;
  },
});

const save = createResource({
  url: "helpdesk.api.settings.email_notifications.update_assignment_notice",
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
