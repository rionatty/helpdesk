<template>
  <Button theme="gray" variant="subtle" :label="__('Client update')" @click="open">
    <template #prefix><LucideMailCheck class="size-4" /></template>
  </Button>
  <Dialog v-model="show" :options="{ title: __('Weekly client update'), size: '3xl' }">
    <template #body-content>
      <div v-if="!info.data" class="py-10 text-center text-sm text-ink-gray-5">
        {{ __("Loading...") }}
      </div>
      <div v-else class="flex flex-col gap-4">
        <div
          v-if="!info.data.enabled_globally"
          class="rounded-md bg-amber-50 p-3 text-p-sm text-amber-800"
        >
          {{ __("Weekly updates are switched off for all projects (Settings > Email Notifications > Weekly client update). You can still preview this one and send it now.") }}
        </div>

        <label class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-8">
          <input v-model="weekly" type="checkbox" class="size-4 accent-blue-600" />
          {{ __("Send this project's weekly update") }}
        </label>
        <div class="flex flex-col gap-1">
          <FormControl
            v-model="recipientsText"
            type="textarea"
            :rows="2"
            :label="__('Send to')"
            :placeholder="__('Leave empty to use the client primary contact')"
          />
          <span
            class="text-p-sm"
            :class="info.data.recipients.length ? 'text-ink-gray-5' : 'text-ink-red-3'"
          >
            {{ recipientsHint }}
          </span>
        </div>
        <div class="flex justify-end">
          <Button
            :label="__('Save settings')"
            :disabled="!dirty"
            :loading="saveRes.loading"
            @click="saveSettings"
          />
        </div>

        <div class="flex flex-col gap-2">
          <span class="text-base font-semibold text-ink-gray-8">
            {{ __("This week's email") }}
          </span>
          <!-- Sandboxed: the preview is inert, scripts and navigation blocked. -->
          <iframe
            v-if="info.data.html"
            :srcdoc="info.data.html"
            sandbox=""
            class="h-96 w-full rounded-md bg-white ring-1 ring-outline-gray-2"
          />
          <p v-else class="rounded-md bg-surface-gray-1 p-4 text-sm text-ink-gray-6">
            {{ __("Nothing to report on this project this week, so no email would be sent.") }}
          </p>
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex w-full items-center gap-2">
        <span v-if="info.data?.last_sent" class="text-p-sm text-ink-gray-5">
          {{ __("Last sent {0}", [timeAgo(info.data.last_sent)]) }}
        </span>
        <span class="flex-1" />
        <Button
          variant="solid"
          :theme="armed ? 'red' : 'blue'"
          :label="armed ? __('Click again to email the client') : __('Send to client now')"
          :disabled="!canSend"
          :loading="sendRes.loading"
          @click="send"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Button, Dialog, FormControl, createResource, toast } from "frappe-ui";
import { __ } from "@/translation";
import { timeAgo } from "@/utils";
import LucideMailCheck from "~icons/lucide/mail-check";

const props = defineProps<{ projectId: string }>();

const show = ref(false);
const weekly = ref(true);
const recipientsText = ref("");
const saved = ref({ weekly: true, text: "" });

const info = createResource({
  url: "helpdesk.api.client_update.get_client_update",
  makeParams: () => ({ project: props.projectId }),
  onSuccess: (d: any) => {
    weekly.value = !!d.weekly_update;
    recipientsText.value = d.recipients_text || "";
    saved.value = { weekly: !!d.weekly_update, text: d.recipients_text || "" };
  },
  onError: (e: any) => {
    toast.error(e?.messages?.[0] || __("Could not load the client update"));
    show.value = false;
  },
});

function open() {
  show.value = true;
  info.fetch();
}

const dirty = computed(
  () => weekly.value !== saved.value.weekly || recipientsText.value.trim() !== saved.value.text
);

const recipientsHint = computed(() => {
  const d = info.data;
  if (!d) return "";
  if (!d.recipients.length) {
    return d.uses_primary_contact
      ? __("No recipient: the client has no primary contact. Add an address above.")
      : __("None of these addresses are valid.");
  }
  return d.uses_primary_contact
    ? __("Goes to the client's primary contact: {0}", [d.recipients.join(", ")])
    : __("Goes to: {0}", [d.recipients.join(", ")]);
});

// Settings must be saved first, so a send always uses what's on screen.
const canSend = computed(
  () => !!info.data?.has_news && !!info.data?.recipients?.length && !dirty.value
);

const saveRes = createResource({
  url: "helpdesk.api.client_update.save_client_update_settings",
  onSuccess: () => {
    toast.success(__("Saved"));
    info.fetch();
  },
  onError: (e: any) => toast.error(e?.messages?.[0] || __("Could not save")),
});

function saveSettings() {
  saveRes.submit({
    project: props.projectId,
    weekly_update: weekly.value ? 1 : 0,
    recipients_text: recipientsText.value,
  });
}

// Sending emails a real client, so it takes two clicks.
const armed = ref(false);
let armTimer: ReturnType<typeof setTimeout> | undefined;
const sendRes = createResource({
  url: "helpdesk.api.client_update.send_client_update_now",
  onError: () => {},
});

async function send() {
  if (!armed.value) {
    armed.value = true;
    clearTimeout(armTimer);
    armTimer = setTimeout(() => (armed.value = false), 4000);
    return;
  }
  armed.value = false;
  try {
    const result = await sendRes.submit({ project: props.projectId });
    toast.success(__("Sent to {0}", [(result?.sent_to || []).join(", ")]));
    info.fetch();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not send the update"));
  }
}
</script>
