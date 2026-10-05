import { useStorage } from "@vueuse/core";
import { computed, type Ref } from "vue";

/**
 * Which milestones are folded shut, per project.
 *
 * Module-level, so the milestone list and the timeline fold in step: a
 * milestone closed in one is closed in the other. Stored per browser, so a
 * long plan stays the way its reader left it.
 */
const collapsedByProject = useStorage<Record<string, string[]>>(
  "hd-milestones-collapsed",
  {}
);

/** The timeline's "Not in a milestone" group folds like a milestone does. */
export const NO_MILESTONE = "__none__";

export function useMilestoneCollapse(projectId: Ref<string> | (() => string)) {
  const pid = computed(
    () =>
      (typeof projectId === "function" ? projectId() : projectId.value) || ""
  );
  const collapsed = computed<string[]>(
    () => collapsedByProject.value[pid.value] || []
  );

  function write(names: string[]) {
    // Replace the map so the storage write actually fires.
    collapsedByProject.value = {
      ...collapsedByProject.value,
      [pid.value]: names,
    };
  }

  const isCollapsed = (name: string) => collapsed.value.includes(name);

  function toggle(name: string) {
    write(
      isCollapsed(name)
        ? collapsed.value.filter((n) => n !== name)
        : [...collapsed.value, name]
    );
  }

  /** Fold or unfold every milestone currently on screen. */
  function setAll(names: string[], value: boolean) {
    write(value ? [...new Set(names)] : []);
  }

  return { collapsed, isCollapsed, toggle, setAll };
}
