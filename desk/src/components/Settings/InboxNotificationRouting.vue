<template>
  <!-- Who is emailed when a new ticket lands in this inbox. Self-contained
       (own load/save) so EmailEdit only has to mount it. -->
  <div class="flex flex-col gap-3 rounded-md p-3 ring-1 ring-outline-gray-modals">
    <div class="flex flex-col gap-0.5">
      <span class="text-base font-semibold text-ink-gray-8">
        {{ __("New ticket emails") }}
      </span>
      <span class="text-p-sm text-ink-gray-5">
        {{ __("Who gets emailed when a ticket arrives in this inbox.") }}
      </span>
    </div>

    <div class="flex flex-col gap-2">
      <label
        v-for="opt in OPTIONS"
        :key="opt.value"
        class="flex items-start gap-2 cursor-pointer"
      >
        <input
          v-model="notify"
          type="radio"
          class="mt-1 accent-blue-600"
          :name="`inbox-notify-${emailAccount}`"
          :value="opt.value"
        />
        <span class="flex flex-col">
          <span class="text-sm text-ink-gray-8">{{ opt.label }}</span>
          <span class="text-p-sm text-ink-gray-5">{{ opt.description }}</span>
        </span>
      </label>
    </div>

    <div v-if="notify === 'Selected agents'" class="flex flex-col gap-2">
      <TextInput v-model="search" size="sm" :placeholder="__('Search agents')" />
      <div class="max-h-48 overflow-y-auto flex flex-col gap-1 rounded-md bg-surface-gray-1 p-2">
        <label
          v-for="a in filteredAgents"
          :key="a.value"
          class="flex items-center gap-2 text-sm text-ink-gray-7 cursor-pointer"
        >
          <input
            type="checkbox"
            class="size-4 accent-blue-600"
            :checked="selected.has(a.value)"
            @change="toggle(a.value)"
          />
          {{ a.label }}
        </label>
        <span v-if="!filteredAgents.length" class="text-p-sm text-ink-gray-4">
          {{ __("No agents found") }}
        </span>
      </div>
      <span class="text-p-sm text-ink-gray-5">
        {{ __("{0} selected", [selected.size]) }}
      </span>
    </div>

    <div class="flex justify-end">
      <Button
        size="sm"
        variant="subtle"
        :label="__('Save notification settings')"
        :loading="saveRes.loading"
        :disabled="!dirty"
        @click="save"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  Button,
  TextInput,
  createListResource,
  createResource,
  toast,
} from "frappe-ui";
import { __ } from "@/translation";

const props = defineProps<{ emailAccount: string }>();

const OPTIONS = [
  {
    value: "Automatic",
    label: __("Automatic"),
    description: __(
      "Agents on the client's project. Everyone, if the ticket can't be matched to a project."
    ),
  },
  {
    value: "Selected agents",
    label: __("Selected agents"),
    description: __("Only the agents you pick."),
  },
  {
    value: "No one",
    label: __("No one"),
    description: __("Don't email anyone. Tickets still show up in the app."),
  },
];

const notify = ref("Automatic");
const selected = ref(new Set<string>());
const search = ref("");
const saved = ref({ notify: "Automatic", agents: [] as string[] });

const agents = createListResource({
  doctype: "HD Agent",
  fields: ["name", "agent_name"],
  filters: { is_active: 1 },
  pageLength: 500,
  auto: true,
});
const agentOptions = computed(() =>
  (agents.data || []).map((a: any) => ({
    value: a.name,
    label: a.agent_name || a.name,
  }))
);
const filteredAgents = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return agentOptions.value;
  return agentOptions.value.filter(
    (a: any) =>
      a.label.toLowerCase().includes(q) || a.value.toLowerCase().includes(q)
  );
});

function apply(data: any) {
  saved.value = {
    notify: data?.notify || "Automatic",
    agents: [...(data?.agents || [])],
  };
  notify.value = saved.value.notify;
  selected.value = new Set(saved.value.agents);
}

const routing = createResource({
  url: "helpdesk.api.settings.email.get_inbox_routing",
  makeParams: () => ({ email_account: props.emailAccount }),
  auto: !!props.emailAccount,
  onSuccess: apply,
});
watch(
  () => props.emailAccount,
  (account) => {
    if (account) routing.reload();
  }
);

function toggle(agent: string) {
  const next = new Set(selected.value);
  if (next.has(agent)) next.delete(agent);
  else next.add(agent);
  selected.value = next;
}

const dirty = computed(() => {
  if (notify.value !== saved.value.notify) return true;
  if (notify.value !== "Selected agents") return false;
  const now = [...selected.value].sort().join(",");
  const before = [...saved.value.agents].sort().join(",");
  return now !== before;
});

const saveRes = createResource({
  url: "helpdesk.api.settings.email.set_inbox_routing",
  onSuccess: (data: any) => {
    apply(data);
    toast.success(__("Notification settings saved"));
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not save notification settings")),
});

function save() {
  if (notify.value === "Selected agents" && !selected.value.size) {
    toast.error(__("Pick at least one agent, or choose Automatic"));
    return;
  }
  saveRes.submit({
    email_account: props.emailAccount,
    notify: notify.value,
    agents: notify.value === "Selected agents" ? [...selected.value] : [],
  });
}
</script>
