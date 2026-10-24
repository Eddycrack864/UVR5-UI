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
  }

  // The observer already batches the changes of each task (requestAnimationFrame would stall
  // in a background tab). Only class changes are watched, so patch() doesn't retrigger itself.
  const start = () => {
    new MutationObserver(patch).observe(document.body, {
      subtree: true, childList: true, attributes: true, attributeFilter: ["class"],
    });
    patch();
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();

  // Choosing a dropdown option with Enter leaves the focus on <body>, so the screen reader
  // jumps back to the top of the page: put it back on the dropdown. Gradio reopens the list on
  // focus, so close it again with the Escape its own handler listens for.
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || !event.isTrusted || !event.target.closest) return;
    const box = event.target.closest('[role="combobox"]');
    if (!box) return;
    setTimeout(() => {
      if (document.activeElement !== document.body || !box.isConnected) return;
      box.focus({ preventScroll: true });
      box.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", code: "Escape", bubbles: true }));
    }, 50);
  }, true);
})();
