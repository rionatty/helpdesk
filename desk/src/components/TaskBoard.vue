<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-col gap-3">
      <!-- Title + count -->
      <div class="flex items-center gap-2">
        <div
          class="size-7 rounded-lg bg-green-100 text-green-700 flex items-center justify-center"
        >
          <LucideListChecks class="size-4" />
        </div>
        <span class="text-sm font-semibold text-ink-gray-8">
          {{ __("Tasks") }}
        </span>
        <span v-if="tasks.data?.length" class="text-xs text-ink-gray-5">
          <template v-if="anyFilterActive">
            · {{ __("showing {0} of {1}", [filteredTasks.length, tasks.data.length]) }}
          </template>
          <template v-else>· {{ tasks.data.length }}</template>
        </span>
      </div>

      <!-- Hub dashboard -->
      <div
        v-if="hub && tasks.data?.length"
        class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3"
      >
        <div
          v-for="card in dashCards"
          :key="card.label"
          class="relative overflow-hidden rounded-xl border border-outline-gray-1 bg-surface-white px-3.5 py-3 flex flex-col gap-2.5 shadow-sm hover:shadow-md transition-shadow"
        >
          <span class="absolute inset-x-0 top-0 h-1" :class="card.bar" />
          <div
            class="size-7 rounded-lg flex items-center justify-center"
            :class="card.chip"
          >
            <component :is="card.icon" class="size-4" />
          </div>
          <div>
            <div class="text-2xl font-bold leading-none" :class="card.num">
              {{ card.value }}
            </div>
            <div class="text-[11px] font-medium text-ink-gray-5 mt-1">
              {{ card.label }}
            </div>
          </div>
        </div>
      </div>

      <!-- Hub dashboards (each chart has its own filter) -->
      <div v-if="hub && tasks.data?.length" class="flex flex-col gap-3">
        <!-- Activity trend -->
        <div class="rounded-xl border border-outline-gray-1 bg-surface-white p-4 pt-3">
          <div class="flex items-center gap-2 mb-1 flex-wrap">
            <LucideTrendingUp class="size-4 text-blue-600" />
            <span class="text-sm font-semibold text-ink-gray-8">
              {{ __("Task activity") }}
            </span>
            <span class="text-xs text-ink-gray-5">
              {{ __("created vs done · last 10 weeks") }}
            </span>
            <span class="flex-1" />
            <select v-model="trendAssignee" class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[9rem]">
              <option value="">{{ __("All assignees") }}</option>
              <option value="__unassigned__">{{ __("Unassigned") }}</option>
              <option v-for="a in assigneeOptions" :key="a.value" :value="a.value">
                {{ a.label }}
              </option>
            </select>
          </div>
          <ECharts :options="trendOption" class="w-full h-52" />
        </div>

        <!-- Breakdown charts -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <!-- By status -->
          <div class="rounded-xl border border-outline-gray-1 bg-surface-white p-4 pt-3">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <LucidePieChart class="size-4 text-emerald-600" />
              <span class="text-sm font-semibold text-ink-gray-8">
                {{ __("By status") }}
              </span>
              <span class="flex-1" />
              <select v-model="statusProject" class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[9rem]">
                <option value="">{{ __("All projects") }}</option>
                <option
                  v-for="p in projectOptions"
                  :key="p.value"
                  :value="p.value"
                >
                  {{ p.label }}
                </option>
              </select>
            </div>
            <ECharts :options="statusChartOption" class="w-full h-56" />
          </div>

          <!-- By priority -->
          <div class="rounded-xl border border-outline-gray-1 bg-surface-white p-4 pt-3">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <LucideBarChart3 class="size-4 text-amber-600" />
              <span class="text-sm font-semibold text-ink-gray-8">
                {{ __("By priority") }}
              </span>
              <span class="flex-1" />
              <select v-model="prioStatus" class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[9rem]">
                <option value="">{{ __("All statuses") }}</option>
                <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
            <ECharts :options="prioChartOption" class="w-full h-56" />
          </div>

          <!-- Workload by assignee -->
          <div class="rounded-xl border border-outline-gray-1 bg-surface-white p-4 pt-3">
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              <LucideUsers class="size-4 text-indigo-600" />
              <span class="text-sm font-semibold text-ink-gray-8">
                {{ __("Workload") }}
              </span>
              <span class="flex-1" />
              <select v-model="loadStatus" class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[9rem]">
                <option value="open">{{ __("Open") }}</option>
                <option value="done">{{ __("Done") }}</option>
                <option value="all">{{ __("All") }}</option>
              </select>
            </div>
            <ECharts :options="loadChartOption" class="w-full h-56" />
          </div>
        </div>
      </div>

      <!-- Filter & search toolbar -->
      <div
        v-if="tasks.data?.length"
        class="flex flex-wrap items-center gap-2"
      >
        <!-- Search -->
        <div class="relative">
          <LucideSearch
            class="size-3.5 text-ink-gray-4 absolute left-2 top-1/2 -translate-y-1/2 pointer-events-none"
          />
          <input
            v-model="search"
            type="text"
            :placeholder="__('Search tasks…')"
            class="w-40 sm:w-48 text-xs rounded-md border border-outline-gray-2 bg-surface-white ps-7 pe-2 py-1.5 text-ink-gray-8 focus:outline-none focus:border-blue-400"
          />
        </div>
        <!-- Priority -->
        <select
          v-model="priorityFilter"
          class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1.5 text-ink-gray-7 focus:outline-none focus:border-blue-400"
        >
          <option value="">{{ __("All priorities") }}</option>
          <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
        </select>
        <!-- Assignee -->
        <select
          v-if="assigneeOptions.length || hasUnassigned"
          v-model="assigneeFilter"
          class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1.5 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[10rem]"
        >
          <option value="">{{ __("All assignees") }}</option>
          <option v-if="hasUnassigned" value="__unassigned__">
            {{ __("Unassigned") }}
          </option>
          <option v-for="a in assigneeOptions" :key="a.value" :value="a.value">
            {{ a.label }}
          </option>
        </select>
        <!-- Milestone -->
        <select
          v-if="milestoneOptions.length"
          v-model="milestoneFilter"
          class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1.5 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[10rem]"
        >
          <option value="">{{ __("All milestones") }}</option>
          <option v-for="m in milestoneOptions" :key="m.value" :value="m.value">
            {{ m.label }}
          </option>
        </select>
        <!-- Project (hub) -->
        <select
          v-if="hub && projectOptions.length"
          v-model="projectFilter"
          class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1.5 text-ink-gray-7 focus:outline-none focus:border-blue-400 max-w-[11rem]"
        >
          <option value="">{{ __("All projects") }}</option>
          <option v-for="p in projectOptions" :key="p.value" :value="p.value">
            {{ p.label }}
          </option>
        </select>
        <!-- View by (hub) -->
        <select
          v-if="hub"
          v-model="viewBy"
          class="text-xs rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1.5 text-ink-gray-7 focus:outline-none focus:border-blue-400"
          :title="__('Group the board by')"
        >
          <option value="status">{{ __("View by status") }}</option>
          <option value="project">{{ __("View by project") }}</option>
          <option value="assignee">{{ __("View by assignee") }}</option>
        </select>
        <!-- Date range -->
        <div
          class="flex items-center gap-1 rounded-md border border-outline-gray-2 bg-surface-white px-1.5 py-1"
        >
          <select
            v-model="dateField"
            class="text-xs bg-transparent text-ink-gray-6 focus:outline-none"
            :title="__('Filter tasks by this date')"
          >
            <option value="creation">{{ __("Created") }}</option>
            <option value="start_date">{{ __("Start") }}</option>
            <option value="end_date">{{ __("Due") }}</option>
          </select>
          <input
            v-model="fromDate"
            type="date"
            :aria-label="__('From date')"
            class="text-xs bg-transparent text-ink-gray-7 focus:outline-none w-[7.5rem]"
          />
          <span class="text-ink-gray-4 text-xs">–</span>
          <input
            v-model="toDate"
            type="date"
            :aria-label="__('To date')"
            class="text-xs bg-transparent text-ink-gray-7 focus:outline-none w-[7.5rem]"
          />
        </div>
        <!-- My tasks (agent only) -->
        <button
          v-if="editable"
          type="button"
          class="text-xs rounded-md border px-2 py-1.5 inline-flex items-center gap-1 transition-colors"
          :class="
            mineOnly
              ? 'border-blue-300 bg-blue-50 text-blue-700'
              : 'border-outline-gray-2 bg-surface-white text-ink-gray-6 hover:border-outline-gray-3'
          "
          @click="mineOnly = !mineOnly"
        >
          <LucideUser class="size-3" /> {{ __("My tasks") }}
        </button>
        <!-- Overdue -->
        <button
          type="button"
          class="text-xs rounded-md border px-2 py-1.5 inline-flex items-center gap-1 transition-colors"
          :class="
            overdueOnly
              ? 'border-red-300 bg-red-50 text-red-700'
              : 'border-outline-gray-2 bg-surface-white text-ink-gray-6 hover:border-outline-gray-3'
          "
          @click="overdueOnly = !overdueOnly"
        >
          <LucideAlertTriangle class="size-3" /> {{ __("Overdue") }}
        </button>
        <!-- Hide done -->
        <button
          type="button"
          class="text-xs rounded-md border px-2 py-1.5 inline-flex items-center gap-1 transition-colors"
          :class="
            hideDone
              ? 'border-blue-300 bg-blue-50 text-blue-700'
              : 'border-outline-gray-2 bg-surface-white text-ink-gray-6 hover:border-outline-gray-3'
          "
          @click="hideDone = !hideDone"
        >
          <LucideEyeOff class="size-3" /> {{ __("Hide done") }}
        </button>
        <!-- Clear -->
        <button
          v-if="anyFilterActive"
          type="button"
          class="text-xs text-blue-600 hover:text-blue-700 font-medium inline-flex items-center gap-0.5 px-1"
          @click="clearFilters"
        >
          <LucideX class="size-3" /> {{ __("Clear") }}
        </button>
      </div>
    </div>

    <!-- Kanban columns -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3 items-start">
      <div
        v-for="col in boardColumns"
        :key="col.key"
        class="relative overflow-hidden rounded-2xl border p-2.5 pt-3 flex flex-col gap-2 min-h-[120px] max-h-[70vh]"
        :class="[colTheme(col.key).bg, colTheme(col.key).border]"
      >
        <span class="absolute inset-x-0 top-0 h-1" :class="colTheme(col.key).bar" />
        <div class="flex items-center justify-between px-1 shrink-0">
          <div class="flex items-center gap-1.5 text-xs font-semibold min-w-0" :class="colTheme(col.key).text">
            <span class="size-2.5 rounded-full shrink-0 ring-2 ring-inset ring-white/60" :class="col.dot" />
            <span class="truncate">{{ col.label }}</span>
            <span class="shrink-0 text-[10px] font-semibold text-ink-gray-6 bg-surface-white rounded-full px-1.5 py-0.5 min-w-[1.25rem] text-center">
              {{ (grouped[col.key] || []).length }}
            </span>
          </div>
          <button
            v-if="editable && col.addable"
            type="button"
            class="text-ink-gray-5 hover:text-ink-gray-9 hover:bg-surface-white rounded-md p-0.5 transition-colors shrink-0"
            :aria-label="__('Add task')"
            @click="quickAdd(col.key)"
          >
            <LucidePlus class="size-3.5" />
          </button>
        </div>

        <!-- Scrollable card stack: the column stays a fixed height no matter
             how many tasks land in it; cards scroll within the column. -->
        <div class="flex flex-col gap-2 overflow-y-auto grow -me-1 pe-1">
        <button
          v-for="t in grouped[col.key]"
          :key="t.name"
          type="button"
          class="text-start rounded-xl border border-outline-gray-2 bg-surface-white px-3 py-2.5 flex flex-col gap-2 hover:shadow-md hover:border-outline-gray-3 hover:-translate-y-0.5 transition-all duration-150"
          @click="open(t)"
        >
          <div class="text-sm font-medium text-ink-gray-8 leading-snug">
            {{ t.subject }}
          </div>
          <div class="flex flex-wrap items-center gap-1.5">
            <span
              class="text-[10px] font-medium rounded-full px-1.5 py-0.5"
              :class="priorityClass(t.priority)"
            >
              {{ t.priority }}
            </span>
            <span
              v-if="t.end_date"
              class="text-[10px] rounded-full px-1.5 py-0.5 inline-flex items-center gap-0.5"
              :class="
                isOverdue(t)
                  ? 'bg-red-100 text-red-700'
                  : 'bg-surface-gray-2 text-ink-gray-6'
              "
            >
              <LucideCalendar class="size-3" /> {{ t.end_date }}
            </span>
            <span
              v-if="t.comment_count"
              class="text-[10px] rounded-full px-1.5 py-0.5 bg-surface-gray-2 text-ink-gray-6 inline-flex items-center gap-0.5"
            >
              <LucideMessageCircle class="size-3" /> {{ t.comment_count }}
            </span>
            <span
              v-if="Number(t.score)"
              class="text-[10px] rounded-full px-1.5 py-0.5 bg-amber-100 text-amber-700 inline-flex items-center gap-0.5"
              :title="__('Review score')"
            >
              <LucideStar class="size-3 fill-amber-500 text-amber-500" /> {{ t.score }}/5
            </span>
            <span
              v-if="t.milestone && milestoneTitle(t.milestone)"
              class="text-[10px] rounded-full px-1.5 py-0.5 bg-violet-100 text-violet-700 inline-flex items-center gap-0.5"
            >
              <LucideFlag class="size-3" /> {{ milestoneTitle(t.milestone) }}
            </span>
            <!-- Hub: status pill + parent (project / add-on / Personal) -->
            <span
              v-if="hub"
              class="text-[10px] rounded-full px-1.5 py-0.5"
              :class="statusChipClass(t.status)"
            >
              {{ t.status }}
            </span>
            <span
              v-if="hub && t.parent_label"
              class="text-[10px] rounded-full px-1.5 py-0.5 bg-indigo-100 text-indigo-700 inline-flex items-center gap-0.5"
            >
              <LucideFolder class="size-3" /> {{ t.parent_label }}
            </span>
            <span
              v-if="t.is_internal && editable"
              class="text-[10px] rounded-full px-1.5 py-0.5 bg-surface-gray-2 text-ink-gray-6 inline-flex items-center gap-0.5"
              :title="__('Hidden from the customer portal')"
            >
              <LucideEyeOff class="size-3" /> {{ __("Internal") }}
            </span>
          </div>
          <div
            v-if="t.assigned_to_name"
            class="flex items-center gap-1.5 text-[11px] text-ink-gray-5"
          >
            <Avatar size="xs" :label="t.assigned_to_name" />
            {{ t.assigned_to_name }}
          </div>
        </button>

        <div
          v-if="!grouped[col.key].length"
          class="flex flex-col items-center justify-center gap-1 text-[11px] text-ink-gray-4 py-6"
        >
          <LucideListChecks class="size-4 text-ink-gray-3" />
          {{ __("Nothing here") }}
        </div>
        </div>
      </div>
    </div>

    <!-- Add task (agent) -->
    <form
      v-if="editable"
      class="flex items-center gap-2 mt-1 rounded-xl border border-outline-gray-2 bg-surface-white p-1.5 pl-3 focus-within:border-blue-400 transition-colors"
      @submit.prevent="add"
    >
      <LucidePlus class="size-4 text-ink-gray-4 shrink-0" />
      <input
        v-model="newSubject"
        type="text"
        :placeholder="hub ? __('Add a personal task…') : __('Add a task…')"
        class="flex-1 text-sm bg-transparent text-ink-gray-8 focus:outline-none"
      />
      <Button
        :label="__('Add')"
        theme="blue"
        variant="solid"
        size="sm"
        :loading="addRes.loading"
        @click="add"
      />
    </form>

    <!-- Task detail dialog -->
    <Dialog v-model="showDetail" :options="{ size: '2xl' }">
      <template #body>
        <div v-if="selected" class="flex flex-col">
          <!-- Header: title + save state + actions -->
          <div
            class="flex items-start gap-3 px-5 pt-5 pb-3 border-b border-outline-gray-1"
          >
            <input
              v-if="editable"
              ref="subjectInput"
              :value="selected.subject"
              :placeholder="__('Task name')"
              class="flex-1 min-w-0 text-lg font-semibold text-ink-gray-9 bg-transparent focus:outline-none border-b border-transparent focus:border-outline-gray-2"
              @change="(e) => patch({ subject: e.target.value })"
              @keydown.enter="(e) => e.target.blur()"
            />
            <h2 v-else class="flex-1 min-w-0 text-lg font-semibold text-ink-gray-9">
              {{ selected.subject }}
            </h2>
            <div class="flex items-center gap-2 shrink-0">
              <span
                v-if="editable"
                class="text-xs flex items-center gap-1"
                :class="updateRes.loading ? 'text-ink-gray-5' : 'text-green-600'"
              >
                <LucideLoader2
                  v-if="updateRes.loading"
                  class="size-3 animate-spin"
                />
                <LucideCheck v-else class="size-3" />
                {{ updateRes.loading ? __("Saving…") : __("Saved") }}
              </span>
              <button
                v-if="editable"
                type="button"
                class="text-ink-gray-4 hover:text-ink-red-3"
                :aria-label="__('Delete task')"
                @click="remove"
              >
                <LucideTrash2 class="size-4" />
              </button>
              <Button
                :label="__('Done')"
                theme="gray"
                variant="solid"
                @click="showDetail = false"
              />
            </div>
          </div>

          <div class="p-5 flex flex-col gap-4">

          <!-- Fields -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Status") }}</span>
              <select
                v-if="editable"
                :value="selected.status"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ status: e.target.value })"
              >
                <option v-for="s in STATUSES" :key="s" :value="s">{{ s }}</option>
              </select>
              <span v-else class="text-sm text-ink-gray-8">{{ selected.status }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Priority") }}</span>
              <select
                v-if="editable"
                :value="selected.priority"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ priority: e.target.value })"
              >
                <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
              </select>
              <span v-else class="text-sm text-ink-gray-8">{{ selected.priority }}</span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Start") }}</span>
              <input
                v-if="editable"
                type="date"
                :value="selected.start_date || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ start_date: e.target.value })"
              />
              <span v-else class="text-sm text-ink-gray-8">
                {{ selected.start_date || "—" }}
              </span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Due") }}</span>
              <input
                v-if="editable"
                type="date"
                :value="selected.end_date || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ end_date: e.target.value })"
              />
              <span v-else class="text-sm text-ink-gray-8">
                {{ selected.end_date || "—" }}
              </span>
            </div>
          </div>

          <!-- Placement: milestone / feature -->
          <div
            v-if="milestoneOptions.length || featureOptions.length"
            class="grid grid-cols-2 gap-3"
          >
            <div v-if="milestoneOptions.length" class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Milestone") }}</span>
              <select
                v-if="editable"
                :value="selected.milestone || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ milestone: e.target.value })"
              >
                <option value="">{{ __("No milestone") }}</option>
                <option v-for="m in milestoneOptions" :key="m.value" :value="m.value">
                  {{ m.label }}
                </option>
              </select>
              <span v-else class="text-sm text-ink-gray-8">
                {{ milestoneTitle(selected.milestone) || "—" }}
              </span>
            </div>
            <div v-if="featureOptions.length" class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Feature") }}</span>
              <select
                v-if="editable"
                :value="selected.feature || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ feature: e.target.value })"
              >
                <option value="">{{ __("No feature") }}</option>
                <option v-for="f in featureOptions" :key="f.value" :value="f.value">
                  {{ f.label }}
                </option>
              </select>
              <span v-else class="text-sm text-ink-gray-8">
                {{ featureTitle(selected.feature) || "—" }}
              </span>
            </div>
          </div>

          <!-- Internal toggle (agent; not for standalone/hub personal tasks) -->
          <label
            v-if="editable && !standalone && !hub"
            class="flex items-center gap-2 text-sm text-ink-gray-7 cursor-pointer"
          >
            <input
              type="checkbox"
              :checked="!!selected.is_internal"
              @change="(e) => patch({ is_internal: e.target.checked ? 1 : 0 })"
            />
            {{ __("Internal only — hidden from the customer portal") }}
          </label>

          <!-- Assignee + Reviewer (agent) -->
          <div v-if="editable" class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Assignee") }}</span>
              <select
                v-if="canAssignOthers"
                :value="selected.assigned_to || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ assigned_to: e.target.value })"
              >
                <option value="">{{ __("Unassigned") }}</option>
                <option v-for="a in agentOptions" :key="a.value" :value="a.value">
                  {{ a.label }}
                </option>
              </select>
              <!-- Hub non-managers can only self-assign — show it read-only. -->
              <span v-else class="text-sm text-ink-gray-8 py-1">
                {{ selected.assigned_to_name || __("You") }}
              </span>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-ink-gray-5">{{ __("Reviewer") }}</span>
              <select
                :value="selected.reviewer || ''"
                class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-2 py-1 text-ink-gray-7 focus:outline-none focus:border-blue-400"
                @change="(e) => patch({ reviewer: e.target.value })"
              >
                <option value="">{{ __("No reviewer") }}</option>
                <option v-for="a in agentOptions" :key="a.value" :value="a.value">
                  {{ a.label }}
                </option>
              </select>
            </div>
          </div>
          <div
            v-else-if="selected.assigned_to_name"
            class="flex items-center gap-2 text-sm text-ink-gray-7"
          >
            <Avatar size="sm" :label="selected.assigned_to_name" />
            {{ selected.assigned_to_name }}
          </div>

          <!-- Review score (agent) -->
          <div v-if="editable" class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">
              {{ __("Score") }}
              <template v-if="!canScore">
                ·
                {{
                  selected.reviewer
                    ? __("only the reviewer can score")
                    : __("set a reviewer to enable scoring")
                }}
              </template>
            </span>
            <div class="flex items-center gap-0.5">
              <button
                v-for="n in 5"
                :key="n"
                type="button"
                :disabled="!canScore"
                :class="canScore ? 'cursor-pointer hover:scale-110 transition-transform' : 'cursor-default'"
                :aria-label="__('Score {0} of 5', [n])"
                @click="canScore && patch({ score: n === Number(selected.score) ? 0 : n })"
              >
                <LucideStar
                  class="size-5"
                  :class="
                    n <= (Number(selected.score) || 0)
                      ? 'text-amber-400 fill-amber-400'
                      : 'text-ink-gray-3'
                  "
                />
              </button>
              <span v-if="Number(selected.score)" class="text-xs text-ink-gray-5 ms-1.5">
                {{ selected.score }}/5
              </span>
            </div>
          </div>

          <!-- Description -->
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-5">{{ __("Description") }}</span>
            <textarea
              v-if="editable"
              :value="selected.description || ''"
              rows="2"
              class="text-sm rounded-md border border-outline-gray-2 bg-surface-white px-3 py-2 text-ink-gray-8 focus:outline-none focus:border-blue-400 resize-none"
              @change="(e) => patch({ description: e.target.value })"
            />
            <p v-else class="text-sm text-ink-gray-8 whitespace-pre-line">
              {{ selected.description || __("No description.") }}
            </p>
          </div>

          <!-- Subtasks (agents only) -->
          <div
            v-if="editable && selected.name"
            class="border-t border-outline-gray-1 pt-3"
          >
            <TaskSubtasks :task-id="selected.name" :editable="editable" />
          </div>

          <!-- Attachments -->
          <div class="border-t border-outline-gray-1 pt-3">
            <DocAttachments
              doctype="HD Addon Task"
              :docname="selected.name"
              :editable="editable"
            />
          </div>

          <!-- Comments -->
          <div class="border-t border-outline-gray-1 pt-3 flex flex-col gap-3">
            <div class="text-sm font-semibold text-ink-gray-8">
              {{ __("Comments") }}
            </div>
            <div
              v-if="comments.data?.length"
              class="flex flex-col gap-3 max-h-60 overflow-y-auto"
            >
              <div v-for="c in comments.data" :key="c.name" class="flex gap-2.5">
                <Avatar size="sm" :label="c.author" class="mt-0.5 shrink-0" />
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-ink-gray-8">
                      {{ c.author }}
                    </span>
                    <span class="text-xs text-ink-gray-4">
                      {{ timeAgo(c.creation) }}
                    </span>
                  </div>
                  <p class="text-sm text-ink-gray-7 whitespace-pre-line">
                    {{ c.content }}
                  </p>
                </div>
              </div>
            </div>
            <p v-else-if="!comments.loading" class="text-sm text-ink-gray-5">
              {{ __("No comments yet.") }}
            </p>
            <form class="flex items-center gap-2" @submit.prevent="addComment">
              <input
                v-model="newComment"
                type="text"
                :placeholder="__('Write a comment…')"
                class="flex-1 text-sm rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-1.5 text-ink-gray-8 focus:outline-none focus:border-blue-400"
              />
              <Button
                :label="__('Send')"
                theme="blue"
                variant="solid"
                size="sm"
                :loading="addCommentRes.loading"
                @click="addComment"
              />
            </form>
          </div>

          <!-- Activity / audit trail (agents only) -->
          <div
            v-if="editable && selected.name"
            class="border-t border-outline-gray-1 pt-3 flex flex-col gap-2.5"
          >
            <div class="flex items-center gap-2">
              <LucideHistory class="size-4 text-ink-gray-6" />
              <span class="text-sm font-semibold text-ink-gray-8">
                {{ __("Activity") }}
              </span>
            </div>
            <div
              v-if="activity.data?.length"
              class="flex flex-col gap-3 max-h-60 overflow-y-auto ps-1"
            >
              <div
                v-for="(a, idx) in activity.data"
                :key="idx"
                class="flex gap-2.5"
              >
                <span class="mt-1.5 size-1.5 rounded-full bg-ink-gray-4 shrink-0" />
                <div class="min-w-0 text-xs">
                  <div class="flex items-center gap-1.5">
                    <span class="font-medium text-ink-gray-8">{{ a.author }}</span>
                    <span
                      v-if="!a.is_agent"
                      class="text-[9px] font-semibold uppercase tracking-wide text-amber-700 bg-amber-100 rounded px-1"
                    >
                      {{ __("Customer") }}
                    </span>
                    <span class="text-ink-gray-4">{{ timeAgo(a.creation) }}</span>
                  </div>
                  <div v-if="a.action === 'created'" class="text-ink-gray-6 mt-0.5">
                    {{ __("created this task") }}
                  </div>
                  <ul v-else class="mt-0.5 flex flex-col gap-0.5">
                    <li v-for="(c, i) in a.changes" :key="i" class="text-ink-gray-6">
                      <span class="font-medium text-ink-gray-7">{{ c.field }}</span>:
                      <span class="text-ink-gray-5 line-through">{{ c.from }}</span>
                      <span class="text-ink-gray-4"> → </span>
                      <span class="text-ink-gray-8">{{ c.to }}</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            <p v-else-if="!activity.loading" class="text-xs text-ink-gray-4">
              {{ __("No changes recorded yet.") }}
            </p>
          </div>
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import {
  Avatar,
  Button,
  Dialog,
  ECharts,
  createListResource,
  createResource,
  dayjs,
  toast,
} from "frappe-ui";
import DocAttachments from "@/components/DocAttachments.vue";
import TaskSubtasks from "@/components/TaskSubtasks.vue";
import { timeAgo, dataTheme } from "@/utils";
import { __ } from "@/translation";
import { useAuthStore } from "@/stores/auth";
import { globalStore } from "@/stores/globalStore";
import LucidePlus from "~icons/lucide/plus";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucideCalendar from "~icons/lucide/calendar";
import LucideMessageCircle from "~icons/lucide/message-circle";
import LucideTrendingUp from "~icons/lucide/trending-up";
import LucideHistory from "~icons/lucide/history";
import LucidePieChart from "~icons/lucide/pie-chart";
import LucideBarChart3 from "~icons/lucide/bar-chart-3";
import LucideUsers from "~icons/lucide/users";
import LucideFlag from "~icons/lucide/flag";
import LucideEyeOff from "~icons/lucide/eye-off";
import LucideListChecks from "~icons/lucide/list-checks";
import LucideCheck from "~icons/lucide/check";
import LucideLoader2 from "~icons/lucide/loader-2";
import LucideSearch from "~icons/lucide/search";
import LucideUser from "~icons/lucide/user";
import LucideStar from "~icons/lucide/star";
import LucideFolder from "~icons/lucide/folder";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideCircleDot from "~icons/lucide/circle-dot";
import LucideCircleCheck from "~icons/lucide/circle-check";
import LucideCirclePause from "~icons/lucide/circle-pause";
import LucideClock from "~icons/lucide/clock";
import LucideX from "~icons/lucide/x";

interface P {
  addonId?: string;
  projectId?: string;
  /** No parent — the independent Tasks workspace (single project/add-on board). */
  standalone?: boolean;
  /** The Tasks hub: every task the user can see, across projects/add-ons. */
  hub?: boolean;
  editable?: boolean;
}
const props = withDefaults(defineProps<P>(), {
  addonId: "",
  projectId: "",
  standalone: false,
  hub: false,
  editable: false,
});
const emit = defineEmits(["changed"]);

const authStore = useAuthStore();
const { $dialog } = globalStore();
const { userId } = authStore;
const isManager = computed(() => !!authStore.isManager);
// In the hub, only managers may assign work to other agents.
const canAssignOthers = computed(() => !props.hub || isManager.value);

const STATUSES = ["To Do", "In Progress", "Pending", "Postponed", "Done"];
const PRIORITIES = ["Low", "Medium", "High", "Urgent"];
const COLUMNS = [
  { key: "To Do", dot: "bg-ink-gray-4" },
  { key: "In Progress", dot: "bg-blue-500" },
  { key: "Pending", dot: "bg-amber-500" },
  { key: "Postponed", dot: "bg-violet-500" },
  { key: "Done", dot: "bg-green-500" },
];
// Per-status column colour (tint bg + accent bar + label). Falls back to a
// neutral slate for the dynamic project/assignee columns.
const NEUTRAL_THEME = {
  bg: "bg-surface-gray-1",
  border: "border-outline-gray-1",
  bar: "bg-ink-gray-3",
  text: "text-ink-gray-7",
};
const COLUMN_THEME: Record<string, typeof NEUTRAL_THEME> = {
  "To Do": NEUTRAL_THEME,
  "In Progress": {
    bg: "bg-blue-50",
    border: "border-blue-100",
    bar: "bg-blue-400",
    text: "text-blue-700",
  },
  Pending: {
    bg: "bg-amber-50",
    border: "border-amber-100",
    bar: "bg-amber-400",
    text: "text-amber-700",
  },
  Postponed: {
    bg: "bg-violet-50",
    border: "border-violet-100",
    bar: "bg-violet-400",
    text: "text-violet-700",
  },
  Done: {
    bg: "bg-green-50",
    border: "border-green-100",
    bar: "bg-green-400",
    text: "text-green-700",
  },
};
function colTheme(key: string) {
  return COLUMN_THEME[key] || NEUTRAL_THEME;
}

const parentParams = () =>
  props.standalone || props.hub
    ? {}
    : props.addonId
    ? { addon: props.addonId }
    : { project: props.projectId };

const tasks = createResource({
  url: props.hub ? "helpdesk.api.task.get_my_tasks" : "helpdesk.api.addon.get_tasks",
  makeParams: () => (props.hub ? {} : parentParams()),
  auto: true,
});
watch(
  () => [props.addonId, props.projectId],
  () => {
    tasks.reload();
    if (props.projectId) milestonesRes.reload();
    if (props.addonId) featuresRes.reload();
  }
);

// --- filters ---
const search = ref("");
const priorityFilter = ref("");
const assigneeFilter = ref(""); // "" all · "__unassigned__" · else assigned_to value
const milestoneFilter = ref("");
const projectFilter = ref(""); // hub only: "" all · "__standalone__" · parent_name
const viewBy = ref("status"); // hub only: status | project | assignee
const dateField = ref("creation"); // creation | start_date | end_date
const fromDate = ref("");
const toDate = ref("");
const overdueOnly = ref(false);
const hideDone = ref(false);
const mineOnly = ref(false);

// Hub: distinct parents (projects / add-ons / Personal) for the project filter.
const projectOptions = computed(() => {
  const map = new Map<string, string>();
  (tasks.data || []).forEach((t: any) => {
    const key = t.parent_name || "__standalone__";
    if (!map.has(key)) map.set(key, t.parent_label || __("Personal"));
  });
  return Array.from(map, ([value, label]) => ({ value, label }));
});

// Hub dashboard — computed from the full visible scope (before board filters).
const dash = computed(() => {
  const all = tasks.data || [];
  const by = (s: string) => all.filter((t: any) => t.status === s).length;
  return {
    total: all.length,
    todo: by("To Do"),
    inProgress: by("In Progress"),
    done: by("Done"),
    pending: by("Pending"),
    postponed: by("Postponed"),
    overdue: all.filter((t: any) => isOverdue(t)).length,
  };
});
const dashCards = computed(() => [
  { label: __("Total"), value: dash.value.total, icon: LucideListChecks,
    chip: "bg-ink-gray-2 text-ink-gray-7", num: "text-ink-gray-9", bar: "bg-ink-gray-4" },
  { label: __("To Do"), value: dash.value.todo, icon: LucideCircleDot,
    chip: "bg-surface-gray-3 text-ink-gray-6", num: "text-ink-gray-8", bar: "bg-ink-gray-4" },
  { label: __("In Progress"), value: dash.value.inProgress, icon: LucideLoader2,
    chip: "bg-blue-100 text-blue-600", num: "text-blue-600", bar: "bg-blue-500" },
  { label: __("Pending"), value: dash.value.pending, icon: LucideCirclePause,
    chip: "bg-amber-100 text-amber-600", num: "text-amber-600", bar: "bg-amber-500" },
  { label: __("Postponed"), value: dash.value.postponed, icon: LucideClock,
    chip: "bg-violet-100 text-violet-600", num: "text-violet-600", bar: "bg-violet-500" },
  { label: __("Done"), value: dash.value.done, icon: LucideCircleCheck,
    chip: "bg-green-100 text-green-600", num: "text-green-600", bar: "bg-green-500" },
  { label: __("Overdue"), value: dash.value.overdue, icon: LucideAlertTriangle,
    chip: "bg-red-100 text-red-600", num: "text-red-600", bar: "bg-red-500" },
]);

// Per-chart filters — independent of the board filters below.
const trendAssignee = ref(""); // "" all · "__unassigned__" · assigned_to
const statusProject = ref(""); // "" all · parent_name · "__standalone__"
const prioStatus = ref(""); // "" all · status
const loadStatus = ref("open"); // all | open | done

const cssVar = (name: string) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const hubTasks = computed<any[]>(() => tasks.data || []);
const parentKeyOf = (t: any) => t.parent_name || "__standalone__";

// Weekly trend for the hub dashboard: tasks created vs done over 10 weeks.
const trendWeeks = computed(() => {
  const arr: ReturnType<typeof dayjs>[] = [];
  const start = dayjs().startOf("week");
  for (let i = 9; i >= 0; i--) arr.push(start.subtract(i, "week"));
  return arr;
});
const trendOption = computed(() => {
  void dataTheme.value;
  const ws = trendWeeks.value;
  const all = hubTasks.value.filter(
    (t: any) =>
      !trendAssignee.value ||
      (trendAssignee.value === "__unassigned__"
        ? !t.assigned_to
        : t.assigned_to === trendAssignee.value)
  );
  const labels = ws.map((w) => w.format("MMM D"));
  const inWeek = (w: any, extra?: (t: any) => boolean) =>
    all.filter(
      (t: any) =>
        t.creation &&
        dayjs(t.creation).isSame(w, "week") &&
        (!extra || extra(t))
    ).length;
  const created = ws.map((w) => inWeek(w));
  const done = ws.map((w) => inWeek(w, (t) => t.status === "Done"));
  return {
    grid: { left: 34, right: 14, top: 30, bottom: 24 },
    legend: {
      data: [__("Created"), __("Done")],
      right: 0,
      top: 0,
      icon: "roundRect",
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: cssVar("--ink-gray-6") },
    },
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: false,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: cssVar("--outline-gray-2") } },
      axisLabel: { color: cssVar("--ink-gray-6"), fontSize: 10 },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: cssVar("--ink-gray-5") },
      splitLine: { lineStyle: { color: cssVar("--outline-gray-1") } },
    },
    tooltip: { trigger: "axis" },
    series: [
      {
        name: __("Created"),
        type: "line",
        data: created,
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        lineStyle: { width: 2.5, color: "#3b82f6" },
        itemStyle: { color: "#3b82f6" },
        areaStyle: {
          color: {
            type: "linear", x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(59,130,246,0.28)" },
              { offset: 1, color: "rgba(59,130,246,0)" },
            ],
          },
        },
      },
      {
        name: __("Done"),
        type: "line",
        data: done,
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        lineStyle: { width: 2.5, color: "#10b981" },
        itemStyle: { color: "#10b981" },
      },
    ],
  };
});

// --- Status breakdown (donut), filterable by project/parent ---
const STATUS_COLORS: Record<string, string> = {
  "To Do": "#94a3b8",
  "In Progress": "#3b82f6",
  Pending: "#f59e0b",
  Postponed: "#8b5cf6",
  Done: "#10b981",
};
const statusChartOption = computed(() => {
  void dataTheme.value;
  const base = hubTasks.value.filter(
    (t: any) => !statusProject.value || parentKeyOf(t) === statusProject.value
  );
  const data = ["To Do", "In Progress", "Pending", "Postponed", "Done"]
    .map((s) => ({
      name: s,
      value: base.filter((t: any) => t.status === s).length,
      itemStyle: { color: STATUS_COLORS[s] },
    }))
    .filter((d) => d.value > 0);
  return {
    tooltip: { trigger: "item" },
    legend: {
      bottom: 0,
      icon: "circle",
      itemWidth: 9,
      itemHeight: 9,
      textStyle: { color: cssVar("--ink-gray-6"), fontSize: 11 },
    },
    series: [
      {
        type: "pie",
        radius: ["48%", "72%"],
        center: ["50%", "42%"],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: cssVar("--surface-white"), borderWidth: 2 },
        label: { show: false },
        data,
      },
    ],
  };
});

// --- Priority breakdown (bar), filterable by status ---
const PRIORITY_COLORS: Record<string, string> = {
  Urgent: "#ef4444",
  High: "#f59e0b",
  Medium: "#3b82f6",
  Low: "#94a3b8",
};
const prioChartOption = computed(() => {
  void dataTheme.value;
  const base = hubTasks.value.filter(
    (t: any) => !prioStatus.value || t.status === prioStatus.value
  );
  const order = ["Urgent", "High", "Medium", "Low"];
  return {
    grid: { left: 58, right: 16, top: 10, bottom: 20 },
    xAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: cssVar("--ink-gray-5") },
      splitLine: { lineStyle: { color: cssVar("--outline-gray-1") } },
    },
    yAxis: {
      type: "category",
      data: order,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: cssVar("--outline-gray-2") } },
      axisLabel: { color: cssVar("--ink-gray-6") },
    },
    tooltip: { trigger: "axis" },
    series: [
      {
        type: "bar",
        barWidth: "55%",
        itemStyle: { borderRadius: [0, 4, 4, 0] },
        data: order.map((p) => ({
          value: base.filter((t: any) => (t.priority || "Medium") === p).length,
          itemStyle: { color: PRIORITY_COLORS[p] },
        })),
      },
    ],
  };
});

// --- Workload by assignee (top 8 bar), filterable by open/done ---
const loadChartOption = computed(() => {
  void dataTheme.value;
  let base = hubTasks.value;
  if (loadStatus.value === "open") base = base.filter((t: any) => t.status !== "Done");
  else if (loadStatus.value === "done") base = base.filter((t: any) => t.status === "Done");
  const map = new Map<string, number>();
  base.forEach((t: any) => {
    const k = t.assigned_to_name || __("Unassigned");
    map.set(k, (map.get(k) || 0) + 1);
  });
  const arr = Array.from(map, ([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
    .reverse();
  return {
    grid: { left: 96, right: 16, top: 10, bottom: 20 },
    xAxis: {
      type: "value",
      minInterval: 1,
      axisLabel: { color: cssVar("--ink-gray-5") },
      splitLine: { lineStyle: { color: cssVar("--outline-gray-1") } },
    },
    yAxis: {
      type: "category",
      data: arr.map((a) => a.name),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: cssVar("--outline-gray-2") } },
      axisLabel: { color: cssVar("--ink-gray-6"), fontSize: 11 },
    },
    tooltip: { trigger: "axis" },
    series: [
      {
        type: "bar",
        barWidth: "55%",
        itemStyle: { color: "#6366f1", borderRadius: [0, 4, 4, 0] },
        data: arr.map((a) => a.value),
      },
    ],
  };
});

// Assignee options are derived from the tasks themselves, so the filter works
// on the customer portal too (where the agent list isn't loaded).
const assigneeOptions = computed(() => {
  const map = new Map<string, string>();
  (tasks.data || []).forEach((t: any) => {
    if (t.assigned_to) map.set(t.assigned_to, t.assigned_to_name || t.assigned_to);
  });
  return Array.from(map, ([value, label]) => ({ value, label }));
});
const hasUnassigned = computed(() =>
  (tasks.data || []).some((t: any) => !t.assigned_to)
);

const filteredTasks = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (tasks.data || []).filter((t: any) => {
    if (milestoneFilter.value && t.milestone !== milestoneFilter.value) return false;
    if (
      projectFilter.value &&
      (t.parent_name || "__standalone__") !== projectFilter.value
    )
      return false;
    if (priorityFilter.value && t.priority !== priorityFilter.value) return false;
    if (assigneeFilter.value === "__unassigned__" && t.assigned_to) return false;
    if (
      assigneeFilter.value &&
      assigneeFilter.value !== "__unassigned__" &&
      t.assigned_to !== assigneeFilter.value
    )
      return false;
    if (mineOnly.value && t.assigned_to !== userId) return false;
    if (fromDate.value || toDate.value) {
      const val = t[dateField.value];
      if (!val) return false; // no date on this field → excluded from a range
      const d = dayjs(val);
      if (fromDate.value && d.isBefore(dayjs(fromDate.value), "day")) return false;
      if (toDate.value && d.isAfter(dayjs(toDate.value), "day")) return false;
    }
    if (overdueOnly.value && !isOverdue(t)) return false;
    if (hideDone.value && t.status === "Done") return false;
    if (q && !(t.subject || "").toLowerCase().includes(q)) return false;
    return true;
  });
});

const anyFilterActive = computed(
  () =>
    !!search.value ||
    !!priorityFilter.value ||
    !!assigneeFilter.value ||
    !!milestoneFilter.value ||
    !!projectFilter.value ||
    !!fromDate.value ||
    !!toDate.value ||
    overdueOnly.value ||
    hideDone.value ||
    mineOnly.value
);
function clearFilters() {
  search.value = "";
  priorityFilter.value = "";
  assigneeFilter.value = "";
  milestoneFilter.value = "";
  projectFilter.value = "";
  fromDate.value = "";
  toDate.value = "";
  overdueOnly.value = false;
  hideDone.value = false;
  mineOnly.value = false;
}

// Board columns depend on "view by" (hub only; the project/add-on board is
// always grouped by status).
const boardColumns = computed(() => {
  if (!props.hub || viewBy.value === "status") {
    return COLUMNS.map((c) => ({
      key: c.key,
      label: c.key,
      dot: c.dot,
      addable: true,
    }));
  }
  const map = new Map<string, string>();
  if (viewBy.value === "project") {
    filteredTasks.value.forEach((t: any) => {
      const key = t.parent_name || "__standalone__";
      if (!map.has(key)) map.set(key, t.parent_label || __("Personal"));
    });
    return Array.from(map, ([key, label]) => ({
      key,
      label,
      dot: "bg-violet-500",
      addable: false,
    }));
  }
  // assignee
  filteredTasks.value.forEach((t: any) => {
    const key = t.assigned_to || "__unassigned__";
    if (!map.has(key)) map.set(key, t.assigned_to_name || __("Unassigned"));
  });
  return Array.from(map, ([key, label]) => ({
    key,
    label,
    dot: "bg-blue-500",
    addable: false,
  }));
});

function columnKey(t: any): string {
  if (!props.hub || viewBy.value === "status") return t.status || "To Do";
  if (viewBy.value === "project") return t.parent_name || "__standalone__";
  return t.assigned_to || "__unassigned__";
}

const grouped = computed(() => {
  const g: Record<string, any[]> = {};
  boardColumns.value.forEach((c) => (g[c.key] = []));
  filteredTasks.value.forEach((t: any) => {
    const key = columnKey(t);
    (g[key] || (g[key] = [])).push(t);
  });
  return g;
});

function statusChipClass(status: string) {
  return (
    {
      "To Do": "bg-surface-gray-2 text-ink-gray-6",
      "In Progress": "bg-blue-50 text-blue-700",
      Pending: "bg-amber-50 text-amber-700",
      Postponed: "bg-violet-50 text-violet-700",
      Done: "bg-green-50 text-green-700",
    }[status] || "bg-surface-gray-2 text-ink-gray-6"
  );
}

// --- milestone / feature context for placement + chips ---
const milestonesRes = createResource({
  url: "helpdesk.api.project.get_milestones",
  makeParams: () => ({ project: props.projectId }),
  auto: !!props.projectId,
});
const featuresRes = createResource({
  url: "helpdesk.api.addon.get_features",
  makeParams: () => ({ addon: props.addonId }),
  auto: !!props.addonId,
});
const milestoneOptions = computed(() =>
  (milestonesRes.data || []).map((m: any) => ({ value: m.name, label: m.title }))
);
const featureOptions = computed(() =>
  (featuresRes.data || []).map((f: any) => ({
    value: f.name,
    label: f.feature_title,
  }))
);
function milestoneTitle(name: string) {
  return (milestonesRes.data || []).find((m: any) => m.name === name)?.title;
}
defineExpose({
  refreshMilestones: () => props.projectId && milestonesRes.reload(),
  reload: () => {
    tasks.reload();
    if (props.projectId) milestonesRes.reload();
  },
  setMilestoneFilter: (name: string) => {
    milestoneFilter.value = name || "";
  },
});
function featureTitle(name: string) {
  return (featuresRes.data || []).find((f: any) => f.name === name)?.feature_title;
}

const agents = createListResource({
  doctype: "HD Agent",
  fields: ["name", "agent_name"],
  filters: { is_active: 1 },
  pageLength: 500,
  auto: props.editable,
});
const agentOptions = computed(() =>
  (agents.data || []).map((a: any) => ({
    value: a.name,
    label: a.agent_name || a.name,
  }))
);

function priorityClass(p: string) {
  return (
    {
      Urgent: "bg-red-100 text-red-700",
      High: "bg-orange-100 text-orange-700",
      Medium: "bg-blue-100 text-blue-700",
      Low: "bg-surface-gray-2 text-ink-gray-6",
    }[p] || "bg-surface-gray-2 text-ink-gray-6"
  );
}
function isOverdue(t: any) {
  if (!t.end_date || t.status === "Done") return false;
  return dayjs(t.end_date).isBefore(dayjs().startOf("day"));
}

function reload() {
  tasks.reload();
  if (props.projectId) milestonesRes.reload();
  emit("changed");
}

const newSubject = ref("");
// When set, the task created by the next add_task success opens for naming.
let pendingOpenStatus: string | null = null;
const addRes = createResource({
  url: "helpdesk.api.addon.add_task",
  onSuccess: (name: string) => {
    newSubject.value = "";
    reload();
    if (pendingOpenStatus !== null && name) {
      openNew(name, pendingOpenStatus);
    }
    pendingOpenStatus = null;
  },
  onError: (e: any) => {
    pendingOpenStatus = null;
    toast.error(e?.messages?.[0] || __("Could not add task"));
  },
});
function add() {
  const s = newSubject.value.trim();
  if (!s) return;
  pendingOpenStatus = null;
  addRes.submit({ ...parentParams(), subject: s });
}
function quickAdd(status: string) {
  pendingOpenStatus = status;
  addRes.submit({
    ...parentParams(),
    subject: __("New task"),
    status,
    ...(milestoneFilter.value ? { milestone: milestoneFilter.value } : {}),
  });
}

// --- detail dialog ---
const showDetail = ref(false);
const selected = ref<any>(null);
const subjectInput = ref<any>(null);

// Scoring is reserved for the task's reviewer (managers may always score).
const canScore = computed(
  () =>
    props.editable &&
    !!selected.value &&
    (!!authStore.isManager || (!!selected.value.reviewer && selected.value.reviewer === userId))
);

// Open a just-created task with its name selected, so the placeholder
// "New task" can be renamed immediately.
async function openNew(name: string, status: string) {
  selected.value = {
    name,
    subject: __("New task"),
    status,
    priority: "Medium",
    milestone: milestoneFilter.value || "",
    feature: "",
    is_internal: 0,
    start_date: "",
    end_date: "",
    description: "",
    assigned_to: "",
    assigned_to_name: "",
    reviewer: "",
    reviewer_name: "",
    score: 0,
  };
  showDetail.value = true;
  comments.reload();
  if (props.editable) activity.reload();
  await nextTick();
  subjectInput.value?.focus?.();
  subjectInput.value?.select?.();
}

const comments = createResource({
  url: "helpdesk.api.addon.get_task_comments",
  makeParams: () => ({ task: selected.value?.name }),
});
// Audit trail (agents only).
const activity = createResource({
  url: "helpdesk.api.addon.get_task_activity",
  makeParams: () => ({ task: selected.value?.name }),
});
function open(t: any) {
  selected.value = { ...t };
  showDetail.value = true;
  comments.reload();
  if (props.editable) activity.reload();
}

const updateRes = createResource({
  url: "helpdesk.api.addon.update_task",
  onSuccess: () => {
    tasks.reload();
    if (props.projectId) milestonesRes.reload();
    if (showDetail.value && props.editable) activity.reload();
    emit("changed");
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not update task")),
});
function patch(fields: Record<string, any>) {
  if (!selected.value) return;
  Object.assign(selected.value, fields);
  updateRes.submit({ name: selected.value.name, ...fields });
}

const deleteRes = createResource({
  url: "helpdesk.api.addon.delete_task",
  onSuccess: () => {
    showDetail.value = false;
    reload();
  },
});
function remove() {
  if (!selected.value) return;
  const name = selected.value.name;
  const subject = selected.value.subject || __("this task");
  $dialog({
    title: __("Delete task"),
    message: __(
      "Delete “{0}”? This permanently removes the task with its subtasks, comments and attachments.",
      [subject]
    ),
    actions: [
      {
        label: __("Delete"),
        theme: "red",
        variant: "solid",
        onClick: (close: Function) => {
          deleteRes.submit({ name });
          close();
        },
      },
    ],
  });
}

const newComment = ref("");
const addCommentRes = createResource({
  url: "helpdesk.api.addon.add_task_comment",
  onSuccess: () => {
    newComment.value = "";
    comments.reload();
    tasks.reload();
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not post comment")),
});
function addComment() {
  const c = newComment.value.trim();
  if (!c || !selected.value) return;
  addCommentRes.submit({ task: selected.value.name, content: c });
}
</script>
