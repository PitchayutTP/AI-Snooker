// Keep browser Back/Forward inside the SPA. Large reports stay in memory,
// not in the URL or the browser's serialised history state.
export function createPageHistory(browser, { capture, onChange, resolve = (page) => page }) {
  const owner = `snooker-${Math.random().toString(36).slice(2)}`;
  const records = new Map();
  let current = 0,
    next = 0;
  function write(method, id, record) {
    browser.history[method]({ snookerNavigation: owner, entry: id }, "", `#${record.page}`);
  }
  function save() {
    const record = records.get(current);
    if (record) record.context = { ...capture() };
  }
  function show(record) {
    const page = resolve(record.page, record.context);
    if (page !== record.page) {
      record.page = page;
      write("replaceState", current, record);
    }
    onChange(page, record.context);
  }
  function pop(event) {
    save();
    const state = event.state;
    if (state?.snookerNavigation === owner && records.has(state.entry)) {
      current = state.entry;
      show(records.get(current));
    } else {
      // A refresh or different account must not restore an old report/context.
      current = ++next;
      const record = { page: "dashboard", context: { ...capture() }, depth: 0 };
      records.set(current, record);
      write("replaceState", current, record);
      show(record);
    }
  }
  return {
    start() {
      const root = { page: "dashboard", context: { ...capture() }, depth: 0 };
      records.set(current, root);
      write("replaceState", current, root);
      browser.addEventListener("popstate", pop);
    },
    stop() {
      browser.removeEventListener("popstate", pop);
      records.clear();
    },
    reset(page = "dashboard", context = {}) {
      records.clear();
      current = ++next;
      const record = { page, context: { ...capture(), ...context }, depth: 0 };
      records.set(current, record);
      write("replaceState", current, record);
      show(record);
    },
    navigate(page, context = {}) {
      save();
      const before = records.get(current);
      const merged = { ...capture(), ...context };
      if (
        before?.page === page &&
        before.context.exerciseId === merged.exerciseId &&
        before.context.report?.id === merged.report?.id
      )
        return;
      const record = { page, context: merged, depth: (before?.depth ?? 0) + 1 };
      current = ++next;
      records.set(current, record);
      write("pushState", current, record);
      show(record);
    },
    back() {
      if (records.get(current)?.depth > 0) browser.history.back();
      else this.navigate("dashboard");
    },
  };
}
