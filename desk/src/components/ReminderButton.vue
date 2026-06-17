<template>
  <button
    class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8 transition-colors"
    :title="__('Set a reminder')"
    @click="openDialog"
  >
    <LucideBell class="size-3.5" />
    <span class="hidden sm:inline">{{ __("Remind me") }}</span>
  </button>

  <Dialog v-if="open" v-model="open" :options="{ title: __('Set a reminder'), size: 'sm' }">
    <template #body-content>
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-ink-gray-6">
            {{ __("Message") }}
          </label>
          <textarea
            v-model="form.message"
            rows="2"
            :placeholder="__('What do you want to be reminded about?')"
            class="w-full text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-ink-gray-6">
            {{ __("Remind at") }}
          </label>
          <input
            v-model="form.remindAt"
            type="datetime-local"
            class="w-full text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-7 focus:outline-none focus:border-blue-400"
          />
        </div>
      </div>
    </template>
    <template #actions>
      <Button
        variant="solid"
        theme="blue"
        class="w-full"
        :loading="saving"
        :disabled="!form.message.trim() || !form.remindAt"
        @click="save"
      >
        {{ __("Set reminder") }}
      </Button>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { Button, Dialog, call, toast } from "frappe-ui";
import { __ } from "@/translation";
import LucideBell from "~icons/lucide/bell";

interface P {
  doctype?: string;
  docname?: string;
}
const props = defineProps<P>();

const open = ref(false);
const saving = ref(false);
const form = reactive({ message: "", remindAt: "" });

function openDialog() {
  form.message = props.docname
    ? `${__("Follow up on")} ${props.doctype} ${props.docname}`
    : "";
  // Default: tomorrow at 09:00
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(9, 0, 0, 0);
  form.remindAt = d.toISOString().slice(0, 16);
  open.value = true;
}

async function save() {
  if (!form.message.trim() || !form.remindAt) return;
  saving.value = true;
  try {
    await call("helpdesk.api.reminder.create_reminder", {
      message: form.message.trim(),
      remind_at: form.remindAt.replace("T", " ") + ":00",
      reference_doctype: props.doctype || null,
      reference_name: props.docname || null,
    });
    toast.success(__("Reminder set"));
    open.value = false;
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not set reminder"));
  } finally {
    saving.value = false;
  }
}
</script>
