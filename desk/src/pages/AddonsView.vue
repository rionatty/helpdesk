<template>
  <div
    class="flex flex-col h-full"
    :class="isCustomerPortal && 'bg-customer-portal'"
  >
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucidePackage class="size-5 text-ink-gray-7" />
          <div class="text-lg font-medium text-ink-gray-9">
            {{ __("Add-ons") }}
          </div>
        </div>
      </template>
      <template #right-header>
        <Button
          v-if="!isCustomerPortal"
          variant="solid"
          theme="gray"
          @click="openCreate"
        >
          <template #prefix><LucidePlus class="size-4" /></template>
          {{ __("New add-on") }}
        </Button>
      </template>
    </LayoutHeader>

    <div
      class="w-full max-w-screen-xl mx-auto px-4 md:px-6 lg:px-8 py-6 flex flex-col gap-5 flex-1 overflow-y-auto"
    >
      <Link
        v-if="!isCustomerPortal"
        class="form-control w-56"
        doctype="HD Customer"
        :placeholder="__('Filter by customer')"
        v-model="customerFilter"
        :hide-me="true"
      />

      <div v-if="addons.loading" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div
          v-for="i in 4"
          :key="i"
          class="h-28 rounded-xl bg-surface-gray-2 animate-pulse"
        />
      </div>

      <div
        v-else-if="!addons.data?.length"
        class="executive-card flex flex-col items-center justify-center text-center py-14 gap-2"
      >
        <div
          class="size-12 rounded-full bg-surface-gray-2 flex items-center justify-center"
        >
          <LucidePackage class="size-6 text-ink-gray-5" />
        </div>
        <p class="font-medium text-ink-gray-8">{{ __("No add-ons yet") }}</p>
        <p class="text-sm text-ink-gray-5">
          {{
            isCustomerPortal
              ? __("Apps and modules deployed for you will appear here.")
              : __("Add the apps/modules a customer is running.")
          }}
        </p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          v-for="a in addons.data"
          :key="a.name"
          type="button"
          class="executive-card executive-card-hover text-start p-5 flex flex-col gap-3"
          @click="open(a.name)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-center gap-3 min-w-0">
              <div
                class="size-10 rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center shrink-0 shadow-sm"
              >
                <LucidePackage class="size-5 text-white" />
              </div>
              <div class="min-w-0">
                <div class="text-base font-semibold text-ink-gray-9 truncate">
                  {{ a.addon_name }}
                </div>
                <div class="text-xs text-ink-gray-5 truncate">
                  {{ a.version ? "v" + a.version : "—" }}
                  <template v-if="!isCustomerPortal"> · {{ a.customer }}</template>
                </div>
              </div>
            </div>
            <Badge
              :label="a.status"
              :theme="statusTheme(a.status)"
              variant="subtle"
            />
          </div>
          <div class="flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-gray-6">
            <span v-if="a.activated_on">
              {{ __("Activated") }}: {{ a.activated_on }}
            </span>
            <span v-if="a.renewal_date">
              {{ __("Renews") }}: {{ a.renewal_date }}
            </span>
          </div>
          <p v-if="a.notes" class="text-sm text-ink-gray-7 truncate">
            {{ a.notes }}
          </p>
        </button>
      </div>
    </div>

    <!-- Create dialog (agent only) -->
    <Dialog
      v-if="!isCustomerPortal"
      v-model="showCreate"
      :options="{ title: __('New add-on'), size: 'lg' }"
    >
      <template #body-content>
        <div class="flex flex-col gap-3.5">
          <FormControl
            v-model="form.addon_name"
            :label="__('Add-on name')"
            type="text"
          />
          <div class="flex flex-col gap-1">
            <span class="text-xs text-ink-gray-6">{{ __("Customer") }}</span>
            <Link doctype="HD Customer" v-model="form.customer" />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <FormControl
              v-model="form.status"
              :label="__('Status')"
              type="select"
              :options="statusOptions"
            />
            <FormControl
              v-model="form.version"
              :label="__('Version')"
              type="text"
            />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <FormControl
              v-model="form.activated_on"
              :label="__('Activated on')"
              type="date"
            />
            <FormControl
              v-model="form.renewal_date"
              :label="__('Renewal date')"
              type="date"
            />
          </div>
          <FormControl v-model="form.notes" :label="__('Notes')" type="textarea" />
        </div>
      </template>
      <template #actions>
        <Button
          variant="solid"
          theme="blue"
          class="w-full"
          :loading="createRes.loading"
          @click="submitCreate"
        >
          {{ __("Create add-on") }}
        </Button>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import {
  Badge,
  Button,
  Dialog,
  FormControl,
  createResource,
  toast,
  usePageMeta,
} from "frappe-ui";
import { useRouter } from "vue-router";
import { LayoutHeader, Link } from "@/components";
import { isCustomerPortal } from "@/utils";
import { __ } from "@/translation";
import LucidePackage from "~icons/lucide/package";
import LucidePlus from "~icons/lucide/plus";

const router = useRouter();
const STATUSES = ["Active", "Trial", "Suspended", "Retired"];
const statusOptions = STATUSES.map((s) => ({ label: s, value: s }));
const customerFilter = ref("");

const addons = createResource({
  url: "helpdesk.api.addon.get_addons",
  makeParams: () => ({ customer: customerFilter.value || undefined }),
  auto: true,
});
watch(customerFilter, () => addons.reload());

function statusTheme(status: string) {
  return (
    { Active: "green", Trial: "blue", Suspended: "orange", Retired: "gray" }[
      status
    ] || "gray"
  );
}

function open(name: string) {
  router.push({
    name: isCustomerPortal.value ? "AddonCustomer" : "AddonAgent",
    params: { addonId: name },
  });
}

// --- Create (agent) ---
const showCreate = ref(false);
const form = reactive({
  addon_name: "",
  customer: "",
  status: "Active",
  version: "",
  activated_on: "",
  renewal_date: "",
  notes: "",
});
function openCreate() {
  Object.assign(form, {
    addon_name: "",
    customer: "",
    status: "Active",
    version: "",
    activated_on: "",
    renewal_date: "",
    notes: "",
  });
  showCreate.value = true;
}
const createRes = createResource({
  url: "helpdesk.api.addon.create_addon",
  onSuccess: (name: string) => {
    showCreate.value = false;
    toast.success(__("Add-on created"));
    router.push({ name: "AddonAgent", params: { addonId: name } });
  },
  onError: (e: any) =>
    toast.error(e?.messages?.[0] || __("Could not create add-on")),
});
function submitCreate() {
  if (!form.addon_name.trim() || !form.customer) {
    toast.error(__("Add-on name and customer are required"));
    return;
  }
  createRes.submit({ ...form });
}

usePageMeta(() => ({ title: __("Add-ons") }));
</script>
