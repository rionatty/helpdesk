<template>
  <div
    class="relative -all flex py-[7px] mx-2 h-7.5 cursor-pointer items-center rounded-lg ps-2 pe-2 duration-300 ease-in-out"
    :class="{
      'w-auto': isExpanded,
      'w-8': !isExpanded,
      'shadow-sm text-white font-medium': isActive,
      'text-ink-gray-8': !isActive,
      [bgColor]: isActive,
      [hvColor]: !isActive,
      'before:absolute before:start-0 before:top-1.5 before:bottom-1.5 before:w-[3px] before:rounded-full before:bg-[var(--hd-gold)]':
        isActive && isExpanded,
    }"
    @click="handleNavigation"
  >
    <Tooltip :text="__(label)" v-if="!isExpanded">
      <span
        class="shrink-0"
        :class="{
          'text-[var(--hd-gold)]': isActive,
          'text-ink-gray-9': !isActive,
          'icon-emoji': isMobileView,
        }"
      >
        <component :is="icon" class="h-4 w-4" />
      </span>
    </Tooltip>
    <span
      v-else
      class="shrink-0"
      :class="{
        'text-[var(--hd-gold)]': isActive,
        'text-ink-gray-7': !isActive,
        'icon-emoji': isMobileView,
      }"
    >
      <component :is="icon" class="h-4 w-4" />
    </span>

    <div
      class="-all ms-2 flex min-w-0 items-center justify-between text-sm duration-300 ease-in-out w-full"
      :class="{
        'opacity-100': isExpanded,
        'opacity-0': !isExpanded,
        '-z-50': !isExpanded,
      }"
    >
      <Tooltip :text="__(label)" placement="right">
        <span class="truncate"> {{ __(label) }}</span>
      </Tooltip>
      <slot name="right" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useScreenSize } from "@/composables/screen";
import { useRouter } from "vue-router";

interface P {
  icon?: unknown;
  label: string;
  isExpanded?: boolean;
  isActive?: boolean;
  onClick?: () => void;
  to?: string | object;
  bgColor?: string;
  hvColor?: string;
}

const props = withDefaults(defineProps<P>(), {
  isActive: false,
  onClick: () => () => true,
  to: "",
  bgColor: "bg-[var(--hd-navy)]",
  hvColor: "hover:bg-[rgba(14,33,72,0.06)]",
});
const router = useRouter();
const { isMobileView } = useScreenSize();

function handleNavigation() {
  props.onClick();
  if (!props.to) return;
  if (
    props.to === router.currentRoute.value.name &&
    !router.currentRoute.value.query.view
  )
    return;
  if (typeof props.to === "string") {
    router.push({
      name: props.to,
    });
    return;
  }
  router.push(props.to);
}
</script>

<style>
.icon-emoji > div {
  @apply flex items-center justify-center;
}
</style>
