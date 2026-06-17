<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between">
      <span class="text-sm font-semibold text-ink-gray-8">
        {{ __("Attachments") }}
        <span v-if="files.data?.length" class="font-normal text-ink-gray-5">
          ({{ files.data.length }})
        </span>
      </span>
      <FileUploader v-if="editable" @success="onUploaded">
        <template #default="{ uploading, openFileSelector }">
          <Button
            size="sm"
            variant="subtle"
            :loading="uploading"
            @click="openFileSelector"
          >
            <template #prefix>
              <LucidePaperclip class="size-3.5" />
            </template>
            {{ __("Attach") }}
          </Button>
        </template>
      </FileUploader>
    </div>

    <div v-if="files.data?.length" class="flex flex-col gap-1.5">
      <div
        v-for="f in files.data"
        :key="f.name"
        class="group flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 bg-surface-gray-1 hover:bg-surface-gray-2 transition-colors"
      >
        <LucideFile class="size-4 shrink-0 text-ink-gray-5" />
        <a
          :href="f.file_url"
          target="_blank"
          rel="noopener"
          class="flex-1 truncate text-sm text-ink-gray-8 hover:text-blue-600"
        >
          {{ f.file_name }}
        </a>
        <span class="shrink-0 text-xs text-ink-gray-4">
          {{ formatBytes(f.file_size) }}
        </span>
        <button
          v-if="editable"
          class="shrink-0 rounded p-0.5 text-ink-gray-4 opacity-0 transition-all hover:bg-surface-gray-3 hover:text-red-500 group-hover:opacity-100"
          :title="__('Remove')"
          @click="remove(f.name)"
        >
          <LucideX class="size-3.5" />
        </button>
      </div>
    </div>
    <p v-else class="text-sm text-ink-gray-4">{{ __("No attachments.") }}</p>
  </div>
</template>

<script setup lang="ts">
import { watch } from "vue";
import { call, createListResource, FileUploader, toast } from "frappe-ui";
import { __ } from "@/translation";
import LucidePaperclip from "~icons/lucide/paperclip";
import LucideFile from "~icons/lucide/file";
import LucideX from "~icons/lucide/x";

interface P {
  doctype: string;
  docname: string;
  editable?: boolean;
}
const props = withDefaults(defineProps<P>(), { editable: true });

const files = createListResource({
  doctype: "File",
  fields: ["name", "file_name", "file_url", "file_size"],
  filters: {
    attached_to_doctype: props.doctype,
    attached_to_name: props.docname,
    is_folder: 0,
  },
  orderBy: "creation desc",
  pageLength: 50,
  auto: true,
});

// Reload when a different record is shown (e.g. task detail dialog)
watch(
  () => props.docname,
  (val) => { if (val) files.reload(); }
);

async function onUploaded(file: any) {
  try {
    await call("frappe.client.set_value", {
      doctype: "File",
      name: file.name,
      fieldname: {
        attached_to_doctype: props.doctype,
        attached_to_name: props.docname,
      },
    });
  } catch {
    // File may already be attached if FileUploader passed doctype/docname
  }
  files.reload();
}

async function remove(name: string) {
  try {
    await call("frappe.client.delete", { doctype: "File", name });
    files.reload();
  } catch {
    toast.error(__("Could not remove file"));
  }
}

function formatBytes(b: number): string {
  if (!b) return "";
  if (b < 1024) return b + " B";
  if (b < 1_048_576) return (b / 1024).toFixed(1) + " KB";
  return (b / 1_048_576).toFixed(1) + " MB";
}

defineExpose({ reload: () => files.reload() });
</script>
