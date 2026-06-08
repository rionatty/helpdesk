<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <div class="text-sm font-semibold text-ink-gray-8">
        {{ __("Features") }}
      </div>
      <span v-if="features.data?.length" class="text-xs text-ink-gray-5">
        {{ features.data.length }}
      </span>
    </div>

    <div v-if="features.data?.length" class="flex flex-col gap-2">
      <div
        v-for="f in features.data"
        :key="f.name"
        class="rounded-lg border border-outline-gray-1 bg-surface-gray-1 px-3 py-2.5 flex flex-col gap-2"
      >
        <div class="flex items-start gap-2">
          <span
            class="mt-1.5 size-2 rounded-full shrink-0"
            :class="dotClass(f.status)"
          />
          <span class="text-sm flex-1 font-medium text-ink-gray-8 leading-snug">
            {{ f.feature_title }}
          </span>
          <Badge :label="f.status" :theme="statusTheme(f.status)" variant="subtle" />
          <button
            v-if="editable"
            type="button"
            class="text-ink-gray-4 hover:text-ink-red-3 shrink-0"
            :aria-label="__('Delete feature')"
            @click="remove(f.name)"
          >
            <LucideTrash2 class="size-3.5" />
          </button>
        </div>
        <div class="flex flex-wrap items-center gap-2 ps-4">
          <select
            v-if="editable"
            :value="f.status"
            class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
            @change="(e) => patch(f.name, { status: e.target.value })"
          >
            <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
          </select>
          <span
            v-if="f.target_date"
            class="text-xs text-ink-gray-5 inline-flex items-center gap-1"
          >
            <LucideCalendar class="size-3.5" /> {{ f.target_date }}
          </span>
          <span
            v-if="f.project"
            class="text-xs text-violet-700 bg-violet-100 rounded-full px-2 py-0.5"
          >
            {{ f.project }}
          </span>
        </div>
      </div>
    </div>
    <div v-else-if="!features.loading" class="text-xs text-ink-gray-5">
      {{ __("No features yet.") }}
    </div>

    <form v-if="editable" class="flex items-center gap-2 mt-1" @submit.prevent="add">
      <input
        v-model="newTitle"
        type="text"
        :placeholder="__('Add a feature…')"
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
import { Badge, Button, createResource, toast } from "frappe-ui";
import { __ } from "@/translation";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucideCalendar from "~icons/lucide/calendar";

interface P {
  addonId: string;
  editable?: boolean;
}
const props = withDefaults(defineProps<P>(), { editable: false });
const emit = defineEmits(["changed"]);

const STATUSES = ["Planned", "In Progress", "Released", "Deprecated"];
const newTitle = ref("");

const features = createResource({
  url: "helpdesk.api.addon.get_features",
  makeParams: () => ({ addon: props.addonId }),
  auto: true,
});
watch(() => props.addonId, () => features.reload());

function reload() {
  features.reload();
  emit("changed");
}

function statusTheme(status: string) {
  return (
    {
      Planned: "gray",
      "In Progress": "blue",
      Released: "green",
      Deprecated: "orange",
    }[status] || "gray"
  );
}
function dotClass(status: string) {
  return (
    {
      Planned: "bg-ink-gray-4",
      "In Progress": "bg-blue-500",
      Released: "bg-green-500",
      Deprecated: "bg-amber-500",
    }[status] || "bg-ink-gray-4"
  );
}

const addRes = createResource({
  url: "helpdesk.api.addon.add_feature",
  onSuccess: () => {
    newTitle.value = "";
    reload();
  },
  onError: (e: any) => toast.error(e?.messages?.[0] || __("Could not add feature")),
});
function add() {
  const t = newTitle.value.trim();
  if (!t) return;
  addRes.submit({ addon: props.addonId, feature_title: t });
}

const updateRes = createResource({
  url: "helpdesk.api.addon.update_feature",
  onSuccess: () => reload(),
});
function patch(name: string, fields: Record<string, any>) {
  updateRes.submit({ name, ...fields });
}

const deleteRes = createResource({
  url: "helpdesk.api.addon.delete_feature",
  onSuccess: () => reload(),
});
function remove(name: string) {
  deleteRes.submit({ name });
}
</script>
