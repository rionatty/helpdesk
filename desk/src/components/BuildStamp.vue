<template>
  <!-- Which build is this, and is the server on the same one? A mismatch
       means a deploy didn't finish (most often: the restart didn't take). -->
  <div
    v-if="isExpanded || outOfSync"
    class="px-2.5 pt-1 text-[10px] leading-tight select-all"
    :class="outOfSync ? 'text-ink-amber-3 font-medium' : 'text-ink-gray-4'"
    :title="title"
  >
    <template v-if="isExpanded">
      <span v-if="!outOfSync">{{ __("Version") }} {{ built }}</span>
      <span v-else>
        {{ __("Out of sync: interface {0}, server {1}", [built, served]) }}
      </span>
    </template>
    <span v-else>!</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { createResource } from "frappe-ui";
import { __ } from "@/translation";

defineProps<{ isExpanded: boolean }>();

declare const __BUILD_COMMIT__: string;
const built =
  typeof __BUILD_COMMIT__ !== "undefined" ? __BUILD_COMMIT__ : "dev";

const info = createResource({
  url: "helpdesk.api.version.get_build_info",
  auto: true,
  // Purely informational: never toast if it fails.
  onError: () => {},
});
const served = computed(() => info.data?.commit || "");

const outOfSync = computed(
  () =>
    !!served.value &&
    served.value !== "unknown" &&
    built !== "dev" &&
    built !== "unknown" &&
    served.value !== built
);

const title = computed(() =>
  outOfSync.value
    ? __(
        "The interface and the server are on different versions. Run scripts/deploy.sh on the server."
      )
    : __("Interface {0} · server {1}", [built, served.value || "…"])
);
</script>
