<template>
  <Teleport to="#app-header" v-if="showHeader">
    <slot>
      <header
        class="flex h-full w-full items-center justify-between px-4 md:px-6"
      >
        <div class="flex items-center gap-2 min-w-0 flex-1">
          <slot name="left-header" />
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <slot name="right-header" class="flex items-center gap-2" />
        </div>
      </header>
    </slot>
  </Teleport>
</template>
<script setup>
import { nextTick, ref } from "vue";
const showHeader = ref(false);

nextTick(() => {
  showHeader.value = true;
});
</script>
