<template>
  <SettingsLayoutBase
    :title="__('Pumble')"
    :description="__('Post helpdesk activity to your Pumble channels.')"
  >
    <template #header-actions>
      <Button
        v-if="!editing"
        variant="solid"
        :label="__('Add channel')"
        @click="startNew"
      />
    </template>

    <template #content>
      <!-- Editor -->
      <div v-if="editing" class="flex flex-col gap-5 pb-6">
        <FormControl
          v-model="form.channel_name"
          type="text"
          :label="__('Channel')"
          placeholder="#support"
        />
        <div class="flex flex-col gap-1">
          <FormControl
            v-model="form.webhook_url"
            type="password"
            :label="__('Webhook URL')"
            :placeholder="
              form.has_webhook
                ? __('Saved. Paste a new URL only to replace it.')
                : 'https://api.pumble.com/workspaces/...'
            "
          />
          <span class="text-p-sm text-ink-gray-5">
            {{
              __(
                "In Pumble, open the channel, add an Incoming Webhook to it, and copy its URL."
              )
            }}
          </span>
        </div>
        <label class="flex items-center gap-2 text-sm text-ink-gray-8 cursor-pointer">
          <input v-model="form.enabled" type="checkbox" class="size-4 accent-blue-600" />
          {{ __("Enabled") }}
        </label>

        <div class="flex flex-col gap-2">
          <span class="text-base font-semibold text-ink-gray-8">{{ __("Post when") }}</span>
          <label
            v-for="e in EVENTS"
            :key="e.field"
            class="flex items-start gap-2 cursor-pointer"
          >
            <input
              v-model="form[e.field]"
              type="checkbox"
              class="mt-1 size-4 accent-blue-600"
            />
            <span class="flex flex-col">
              <span class="text-sm text-ink-gray-8">{{ e.label }}</span>
              <span class="text-p-sm text-ink-gray-5">{{ e.description }}</span>
            </span>
          </label>
        </div>

        <div class="flex flex-col gap-2">
          <span class="text-base font-semibold text-ink-gray-8">{{ __("Only for") }}</span>
          <span class="text-p-sm text-ink-gray-5">
            {{ __("Optional. Leave these empty to post from everywhere.") }}
          </span>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <FormControl
              v-model="form.project"
              type="select"
              :label="__('Project')"
              :options="projectOptions"
            />
            <FormControl
              v-model="form.customer"
              type="select"
              :label="__('Client')"
              :options="customerOptions"
            />
            <FormControl
              v-model="form.email_account"
              type="select"
              :label="__('Inbox')"
              :options="inboxOptions"
            />
          </div>
        </div>

        <div class="flex justify-end gap-2">
          <Button :label="__('Cancel')" @click="editing = false" />
          <Button
            variant="solid"
            :label="__('Save channel')"
            :loading="saveRes.loading"
            @click="save"
          />
        </div>
      </div>

      <!-- Channel list -->
      <div v-else class="flex flex-col gap-4 pb-6">
        <div
          v-if="channels.data && !channels.data.length"
          class="flex flex-col gap-1.5 rounded-md bg-surface-gray-1 p-4 text-sm text-ink-gray-7"
        >
          <span class="font-semibold text-ink-gray-8">{{ __("No Pumble channels yet") }}</span>
          <span>1. {{ __("In Pumble, open the channel you want the helpdesk to post to.") }}</span>
          <span>2. {{ __("Add an Incoming Webhook to that channel and copy its URL.") }}</span>
          <span>3. {{ __("Click Add channel here and paste the URL.") }}</span>
        </div>

        <div
          v-for="c in channels.data || []"
          :key="c.name"
          class="flex flex-col gap-1.5 rounded-md p-3 ring-1 ring-outline-gray-modals"
        >
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-base font-semibold text-ink-gray-8">{{ c.channel_name }}</span>
            <Badge
              variant="subtle"
              :theme="c.enabled ? 'green' : 'gray'"
              :label="c.enabled ? __('On') : __('Off')"
            />
            <Badge
              v-if="!c.has_webhook"
              variant="subtle"
              theme="red"
              :label="__('No webhook URL')"
            />
            <span class="flex-1" />
            <Button
              size="sm"
              :label="__('Send test')"
              :loading="testing === c.name"
              @click="test(c)"
            />
            <Button size="sm" :label="__('Edit')" @click="startEdit(c)" />
            <Button
              size="sm"
              variant="ghost"
              theme="red"
              :label="armed === c.name ? __('Confirm delete') : __('Delete')"
              @click="remove(c)"
            />
          </div>
          <span class="text-p-sm text-ink-gray-6">{{ eventSummary(c) }}</span>
          <span class="text-p-sm text-ink-gray-5">{{ scopeSummary(c) }}</span>
        </div>

        <div v-if="log.data && log.data.length" class="flex flex-col gap-1.5">
          <span class="text-base font-semibold text-ink-gray-8">{{ __("Recent messages") }}</span>
          <div
            class="max-h-64 overflow-y-auto rounded-md ring-1 ring-outline-gray-modals divide-y divide-outline-gray-1"
          >
            <div
              v-for="l in log.data"
              :key="l.name"
              class="flex items-start gap-3 px-3 py-1.5 text-p-sm"
            >
              <span class="w-24 shrink-0 text-ink-gray-5">{{ timeAgo(l.creation) }}</span>
              <span class="w-28 shrink-0 truncate text-ink-gray-7">{{ channelLabel(l.channel) }}</span>
              <span class="w-36 shrink-0 text-ink-gray-7">{{ eventLabel(l.event) }}</span>
              <span
                class="shrink-0 font-medium"
                :class="l.status === 'Sent' ? 'text-green-700' : 'text-ink-red-3'"
              >
                {{ l.status === "Sent" ? __("Sent") : __("Failed") }}
              </span>
              <span v-if="l.error" class="truncate text-ink-red-3" :title="l.error">
                {{ l.error }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </SettingsLayoutBase>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { Badge, Button, FormControl, createResource, toast } from "frappe-ui";
import SettingsLayoutBase from "@/components/layouts/SettingsLayoutBase.vue";
import { __ } from "@/translation";
import { timeAgo } from "@/utils";

const EVENTS = [
  {
    field: "on_new_ticket",
    label: __("New ticket"),
    description: __("A ticket arrives, by email or through the portal."),
  },
  {
    field: "on_customer_reply",
    label: __("Customer replied"),
    description: __("A customer writes back on a ticket."),
  },
  {
    field: "on_sla_breach",
    label: __("SLA breached"),
    description: __(
      "A first-response or resolution deadline is missed. Posted once per deadline."
    ),
  },
  {
    field: "on_ticket_resolved",
    label: __("Ticket resolved"),
    description: __("A ticket is resolved or closed."),
  },
  {
    field: "on_project_activity",
    label: __("Client activity on projects"),
    description: __(
      "A client comments on or reviews a task, signs off a milestone, or reports a test result."
    ),
  },
  {
    field: "on_support_hours",
    label: __("Support hours alerts"),
    description: __(
      "A client reaches its contract's alert level, or uses all its hours. Posted once per level per period."
    ),
  },
];

const channels = createResource({ url: "helpdesk.api.pumble.get_channels", auto: true });
const log = createResource({ url: "helpdesk.api.pumble.get_log", auto: true });
const scope = createResource({ url: "helpdesk.api.pumble.get_scope_options" });

const editing = ref(false);
const form = reactive<Record<string, any>>({});

function blank() {
  return {
    name: null,
    channel_name: "",
    webhook_url: "",
    has_webhook: false,
    enabled: true,
    on_new_ticket: true,
    on_customer_reply: true,
    on_sla_breach: true,
    on_ticket_resolved: false,
    on_project_activity: true,
    on_support_hours: true,
    project: "",
    customer: "",
    email_account: "",
  };
}

function openEditor() {
  if (!scope.data) scope.fetch();
  editing.value = true;
}

function startNew() {
  Object.assign(form, blank());
  openEditor();
}

function startEdit(c: any) {
  Object.assign(form, blank(), {
    name: c.name,
    channel_name: c.channel_name || "",
    has_webhook: !!c.has_webhook,
    enabled: !!c.enabled,
    project: c.project || "",
    customer: c.customer || "",
    email_account: c.email_account || "",
  });
  for (const e of EVENTS) form[e.field] = !!c[e.field];
  openEditor();
}

const projectOptions = computed(() => [
  { label: __("Any project"), value: "" },
  ...(scope.data?.projects || []).map((p: any) => ({
    label: p.project_name || p.name,
    value: p.name,
  })),
]);
const customerOptions = computed(() => [
  { label: __("Any client"), value: "" },
  ...(scope.data?.customers || []).map((c: string) => ({ label: c, value: c })),
]);
const inboxOptions = computed(() => [
  { label: __("Any inbox"), value: "" },
  ...(scope.data?.inboxes || []).map((i: any) => ({
    label: i.email_id || i.name,
    value: i.name,
  })),
]);

const saveRes = createResource({
  url: "helpdesk.api.pumble.save_channel",
  onSuccess: () => {
    toast.success(__("Channel saved"));
    editing.value = false;
    channels.reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not save the channel")),
});

function save() {
  if (!(form.channel_name || "").trim()) {
    toast.error(__("Give the channel a name"));
    return;
  }
  const data: Record<string, any> = { ...form };
  delete data.has_webhook;
  data.enabled = data.enabled ? 1 : 0;
  for (const e of EVENTS) data[e.field] = data[e.field] ? 1 : 0;
  saveRes.submit({ data });
}

// Errors from these two are toasted in the handlers below, so the resources
// must not fall through to the app-wide handler as well (two toasts).
const testRes = createResource({
  url: "helpdesk.api.pumble.send_test",
  onError: () => {},
});
const deleteRes = createResource({
  url: "helpdesk.api.pumble.delete_channel",
  onError: () => {},
});

const testing = ref<string | null>(null);
async function test(c: any) {
  testing.value = c.name;
  try {
    const result = await testRes.submit({ name: c.name });
    if (result?.ok) toast.success(__("Test message sent to {0}", [c.channel_name]));
    else toast.error(result?.error || __("Pumble did not accept the message"));
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not send the test message"));
  } finally {
    testing.value = null;
    log.reload();
  }
}

// Delete is two clicks: the first arms it for a few seconds.
const armed = ref<string | null>(null);
let armTimer: ReturnType<typeof setTimeout> | undefined;
async function remove(c: any) {
  if (armed.value !== c.name) {
    armed.value = c.name;
    clearTimeout(armTimer);
    armTimer = setTimeout(() => (armed.value = null), 4000);
    return;
  }
  armed.value = null;
  try {
    await deleteRes.submit({ name: c.name });
    toast.success(__("Channel removed"));
    channels.reload();
    log.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not remove the channel"));
  }
}

const EVENT_LABEL: Record<string, string> = Object.fromEntries(
  EVENTS.map((e) => [e.field.replace(/^on_/, ""), e.label])
);
function eventLabel(event: string) {
  return event === "test" ? __("Test message") : EVENT_LABEL[event] || event;
}
function eventSummary(c: any) {
  const on = EVENTS.filter((e) => c[e.field]).map((e) => e.label);
  return on.length ? on.join(" · ") : __("No events selected");
}
function scopeSummary(c: any) {
  const parts: string[] = [];
  if (c.project) parts.push(__("project {0}", [c.project_name || c.project]));
  if (c.customer) parts.push(__("client {0}", [c.customer]));
  if (c.email_account) parts.push(__("inbox {0}", [c.email_account]));
  return parts.length
    ? __("Only for {0}", [parts.join(", ")])
    : __("All projects, clients and inboxes");
}
function channelLabel(name: string) {
  return (channels.data || []).find((c: any) => c.name === name)?.channel_name || name;
}
</script>
