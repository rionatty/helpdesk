import { createApp, h } from "vue";
import {
  Badge,
  Button,
  Dialog,
  ErrorMessage,
  FeatherIcon,
  FormControl,
  frappeRequest,
  FrappeUI,
  setConfig,
  TextInput,
  toast,
  Tooltip,
} from "frappe-ui";
import { createPinia } from "pinia";
import App from "./App.vue";
import { createDialog } from "./components/dialogs";
import "./index.css";
import { router } from "./router";
import { telemetryPlugin } from "frappe-ui/frappe";
import { isCustomerPortal } from "@/utils";
import { __, translationPlugin } from "./translation";
import CircleAlert from "~icons/lucide/circle-alert";
import { initSocket } from "./socket";

const globalComponents = {
  Badge,
  Button,
  Dialog,
  ErrorMessage,
  FeatherIcon,
  FormControl,
  Tooltip,
  TextInput,
};

// frappe-ui@1.0.0-beta.3 (src/utils/frappeRequest.js:62-99) parses a non-2xx
// body with JSON.parse inside an EMPTY catch, then dereferences `error`
// unguarded at lines 73/82/86/89/99. A body that isn't JSON — an nginx/proxy
// 502/504 HTML page, an empty body, a 413, an HTML login redirect — leaves
// `error` undefined, so the library throws "Cannot read properties of
// undefined (reading 'exc')" and that TypeError REPLACES the real failure,
// erasing which URL actually failed. A 2xx carrying an HTML body fails the
// same way with a SyntaxError out of response.json().
// Only those two classes are rewritten: frappe-ui's own error objects are
// plain Errors and pass through untouched, and AbortError is a DOMException
// so resources.js's `error?.name !== 'AbortError'` check still works. No app
// code runs inside this try (onSuccess/transform run outside the fetcher
// promise), so this cannot swallow a component bug. The original error is
// kept on `cause` and logged — nothing is hidden.
setConfig("resourceFetcher", async (options) => {
  try {
    return await frappeRequest(options);
  } catch (err) {
    if (!(err instanceof TypeError) && !(err instanceof SyntaxError)) {
      throw err;
    }
    console.error(
      "[helpdesk] no usable response for",
      options?.url,
      "— raw error:",
      err
    );
    const wrapped = new Error(
      __("{0}: the server could not be reached, or it returned an invalid response", [
        options?.url || "request",
      ])
    );
    wrapped.cause = err;
    wrapped.exc_type = "InvalidServerResponse";
    wrapped.messages = [wrapped.message];
    throw wrapped;
  }
});
setConfig("serverMessagesHandler", (msgs) => {
  if (isCustomerPortal.value) {
    return;
  }
  msgs.forEach((msg) => {
    msg = JSON.parse(msg);
    if (msg && msg.message == "Feedback email has been sent to the customer.") {
      toast.success(msg.message);
      return;
    }
    toast.create({
      message: msg.message,
      icon: h(CircleAlert, { class: "text-ink-blue-2" }),
    });
  });
});
setConfig("fallbackErrorHandler", (error) => {
  // Keep the full error (incl. traceback) in the console for diagnosis —
  // the toast only carries the message.
  console.error("[helpdesk] unhandled resource error:", error);
  // `messages` is an array on frappe-ui errors but absent on plain ones, and
  // `message` is a String — calling .join on it throws inside this handler,
  // which resources.js swallows with a console.warn, so the user would get NO
  // toast at all. Never let the error handler be the thing that fails.
  const messages = Array.isArray(error?.messages) ? error.messages : [];
  const msg =
    messages.filter(Boolean).join(", ") ||
    error?.message ||
    __("Something went wrong");
  // Background permission failures are noise to portal customers (e.g. an
  // auxiliary widget they can't use anyway) — log them, don't toast them.
  if (isCustomerPortal.value && error?.exc_type === "PermissionError") {
    return;
  }
  toast.error(msg);
});

const pinia = createPinia();
const app = createApp(App);

app.use(FrappeUI);
app.use(pinia);
app.use(router);
app.use(translationPlugin);
app.use(telemetryPlugin, { app_name: "helpdesk" });

for (const c in globalComponents) {
  app.component(c, globalComponents[c]);
}

app.config.globalProperties.$dialog = createDialog;

let socket;
if (import.meta.env.DEV) {
  frappeRequest({
    url: "/api/method/helpdesk.www.helpdesk.index.get_context_for_dev",
  }).then((values) => {
    for (let key in values) {
      window[key] = values[key];
    }
    if (window.dir) document.documentElement.dir = window.dir;
    if (window.lang) document.documentElement.lang = window.lang;
    socket = initSocket();
    app.config.globalProperties.$socket = socket;
    app.mount("#app");
  });
} else {
  socket = initSocket();
  app.config.globalProperties.$socket = socket;
  app.mount("#app");
}
