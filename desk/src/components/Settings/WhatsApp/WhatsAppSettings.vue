<template>
  <SettingsLayoutBase
    :title="__('WhatsApp')"
    :description="
      __(
        'Customers message your WhatsApp Business number; each conversation becomes a ticket, and agent replies go back on WhatsApp.'
      )
    "
  >
    <template #header-actions>
      <Button
        variant="solid"
        :label="__('Save')"
        :loading="saveRes.loading"
        :disabled="!settings.data"
        @click="save"
      />
    </template>

    <template #content>
      <div v-if="!settings.data" class="py-10 text-center text-sm text-ink-gray-5">
        {{ __("Loading...") }}
      </div>
      <div v-else class="flex flex-col gap-6 pb-6">
        <!-- On / off -->
        <div
          class="flex items-center justify-between gap-4 rounded-md border border-outline-gray-2 p-3"
        >
          <div class="flex flex-col">
            <span class="text-base font-medium text-ink-gray-8">
              {{ __("WhatsApp channel") }}
            </span>
            <span class="text-p-sm" :class="statusClass">{{ statusText }}</span>
          </div>
          <Switch v-model="form.enabled" />
        </div>

        <!-- Meta account -->
        <section class="flex flex-col gap-3">
          <h3 class="text-base font-semibold text-ink-gray-8">{{ __("Meta account") }}</h3>
          <p class="text-p-sm text-ink-gray-6">
            {{
              __(
                "From the Meta app dashboard (developers.facebook.com): WhatsApp > API Setup for the phone number ID, a permanent System User token with the whatsapp_business_messaging permission, and App settings > Basic for the app secret."
              )
            }}
          </p>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <FormControl
              v-model="form.phone_number_id"
              :label="__('Phone number ID')"
              placeholder="123456789012345"
            />
            <FormControl
              v-model="form.business_account_id"
              :label="__('Business account ID (optional)')"
            />
            <FormControl
              v-model="form.access_token"
              type="password"
              :label="__('Access token')"
              :placeholder="
                settings.data.has_access_token
                  ? __('Saved. Leave empty to keep it.')
                  : __('Paste the token')
              "
            />
            <FormControl
              v-model="form.app_secret"
              type="password"
              :label="__('App secret')"
              :placeholder="
                settings.data.has_app_secret
                  ? __('Saved. Leave empty to keep it.')
                  : __('Paste the app secret')
              "
            />
            <FormControl
              v-model="form.graph_version"
              :label="__('Graph API version')"
              placeholder="v23.0"
            />
            <FormControl
              v-if="settings.data.display_phone_number"
              :model-value="'+' + settings.data.display_phone_number"
              :label="__('Business number')"
              disabled
            />
          </div>
        </section>

        <!-- Webhook -->
        <section class="flex flex-col gap-3">
          <h3 class="text-base font-semibold text-ink-gray-8">{{ __("Webhook") }}</h3>
          <p class="text-p-sm text-ink-gray-6">
            {{
              __(
                "In the Meta app: WhatsApp > Configuration > Webhook. Paste the callback URL and the verify token, verify, then subscribe to the messages field."
              )
            }}
          </p>
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Callback URL") }}</span>
            <div class="flex items-center gap-2">
              <code
                class="min-w-0 flex-1 truncate rounded bg-surface-gray-2 px-2 py-1.5 text-p-sm text-ink-gray-8"
                :title="settings.data.webhook_url"
              >
                {{ settings.data.webhook_url }}
              </code>
              <Button :label="__('Copy')" @click="copy(settings.data.webhook_url)" />
            </div>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Verify token") }}</span>
            <div class="flex items-center gap-2">
              <code
                class="min-w-0 flex-1 truncate rounded bg-surface-gray-2 px-2 py-1.5 text-p-sm text-ink-gray-8"
              >
                {{ settings.data.verify_token }}
              </code>
              <Button :label="__('Copy')" @click="copy(settings.data.verify_token)" />
              <Button
                variant="ghost"
                :label="__('New token')"
                :loading="tokenRes.loading"
                @click="newToken"
              />
            </div>
          </div>
        </section>

        <!-- Tickets -->
        <section class="flex flex-col gap-3">
          <h3 class="text-base font-semibold text-ink-gray-8">{{ __("Tickets") }}</h3>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <FormControl
              v-model="form.default_team"
              type="select"
              :options="teamOptions"
              :label="__('Team for new tickets')"
            />
            <FormControl
              v-model="form.reopen_window_hours"
              type="number"
              min="0"
              :label="__('Reopen a resolved ticket within (hours)')"
            />
          </div>
          <div class="flex items-center justify-between gap-4">
            <span class="text-p-sm text-ink-gray-7">
              {{ __("Acknowledge a new ticket on WhatsApp") }}
            </span>
            <Switch v-model="form.send_acknowledgement" />
          </div>
          <FormControl
            v-if="form.send_acknowledgement"
            v-model="form.acknowledgement_message"
            type="textarea"
            :rows="2"
            :label="__('Acknowledgement')"
            :placeholder="defaultAck"
            :description="__('{ticket} is the ticket number, {name} the customer\'s first name.')"
          />
        </section>

        <!-- Template -->
        <section class="flex flex-col gap-3">
          <h3 class="text-base font-semibold text-ink-gray-8">
            {{ __("Replies after 24 hours") }}
          </h3>
          <!-- Text set in the script: its template placeholders clash with Vue's. -->
          <p class="text-p-sm text-ink-gray-6">{{ templateHelp }}</p>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <FormControl
              v-model="form.template_name"
              :label="__('Template name')"
              placeholder="ticket_reply"
            />
            <FormControl
              v-model="form.template_language"
              :label="__('Template language')"
              placeholder="en"
            />
          </div>
        </section>

        <!-- Test -->
        <section class="flex flex-col gap-3">
          <h3 class="text-base font-semibold text-ink-gray-8">{{ __("Test") }}</h3>
          <p class="text-p-sm text-ink-gray-6">
            {{
              __(
                "Sends Meta's hello_world template to a number. Save your settings first. While the Meta app is in development mode, the number must be on its list of test recipients."
              )
            }}
          </p>
          <div class="flex items-end gap-2">
            <FormControl
              v-model="testNumber"
              class="flex-1"
              :label="__('Number, with country code')"
              placeholder="254712345678"
            />
            <Button
              :label="__('Send test')"
              :loading="testRes.loading"
              :disabled="!testNumber.trim()"
              @click="sendTest"
            />
          </div>
        </section>

        <!-- Log -->
        <section class="flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold text-ink-gray-8">
              {{ __("Recent messages") }}
            </h3>
            <Button variant="ghost" :label="__('Refresh')" @click="log.reload()" />
          </div>
          <p v-if="!log.data?.length" class="text-p-sm text-ink-gray-5">
            {{ __("Nothing yet.") }}
          </p>
          <div
            v-else
            class="flex flex-col divide-y divide-outline-gray-1 rounded-md border border-outline-gray-2"
          >
            <div
              v-for="m in log.data"
              :key="m.name"
              class="flex items-start gap-3 px-3 py-1.5 text-p-sm"
            >
              <span class="w-24 shrink-0 text-ink-gray-5">{{ timeAgo(m.creation) }}</span>
              <span class="w-6 shrink-0 text-ink-gray-6" :title="__(m.direction)">
                {{ m.direction === "Incoming" ? "←" : "→" }}
              </span>
              <span class="w-32 shrink-0 truncate text-ink-gray-7" :title="m.contact_name">
                +{{ m.wa_id }}
              </span>
              <span class="w-20 shrink-0 font-medium" :class="logClass(m.status)">
                {{ __(m.status || "") }}
              </span>
              <span class="min-w-0 flex-1 truncate text-ink-gray-7" :title="m.error || m.body">
                <template v-if="m.ticket">#{{ m.ticket }} · </template>{{ m.error || m.body }}
              </span>
            </div>
          </div>
        </section>
      </div>
    </template>
  </SettingsLayoutBase>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { Button, FormControl, Switch, createResource, toast } from "frappe-ui";
import SettingsLayoutBase from "@/components/layouts/SettingsLayoutBase.vue";
import { __ } from "@/translation";
import { timeAgo } from "@/utils";

const templateHelp = __(
  "WhatsApp only allows free text within 24 hours of the customer's last message. After that a reply can only go as an approved template. Create one in WhatsApp Manager whose body takes two values: {{1}} the ticket number and {{2}} the reply."
);
const defaultAck =
  "Thanks{name}! We have your message and opened ticket #{ticket}. We will reply here as soon as we can.";

const form = reactive<Record<string, any>>({});

const settings = createResource({
  url: "helpdesk.api.whatsapp.get_settings",
  auto: true,
  onSuccess: (d: any) => {
    Object.assign(form, {
      enabled: !!d.enabled,
      phone_number_id: d.phone_number_id || "",
      business_account_id: d.business_account_id || "",
      graph_version: d.graph_version || "v23.0",
      default_team: d.default_team || "",
      reopen_window_hours: d.reopen_window_hours ?? 72,
      send_acknowledgement: !!d.send_acknowledgement,
      acknowledgement_message: d.acknowledgement_message || "",
      template_name: d.template_name || "",
      template_language: d.template_language || "en",
      access_token: "",
      app_secret: "",
    });
  },
});
const log = createResource({ url: "helpdesk.api.whatsapp.get_log", auto: true });

const teamOptions = computed(() => [
  { label: __("No team"), value: "" },
  ...(settings.data?.teams || []).map((t: string) => ({ label: t, value: t })),
]);

const statusText = computed(() => {
  const d = settings.data;
  if (!d) return "";
  if (d.ready) {
    return d.display_phone_number
      ? __("On, receiving messages for +{0}", [d.display_phone_number])
      : __("On. Waiting for the first message to arrive.");
  }
  return d.enabled
    ? __("On, but the phone number ID or access token is missing")
    : __("Off");
});
const statusClass = computed(() =>
  settings.data?.ready ? "text-green-700" : "text-ink-gray-5"
);

const saveRes = createResource({
  url: "helpdesk.api.whatsapp.save_settings",
  onError: () => {},
});
async function save() {
  try {
    await saveRes.submit({
      data: {
        ...form,
        enabled: form.enabled ? 1 : 0,
        send_acknowledgement: form.send_acknowledgement ? 1 : 0,
        reopen_window_hours: Number(form.reopen_window_hours) || 0,
      },
    });
    toast.success(__("WhatsApp settings saved"));
    settings.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not save the settings"));
  }
}

const tokenRes = createResource({
  url: "helpdesk.api.whatsapp.new_verify_token",
  onError: () => {},
});
async function newToken() {
  try {
    await tokenRes.submit();
    toast.success(__("New verify token. Verify the webhook in Meta again with it."));
    settings.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not make a new token"));
  }
}

const testNumber = ref("");
const testRes = createResource({
  url: "helpdesk.api.whatsapp.send_test",
  onError: () => {},
});
async function sendTest() {
  try {
    await testRes.submit({ to: testNumber.value });
    toast.success(__("Test message sent"));
    log.reload();
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not send the test"));
    log.reload();
  }
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(__("Copied"));
  } catch {
    toast.error(__("Could not copy. Select the text and copy it yourself."));
  }
}

function logClass(status: string) {
  if (status === "Failed") return "text-ink-red-3";
  if (status === "Read" || status === "Delivered") return "text-green-700";
  return "text-ink-gray-6";
}
</script>
