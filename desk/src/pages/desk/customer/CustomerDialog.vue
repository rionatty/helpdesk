<template>
  <Dialog bare>
    <div class="flex flex-col items-center gap-4 p-6 w-80">
      <div class="text-xl font-medium text-ink-gray-9">
        {{ customer.doc?.name }}
      </div>
      <Avatar
        size="lg"
        :label="customer.doc?.name"
        :image="customer.doc?.image"
        class="cursor-pointer hover:opacity-80"
      />
      <div class="flex gap-2">
        <FileUploader @success="(file) => updateImage(file)">
          <template #default="{ uploading, openFileSelector }">
            <Button
              :label="
                customer.doc?.image ? __('Change photo') : __('Upload photo')
              "
              :loading="uploading"
              @click="openFileSelector"
            />
          </template>
        </FileUploader>
        <Button
          v-if="customer.doc?.image"
          :label="__('Remove photo')"
          @click="updateImage(null)"
        />
      </div>

      <form class="w-full space-y-4" @submit.prevent="update">
        <TextInput v-model="domain" label="Domain" placeholder="example.com" />
        <Button
          type="button"
          class="w-full"
          variant="solid"
          theme="gray"
          :label="__('Save')"
          :loading="customer.setValue.loading"
          @click="update"
        />
      </form>

      <!-- Users section -->
      <div class="w-full border-t border-outline-gray-1 pt-3">
        <p class="text-xs font-medium text-ink-gray-5 uppercase tracking-wide mb-2">
          {{ __("Users") }} ({{ customerContacts.length }})
        </p>

        <!-- Search to add -->
        <Autocomplete
          :value="null"
          :options="contactSearchOptions"
          :filterable="false"
          size="sm"
          :placeholder="__('Search contact to add…')"
          class="mb-3"
          @update:query="onSearchQuery"
          @change="onContactSelected"
        />

        <!-- Contact rows -->
        <div class="space-y-1.5">
          <div
            v-for="c in customerContacts"
            :key="c.name"
            class="flex items-center justify-between rounded-lg px-2 py-1.5 bg-surface-gray-1"
          >
            <div class="flex items-center gap-2 min-w-0">
              <Avatar size="xs" :label="c.full_name" :image="c.image" />
              <div class="min-w-0">
                <p class="text-sm font-medium text-ink-gray-9 truncate">
                  {{ c.full_name }}
                </p>
                <p class="text-xs text-ink-gray-5 truncate">{{ c.email_id }}</p>
              </div>
            </div>
            <div class="flex items-center gap-1 shrink-0 ms-2">
              <span
                v-if="c.user"
                class="text-xs px-1.5 py-0.5 rounded bg-green-50 text-green-700 font-medium border border-green-200"
              >
                {{ __("Login") }}
              </span>
              <Button
                v-else
                size="sm"
                :label="__('Invite')"
                :loading="invitingContact === c.name"
                @click="inviteContact(c)"
              />
              <button
                class="p-1 rounded hover:bg-surface-gray-2 text-ink-gray-4 hover:text-ink-gray-8 transition-colors"
                :title="__('Remove')"
                @click="removeContact(c.name)"
              >
                <FeatherIcon name="x" class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          <p
            v-if="!customerContacts.length"
            class="text-center text-sm text-ink-gray-4 py-3"
          >
            {{ __("No users yet — search above to add.") }}
          </p>
        </div>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import Autocomplete from "@/components/Autocomplete.vue";
import {
  Avatar,
  Button,
  call,
  createDocumentResource,
  Dialog,
  FeatherIcon,
  FileUploader,
  toast,
} from "frappe-ui";
import { computed, onMounted, ref } from "vue";

const props = defineProps({
  name: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["customer-updated"]);

// ── Customer document ──────────────────────────────────────────────────────

const domain = computed({
  get() {
    return customer.doc?.domain;
  },
  set(d: string) {
    customer.doc.domain = d;
  },
});

const customer = createDocumentResource({
  doctype: "HD Customer",
  name: props.name,
  auto: true,
  setValue: {
    onSuccess() {
      toast.success(__("Customer updated successfully."));
    },
    onError() {
      toast.error(__("Error updating customer"));
    },
  },
});

async function update() {
  await customer.setValue.submit({
    domain: domain.value,
  });
  emit("customer-updated");
}

function updateImage(file) {
  customer.setValue.submit({
    image: file?.file_url || null,
  });
  emit("customer-updated");
}

// ── Contacts / Users ───────────────────────────────────────────────────────

const customerContacts = ref<any[]>([]);
const contactSearchOptions = ref<any[]>([]);
const invitingContact = ref("");

async function loadContacts() {
  const result = await call("helpdesk.api.contact.get_customer_contacts", {
    customer: props.name,
  });
  customerContacts.value = result || [];
}

async function onSearchQuery(q: string) {
  if (!q) {
    contactSearchOptions.value = [];
    return;
  }
  const results = await call("helpdesk.api.contact.search_contacts", { txt: q });
  const linked = new Set(customerContacts.value.map((c) => c.name));
  contactSearchOptions.value = (results || [])
    .filter((r) => !linked.has(r.name))
    .map((r) => ({
      label: r.full_name || r.email_id,
      value: r.name,
    }));
}

async function onContactSelected(opt: any) {
  if (!opt?.value) return;
  try {
    await call("helpdesk.api.contact.add_contact_to_customer", {
      contact: opt.value,
      customer: props.name,
    });
    contactSearchOptions.value = [];
    await loadContacts();
    toast.success(__("User added"));
  } catch {
    toast.error(__("Failed to add user"));
  }
}

async function removeContact(contactName: string) {
  try {
    await call("helpdesk.api.contact.remove_contact_from_customer", {
      contact: contactName,
      customer: props.name,
    });
    await loadContacts();
  } catch {
    toast.error(__("Failed to remove user"));
  }
}

async function inviteContact(contact: any) {
  invitingContact.value = contact.name;
  try {
    await call("frappe.contacts.doctype.contact.contact.invite_user", {
      contact: contact.name,
    });
    toast.success(__("Invitation sent to " + contact.email_id));
    await loadContacts();
  } catch {
    toast.error(__("Failed to send invitation"));
  } finally {
    invitingContact.value = "";
  }
}

onMounted(loadContacts);
</script>
