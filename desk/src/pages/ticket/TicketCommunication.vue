<template>
  <div
    class="flex-1 px-3 pt-2.5 mb-4 rounded-md shadow text-base leading-6 transition-all duration-300 ease-in-out border-l-4"
    :class="bubbleClass"
  >
    <div class="mb-4 flex items-center justify-between text-base">
      <div class="flex items-center gap-0.5">
        <UserAvatar v-bind="user" size="lg" expand strong :hide-avatar="true" />
        <Badge
          v-if="isSelf"
          class="ms-2"
          theme="gray"
          variant="subtle"
          :label="__('You')"
        />
        <Badge
          v-else-if="!fromCustomer"
          class="ms-2"
          theme="blue"
          variant="subtle"
          :label="__('Support team')"
        />
        <LucideDot class="text-ink-gray-4 size-4" />
        <Tooltip :text="dateFormat(date, dateTooltipFormat)">
          <span class="text-ink-gray-5">
            {{ timeAgo(date) }}
          </span>
        </Tooltip>
      </div>
    </div>

    <EmailContent :content="sanitize(content)" />
    <div class="flex flex-wrap gap-2 mb-2">
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
import { AttachmentItem, UserAvatar } from "@/components";
import { UserInfo } from "@/types";
import { dateFormat, dateTooltipFormat, timeAgo } from "@/utils";
import { __ } from "@/translation";
import { Badge, dayjs, Tooltip } from "frappe-ui";
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

const bubbleClass = computed(() =>
  props.fromCustomer
    ? "bg-surface-white border-outline-gray-2"
    : "bg-surface-blue-1 border-blue-400"
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
