<template>
  <div
    class="px-4 pt-3 pb-2.5 rounded-2xl border shadow-sm text-base leading-6 transition-all duration-300 ease-in-out"
    :class="bubbleClass"
  >
    <div
      class="mb-2 flex items-center justify-between gap-2"
      :class="fromCustomer ? 'flex-row-reverse' : ''"
    >
      <div
        class="flex items-center gap-1.5 min-w-0"
        :class="fromCustomer ? 'flex-row-reverse' : ''"
      >
        <span class="font-semibold truncate" :class="nameClass">
          {{ user.name }}
        </span>
        <span
          v-if="isSelf"
          class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700"
        >
          {{ __("You") }}
        </span>
        <span
          v-else-if="!fromCustomer"
          class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium bg-violet-100 text-violet-700"
        >
          {{ __("Support team") }}
        </span>
      </div>
      <Tooltip :text="dateFormat(date, dateTooltipFormat)">
        <span class="shrink-0 text-sm text-ink-gray-5">
          {{ timeAgo(date) }}
        </span>
      </Tooltip>
    </div>

    <EmailContent :content="sanitize(content)" />
    <div v-if="attachments.length" class="flex flex-wrap gap-2 mt-2">
      <AttachmentItem
        v-for="a in attachments"
        :key="a.file_url"
        :label="a.file_name"
        :url="a.file_url"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { AttachmentItem } from "@/components";
import { UserInfo } from "@/types";
import { dateFormat, dateTooltipFormat, timeAgo } from "@/utils";
import { __ } from "@/translation";
import { Tooltip } from "frappe-ui";
import sanitizeHtml from "sanitize-html";
import { computed } from "vue";

interface Attachment {
  file_name: string;
  file_url: string;
}

interface P {
  content: string;
  date: string;
  user: UserInfo;
  cc?: string;
  bcc?: string;
  attachments?: Attachment[];
  fromCustomer?: boolean;
  isSelf?: boolean;
}

const props = withDefaults(defineProps<P>(), {
  cc: () => "",
  bcc: () => "",
  attachments: () => [],
  fromCustomer: true,
  isSelf: false,
});

// Customer messages = blue, support messages = violet. The "tail" corner sits
// on the side nearest the avatar (customer right, support left).
const bubbleClass = computed(() =>
  props.fromCustomer
    ? "bg-blue-50 border-blue-200 rounded-br-md"
    : "bg-violet-50 border-violet-200 rounded-bl-md"
);
const nameClass = computed(() =>
  props.fromCustomer ? "text-blue-800" : "text-violet-800"
);

function sanitize(html: string) {
  return sanitizeHtml(html, {
    allowedTags: sanitizeHtml.defaults.allowedTags.concat(["img", "video"]),
    allowedAttributes: {
      a: ["href"],
      video: ["src", "controls"],
      img: ["src", "width", "height"],
      table: ["border", "cellpadding", "cellspacing", "width", "data-type"],
      td: ["colspan", "rowspan", "width", "align", "valign"],
      th: ["colspan", "rowspan", "width", "align", "valign"],
    },
  });
}
</script>
