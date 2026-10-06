<template>
  <Dialog
    v-model="open"
    :options="{ title: __('Sign off {0}', [card?.name || '']), size: 'lg' }"
  >
    <template #body-content>
      <div class="flex flex-col gap-3">
        <p class="text-p-sm text-ink-gray-6">
          {{
            agentMode
              ? __(
                  "Hand your device to the client to sign, or record that they signed the printed copy."
                )
              : __("Check the job card, then sign to confirm the work was done.")
          }}
        </p>
        <Button
          class="self-start"
          variant="subtle"
          :label="__('View the job card')"
          @click="printJobCard(card.name, false)"
        >
          <template #prefix><LucideFileText class="size-4" /></template>
        </Button>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FormControl v-model="signedBy" :label="__('Name')" maxlength="140" />
          <FormControl
            v-model="designation"
            :label="__('Title (optional)')"
            maxlength="140"
            :placeholder="__('e.g. Finance manager')"
          />
        </div>
        <label
          v-if="agentMode"
          class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-8"
        >
          <input v-model="onPaper" type="checkbox" class="size-4 accent-blue-600" />
          {{ __("They signed the printed copy") }}
        </label>
        <SignaturePad v-if="!onPaper" ref="pad" />
        <FormControl
          v-model="comments"
          type="textarea"
          :rows="2"
          :label="__('Comments (optional)')"
        />
        <label class="flex cursor-pointer items-center gap-2 text-sm text-ink-gray-8">
          <input v-model="satisfied" type="checkbox" class="size-4 accent-blue-600" />
          {{
            agentMode
              ? __("The client accepts the work as done")
              : __("The work was done to my satisfaction")
          }}
        </label>
      </div>
    </template>
    <template #actions>
      <div class="flex w-full justify-end gap-2">
        <Button :label="__('Cancel')" @click="open = false" />
        <Button
          variant="solid"
          :label="__('Sign off')"
          :loading="signRes.loading"
          @click="submit"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { Button, Dialog, FormControl, createResource, toast } from "frappe-ui";
import { __ } from "@/translation";
import LucideFileText from "~icons/lucide/file-text";
import SignaturePad from "./SignaturePad.vue";
import { printJobCard } from "./print";

const props = defineProps<{ card: any; agentMode?: boolean }>();
const open = defineModel<boolean>({ default: false });
const emit = defineEmits<{ (e: "signed", card: any): void }>();

const signedBy = ref("");
const designation = ref("");
const comments = ref("");
const satisfied = ref(true);
const onPaper = ref(false);
const pad = ref<any>(null);

// Fresh fields each time it opens (it may mount already open).
watch(open, (isOpen) => {
  if (!isOpen) return;
  signedBy.value = props.card?.contact_name || "";
  designation.value = "";
  comments.value = "";
  satisfied.value = true;
  onPaper.value = false;
}, { immediate: true });

const signRes = createResource({
  url: "helpdesk.api.job_card.sign_job_card",
  onError: () => {},
});

async function submit() {
  if (!signedBy.value.trim()) {
    toast.error(__("Enter the name of the person signing"));
    return;
  }
  const signature = onPaper.value ? null : pad.value?.toDataURL();
  if (!onPaper.value && !signature) {
    toast.error(__("Sign in the box first"));
    return;
  }
  try {
    const card = await signRes.submit({
      name: props.card.name,
      signed_by: signedBy.value,
      designation: designation.value,
      signature,
      comments: comments.value,
      satisfied: satisfied.value ? 1 : 0,
    });
    toast.success(__("Job card signed off"));
    open.value = false;
    emit("signed", card);
  } catch (e: any) {
    toast.error(e?.messages?.[0] || __("Could not sign the job card"));
  }
}
</script>
