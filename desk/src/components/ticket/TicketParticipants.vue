<template>
  <div class="flex flex-col gap-2">
    <div
      class="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-cyan-700 px-3 py-2 -mx-3 rounded-md bg-cyan-50"
    >
      <span class="h-3 w-1 rounded-full bg-cyan-500" />
      {{ __("Participants") }}
    </div>
    <p class="text-xs text-ink-gray-5 -mt-1">
      {{ __("Add colleagues to CC them on replies.") }}
    </p>

    <div v-if="participants.data?.length" class="flex flex-col gap-1.5">
      <div
        v-for="p in participants.data"
        :key="p.name"
        class="flex items-center gap-2 text-sm"
      >
        <Avatar size="xs" :label="p.email" />
        <span class="flex-1 truncate text-ink-gray-8">{{ p.email }}</span>
        <button
          type="button"
          class="text-ink-gray-4 hover:text-ink-red-3 shrink-0"
          :aria-label="__('Remove participant')"
          @click="remove(p.name)"
        >
          <LucideX class="size-3.5" />
        </button>
      </div>
    </div>

    <form class="flex items-center gap-2" @submit.prevent="add">
      <input
        v-model="email"
        type="email"
        :placeholder="__('colleague@company.com')"
        class="flex-1 text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-1.5 text-ink-gray-8 focus:outline-none focus:border-blue-400"
      />
      <Button
        :label="__('Add')"
        theme="blue"
        variant="subtle"
        size="sm"
        :loading="addRes.loading"
        @click="add"
      />
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { Avatar, Button, createResource, toast } from "frappe-ui";
import { __ } from "@/translation";
import LucideX from "~icons/lucide/x";

interface P {
  ticketId: string;
}
const props = defineProps<P>();
const email = ref("");

const participants = createResource({
  url: "helpdesk.api.participant.get_participants",
  makeParams: () => ({ ticket: props.ticketId }),
  auto: true,
});

watch(
  () => props.ticketId,
  () => participants.reload()
);

const addRes = createResource({
  url: "helpdesk.api.participant.add_participant",
  onSuccess: () => {
    email.value = "";
    participants.reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not add participant")),
});
function add() {
  const e = email.value.trim();
  if (!e) return;
  addRes.submit({ ticket: props.ticketId, email: e });
}

const removeRes = createResource({
  url: "helpdesk.api.participant.remove_participant",
  onSuccess: () => participants.reload(),
});
function remove(name: string) {
  removeRes.submit({ name });
}
</script>
