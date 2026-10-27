<template>
  <!-- The team's own notes on a project or task: access details, decisions,
       context. Agents only — the parent mounts this on the agent side, and
       the API refuses anyone who isn't an agent on the record. -->
  <div class="flex flex-col gap-3">
    <div class="flex items-center gap-2">
      <div
        class="size-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center"
      >
        <LucideStickyNote class="size-4" />
      </div>
      <span class="text-sm font-semibold text-ink-gray-8">{{ __("Notes") }}</span>
      <span v-if="list.length" class="text-xs text-ink-gray-5">
        · {{ list.length }}
      </span>
      <span
        class="ms-auto inline-flex items-center gap-1 text-[11px] text-ink-gray-5"
        :title="__('Only your team sees these — never the customer.')"
      >
        <LucideLock class="size-3" />
        {{ __("Team only") }}
      </span>
    </div>

    <!-- New note -->
    <div class="flex flex-col gap-2">
      <textarea
        v-model="draft"
        rows="2"
        maxlength="20000"
        :placeholder="__('Add a note for the team…')"
        class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-y"
        @keydown.ctrl.enter.prevent="addNote"
        @keydown.meta.enter.prevent="addNote"
      />
      <div v-if="draft.trim()" class="flex items-center justify-end gap-2">
        <span class="text-[11px] text-ink-gray-4">
          {{ __("Ctrl+Enter to save") }}
        </span>
        <Button
          size="sm"
          variant="solid"
          :label="__('Add note')"
          :loading="addRes.loading"
          @click="addNote"
        />
      </div>
    </div>

    <!-- Notes, pinned first -->
    <div
      v-for="n in list"
      :key="n.name"
      class="rounded-lg border px-3 py-2.5"
      :class="
        n.pinned
          ? 'border-amber-200 bg-amber-50'
          : 'border-outline-gray-1 bg-surface-gray-1'
      "
    >
      <div class="flex items-center gap-2 text-xs">
        <Avatar size="xs" :label="n.author_name" />
        <span class="font-medium text-ink-gray-8 truncate">
          {{ n.author_name }}
        </span>
        <Tooltip :text="dateFormat(n.creation, dateTooltipFormat)">
          <span class="text-ink-gray-5 shrink-0">{{ timeAgo(n.creation) }}</span>
        </Tooltip>
        <Tooltip
          v-if="n.edited_on"
          :text="dateFormat(n.edited_on, dateTooltipFormat)"
        >
          <span class="text-ink-gray-4 shrink-0">· {{ __("edited") }}</span>
        </Tooltip>
        <span class="flex-1" />
        <button
          type="button"
          class="rounded p-1 hover:bg-surface-gray-3"
          :class="n.pinned ? 'text-amber-600' : 'text-ink-gray-4 hover:text-ink-gray-8'"
          :title="n.pinned ? __('Unpin') : __('Pin to the top')"
          :aria-pressed="!!n.pinned"
          @click="togglePin(n)"
        >
          <LucidePin class="size-3.5" />
        </button>
        <template v-if="n.can_change && editing !== n.name">
          <button
            type="button"
            class="rounded p-1 text-ink-gray-4 hover:text-ink-gray-8 hover:bg-surface-gray-3"
            :title="__('Edit note')"
            @click="startEdit(n)"
          >
            <LucidePencil class="size-3.5" />
          </button>
          <button
            type="button"
            class="rounded p-1 text-ink-gray-4 hover:text-red-600 hover:bg-surface-gray-3"
            :title="__('Delete note')"
            @click="removeNote(n)"
          >
            <LucideTrash2 class="size-3.5" />
          </button>
        </template>
      </div>

      <div v-if="editing === n.name" class="mt-2 flex flex-col gap-2">
        <textarea
          v-model="editDraft"
          rows="3"
          maxlength="20000"
          class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-y"
          @keydown.ctrl.enter.prevent="saveEdit(n)"
          @keydown.meta.enter.prevent="saveEdit(n)"
          @keydown.esc.prevent="editing = null"
        />
        <div class="flex items-center justify-end gap-2">
          <Button size="sm" :label="__('Cancel')" @click="editing = null" />
          <Button
            size="sm"
            variant="solid"
            :label="__('Save')"
            :disabled="!editDraft.trim()"
            :loading="updateRes.loading"
            @click="saveEdit(n)"
          />
        </div>
      </div>
      <p
        v-else
        class="mt-1.5 text-sm text-ink-gray-8 whitespace-pre-wrap break-words"
      >{{ n.content }}</p>
    </div>

    <p v-if="!notes.loading && !list.length" class="text-xs text-ink-gray-4">
      {{
        __(
          "No notes yet — access details, decisions, anything the team should know."
        )
      }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Avatar, Button, Tooltip, createResource, toast } from "frappe-ui";
import { __ } from "@/translation";
import { dateFormat, dateTooltipFormat, timeAgo } from "@/utils";
import LucideStickyNote from "~icons/lucide/sticky-note";
import LucideLock from "~icons/lucide/lock";
import LucidePin from "~icons/lucide/pin";
import LucidePencil from "~icons/lucide/pencil";
import LucideTrash2 from "~icons/lucide/trash-2";

const props = defineProps<{
  referenceDoctype: "HD Project" | "HD Addon Task";
  referenceName: string;
}>();

const draft = ref("");
const editing = ref<string | null>(null);
const editDraft = ref("");

const notes = createResource({
  url: "helpdesk.api.notes.get_notes",
  makeParams: () => ({
    reference_doctype: props.referenceDoctype,
    reference_name: props.referenceName,
  }),
  auto: !!props.referenceName,
  onError: (e: any) => console.warn("[helpdesk] notes:", e),
});
const list = computed<any[]>(() => notes.data || []);

watch(
  () => props.referenceName,
  (name) => {
    draft.value = "";
    editing.value = null;
    if (name) notes.reload();
  }
);

function failed(fallback: string) {
  return (e: any) => toast.error(e?.messages?.[0] || fallback);
}

const addRes = createResource({
  url: "helpdesk.api.notes.add_note",
  onSuccess: () => {
    draft.value = "";
    notes.reload();
  },
  onError: failed(__("Could not save the note")),
});
function addNote() {
  const content = draft.value.trim();
  if (!content || addRes.loading) return;
  addRes.submit({
    reference_doctype: props.referenceDoctype,
    reference_name: props.referenceName,
    content,
  });
}

const updateRes = createResource({
  url: "helpdesk.api.notes.update_note",
  onSuccess: () => {
    editing.value = null;
    notes.reload();
  },
  onError: failed(__("Could not update the note")),
});
function startEdit(n: any) {
  editDraft.value = n.content || "";
  editing.value = n.name;
}
function saveEdit(n: any) {
  const content = editDraft.value.trim();
  if (!content) return;
  if (content === n.content) {
    editing.value = null;
    return;
  }
  updateRes.submit({ name: n.name, content });
}
function togglePin(n: any) {
  updateRes.submit({ name: n.name, pinned: n.pinned ? 0 : 1 });
}

const deleteRes = createResource({
  url: "helpdesk.api.notes.delete_note",
  onSuccess: () => notes.reload(),
  onError: failed(__("Could not delete the note")),
});
function removeNote(n: any) {
  if (!window.confirm(__("Delete this note? This can't be undone."))) return;
  deleteRes.submit({ name: n.name });
}
</script>
