// Screen reader fixes that Gradio doesn't do yet (issue #66). Gradio adds it to the page
// <head> when the app mounts; CONFIG comes from uvr5_ui/ui/a11y.py.
(() => {
  if (window.uvr5A11y) return; // Gradio can insert the head twice
  window.uvr5A11y = true;
  const CONFIG = __CONFIG__;

  // Gradio picks its own UI language (and <html lang>) from the browser, so a Spanish browser
  // got Spanish Gradio texts next to an English app, read by NVDA with the wrong voice.
  // changeLocale is what Gradio's own settings panel calls; importing the already loaded
  // module gives the same instance. If a Gradio update renames it, nothing happens.
  const useAppLocale = () => {
    const core = performance.getEntriesByType("resource").map((entry) => entry.name)
      .find((name) => /\/assets\/core-[\w-]+\.js$/.test(name));
    if (!core) return false;
    import(core).then((module) => module.changeLocale && module.changeLocale(CONFIG.gradio_locale))
      .catch(() => {});
    return true;
  };
  if (!useAppLocale()) window.addEventListener("load", useAppLocale, { once: true });

  const keepLanguage = () => {
    if (document.documentElement.lang !== CONFIG.page_lang) document.documentElement.lang = CONFIG.page_lang;
  };
  keepLanguage();
  new MutationObserver(keepLanguage).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });

  // One polite live region for our announcements (stem_mixer, the announcer component...)
  let region = null;
  window.uvr5Announce = (text) => {
    if (!text || !document.body) return;
    if (!region || !region.isConnected) {
      region = document.createElement("div");
      region.className = "uvr-sr-only";
      region.setAttribute("role", "status");
      region.setAttribute("aria-live", "polite");
      region.setAttribute("aria-atomic", "true");
      document.body.append(region);
    }
    // Emptied first so the same message twice in a row is announced again
    region.textContent = "";
    setTimeout(() => { region.textContent = text; }, 100);
  };

  const ARROWS = /^[▼▲◀▶►◄]$/;
  const announced = new WeakSet();

  function patch() {
    // Accordions: no aria-expanded, and the arrow was read as "black down-pointing triangle"
    for (const button of document.querySelectorAll("button.label-wrap")) {
      const open = String(button.classList.contains("open"));
      if (button.getAttribute("aria-expanded") !== open) button.setAttribute("aria-expanded", open);
      for (const node of button.querySelectorAll("*")) {
        if (!node.children.length && ARROWS.test(node.textContent.trim()) && !node.hasAttribute("aria-hidden")) {
          node.setAttribute("aria-hidden", "true");
        }
      }
    }
    // Validation messages ("Please select a model first") appear outside any live region
    const errors = [];
    for (const error of document.querySelectorAll(".validation-error")) {
      if (announced.has(error)) continue;
      announced.add(error);
      const text = error.textContent.trim();
      if (text) errors.push(text);
    }
    if (errors.length) window.uvr5Announce(errors.join(". "));
    patchTabs();
  }

  // The observer already batches the changes of each task (requestAnimationFrame would stall
  // in a background tab). Only class and aria-selected are watched, which patch() never
  // changes, so it doesn't retrigger itself.
  const start = () => {
    new MutationObserver(patch).observe(document.body, {
      subtree: true, childList: true, attributes: true, attributeFilter: ["class", "aria-selected"],
    });
    patch();
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();

  // Choosing a dropdown option with Enter leaves the focus on <body>, so the screen reader
  // jumps back to the top of the page: put it back on the dropdown right away, before the
  // screen reader announces the page. Gradio reopens the list on focus, so close it again with
  // the Escape its own handler listens for.
  let enterOn = null;
  document.addEventListener("keydown", (event) => {
    const box = event.target.closest && event.target.closest('[role="combobox"]');
    enterOn = event.key === "Enter" && event.isTrusted && box ? box : null;
  }, true);
  document.addEventListener("focusout", (event) => {
    const box = enterOn;
    if (!box || event.target !== box || event.relatedTarget) return;
    enterOn = null;
    queueMicrotask(() => {
      if (!box.isConnected || (document.activeElement && document.activeElement !== document.body)) return;
      box.focus({ preventScroll: true });
      box.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", code: "Escape", bubbles: true }));
    });
  }, true);

  // Tabs: Gradio makes every tab a Tab stop and ignores the arrow keys. Use the ARIA tabs
  // pattern: only the selected tab is a Tab stop, and the arrows/Home/End move between tabs
  // (Enter or Space opens one).
  const visibleTabs = (list) => [...list.querySelectorAll('[role="tab"]')].filter((tab) => tab.offsetParent);
  function patchTabs() {
    for (const list of document.querySelectorAll('[role="tablist"]')) {
      const tabs = visibleTabs(list);
      const current = tabs.find((tab) => tab === document.activeElement)
        || tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
      for (const tab of tabs) {
        const index = tab === current ? 0 : -1;
        if (tab.tabIndex !== index) tab.tabIndex = index;
      }
    }
  }
  document.addEventListener("keydown", (event) => {
    const tab = event.target.closest && event.target.closest('[role="tab"]');
    const list = tab && tab.closest('[role="tablist"]');
    if (!list || !["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    const tabs = visibleTabs(list);
    const index = tabs.indexOf(tab);
    const next = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 }[event.key];
    const target = tabs[(next + tabs.length) % tabs.length];
    event.preventDefault();
    target.focus();
    patchTabs();
  });
  document.addEventListener("focusout", (event) => {
    if (event.target.closest && event.target.closest('[role="tablist"]')) setTimeout(patchTabs);
  });
})();
