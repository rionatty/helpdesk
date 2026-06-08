<template>
  <div class="flex flex-col gap-3">
    <div class="text-sm font-semibold text-ink-gray-8">
      {{ __("Discussion") }}
    </div>

    <div v-if="comments.data?.length" class="flex flex-col gap-3">
      <div v-for="c in comments.data" :key="c.name" class="flex gap-2.5">
        <Avatar size="sm" :label="c.author" />
        <div
          class="flex-1 min-w-0 rounded-lg px-3 py-2"
          :class="c.is_agent ? 'bg-violet-50' : 'bg-blue-50'"
        >
          <div class="flex items-center justify-between gap-2">
            <span
              class="text-sm font-semibold"
              :class="c.is_agent ? 'text-violet-800' : 'text-blue-800'"
            >
              {{ c.author }}
              <span
                v-if="c.is_agent"
                class="ms-1 text-xs font-medium text-violet-600"
                >· {{ __("Team") }}</span
              >
            </span>
            <span class="text-xs text-ink-gray-5 shrink-0">
              {{ timeAgo(c.creation) }}
            </span>
          </div>
          <p class="text-sm text-ink-gray-8 whitespace-pre-line mt-0.5">
            {{ c.content }}
          </p>
        </div>
      </div>
    </div>
    <div v-else-if="!comments.loading" class="text-sm text-ink-gray-5">
      {{ __("No comments yet — start the conversation.") }}
    </div>

    <form class="flex items-start gap-2 mt-1" @submit.prevent="post">
      <textarea
        v-model="text"
        rows="2"
        :placeholder="__('Write a comment…')"
        class="flex-1 text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
      />
      <Button
        :label="__('Post')"
        theme="blue"
        variant="solid"
        size="sm"
        :loading="addRes.loading"
        @click="post"
      />
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { Avatar, Button, createResource, toast } from "frappe-ui";
import { timeAgo } from "@/utils";
import { __ } from "@/translation";

interface P {
  projectId: string;
}
const props = defineProps<P>();
const text = ref("");

const comments = createResource({
  url: "helpdesk.api.project.get_project_comments",
  makeParams: () => ({ project: props.projectId }),
  auto: true,
});
watch(
  () => props.projectId,
  () => comments.reload()
);

const addRes = createResource({
  url: "helpdesk.api.project.add_project_comment",
  onSuccess: () => {
    text.value = "";
    comments.reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not post comment")),
});
function post() {
  const t = text.value.trim();
  if (!t) return;
  addRes.submit({ project: props.projectId, content: t });
}
</script>
