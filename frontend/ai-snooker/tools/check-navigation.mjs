import assert from "node:assert/strict";
import { createPageHistory } from "../src/lib/pageHistory.js";

function browserFixture() {
  const events = new EventTarget();
  const entries = [{ state: null, url: "https://example.org" }];
  let index = 0;
  const browser = {
    addEventListener: (...args) => events.addEventListener(...args),
    removeEventListener: (...args) => events.removeEventListener(...args),
    history: {
      replaceState(state, unused, url) {
        entries[index] = { state, url };
      },
      pushState(state, unused, url) {
        entries.splice(index + 1);
        entries.push({ state, url });
        index++;
      },
      back() {
        if (index > 0) {
          index--;
          emit();
        }
      },
      forward() {
        if (index < entries.length - 1) {
          index++;
          emit();
        }
      },
    },
  };
  function emit() {
    const event = new Event("popstate");
    event.state = entries[index].state;
    events.dispatchEvent(event);
  }
  return {
    browser,
    entries,
    get index() {
      return index;
    },
  };
}

const fixture = browserFixture();
let context = { exerciseId: "", criteriaId: "", report: null, sessionId: null };
let page = "dashboard";
const navigation = createPageHistory(fixture.browser, {
  capture: () => context,
  resolve: (target) => (target === "training" && !context.sessionId ? "dashboard" : target),
  onChange: (target, value) => {
    page = target;
    context = { ...value, sessionId: context.sessionId };
  },
});
navigation.start();
assert.equal(fixture.entries.length, 1);
navigation.navigate("setup", { exerciseId: "1", criteriaId: "11" });
navigation.navigate("criteria");
const length = fixture.entries.length;
fixture.browser.history.back();
assert.equal(page, "setup");
assert.equal(context.exerciseId, "1");
assert.equal(fixture.entries.length, length);
fixture.browser.history.forward();
assert.equal(page, "criteria");
navigation.navigate("setup", { exerciseId: "3", criteriaId: "31" });
fixture.browser.history.back();
assert.equal(context.exerciseId, "1");
fixture.browser.history.forward();
assert.equal(context.exerciseId, "3");
navigation.navigate("summary", { report: { id: "first", attempts: [] } });
navigation.navigate("history");
navigation.navigate("summary", { report: { id: "second", attempts: [] } });
fixture.browser.history.back();
fixture.browser.history.back();
assert.equal(page, "summary");
assert.equal(context.report.id, "first");
assert.deepEqual(Object.keys(fixture.entries[fixture.index].state).sort(), [
  "entry",
  "snookerNavigation",
]);

context.sessionId = "live-session";
navigation.navigate("training");
navigation.navigate("profile");
fixture.browser.history.back();
assert.equal(page, "training");
assert.equal(context.sessionId, "live-session");
fixture.browser.history.forward();
context.sessionId = null;
fixture.browser.history.back();
assert.equal(page, "dashboard");
navigation.stop();
fixture.browser.history.forward();
assert.equal(page, "dashboard");

// StrictMode setup/cleanup and login remount do not add artificial history entries.
const count = fixture.entries.length;
let restored = false;
const fresh = createPageHistory(fixture.browser, {
  capture: () => ({}),
  onChange: () => {
    restored = true;
  },
});
fresh.start();
assert.equal(fixture.entries.length, count);
fixture.browser.history.back();
assert.equal(restored, true);
fresh.stop();
const resetFixture = browserFixture();
let resetContext = { report: { id: "deleted" } };
let resetPage;
const resetNavigation = createPageHistory(resetFixture.browser, {
  capture: () => resetContext,
  onChange: (page, value) => {
    resetPage = page;
    resetContext = value;
  },
});
resetNavigation.start();
resetNavigation.navigate("summary");
resetNavigation.navigate("profile");
resetNavigation.reset("profile", { report: null });
assert.equal(resetPage, "profile");
assert.equal(resetContext.report, null);
resetFixture.browser.history.back();
assert.equal(resetPage, "dashboard");
assert.equal(resetContext.report, null);
resetNavigation.stop();
console.log(
  "Navigation checks passed: Back/Forward, module and report restoration, active/completed session, cleanup, remount",
);
