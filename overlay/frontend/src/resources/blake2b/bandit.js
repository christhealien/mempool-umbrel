/* mempool for Umbrel (blake2b): light/dark toggle and gold highlighting of blocks found by Hash Bandit.
   Plain script, no dependencies. It only adds CSS classes to what the page already shows, so it keeps working
   when upstream changes its templates; if a selector stops matching, the highlight just doesn't appear. */
(function () {
  "use strict";
  var SLUG = "hashbandit";
  var root = document.documentElement;

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  /* ----- theme ----- */
  function apply(t) { root.setAttribute("data-b2b", t === "light" ? "light" : "dark"); var b = document.getElementById("b2b-toggle"); if (b) { b.textContent = t === "light" ? "☾" : "☀"; b.title = t === "light" ? "Switch to dark" : "Switch to light"; b.setAttribute("aria-label", b.title); } }
  var theme = store("b2b-theme") === "light" ? "light" : "dark";
  apply(theme);
  /* the toggle lives next to the search box (in the header, so it never floats over the page); until that box exists it is a fixed corner button */
  function dock(b) {
    var search = document.querySelector("app-search-form");
    if (!search || !search.parentNode) return;
    var wrap = search.parentNode;
    if (!wrap.classList || !wrap.classList.contains("b2b-searchwrap")) {
      wrap = document.createElement("div"); wrap.className = "b2b-searchwrap";
      search.parentNode.insertBefore(wrap, search); wrap.appendChild(search);
    }
    if (b.parentNode !== wrap) wrap.appendChild(b);
    b.classList.add("b2b-docked");
  }
  function addToggle() {
    if (!document.body) return;
    var b = document.getElementById("b2b-toggle");
    if (!b) {
      b = document.createElement("button");
      b.id = "b2b-toggle"; b.type = "button";
      b.addEventListener("click", function () { theme = theme === "light" ? "dark" : "light"; store("b2b-theme", theme); apply(theme); });
      document.body.appendChild(b); apply(theme);
    }
    if (!b.classList.contains("b2b-docked") || !b.parentNode || !b.parentNode.classList || !b.parentNode.classList.contains("b2b-searchwrap")) dock(b);
  }

  /* ----- gold ----- */
  var ready = false;                  // false while the page is first drawn: blocks already there don't pulse
  setTimeout(function () { ready = true; }, 6000);
  var GOLD_SEL = [
    'img[src*="/mining-pools/' + SLUG + '"]',
    'a[href$="/mining/pool/' + SLUG + '"]',
    'a[href*="/mining/pool/' + SLUG + '/"]'
  ].join(",");

  function mark(el, isNew) {
    if (!el || el.classList.contains("b2b-gold")) return;
    el.classList.add("b2b-gold");
    if (el.classList.contains("bitcoin-block") && !el.querySelector(".b2b-star")) {
      var st = document.createElement("span"); st.className = "b2b-star"; st.textContent = "\u2605"; el.appendChild(st);
    }
    if (isNew) { el.classList.add("b2b-gold-new"); setTimeout(function () { el.classList.remove("b2b-gold-new"); }, 6000); }
  }
  function scan() {
    var hits = document.querySelectorAll(GOLD_SEL);
    for (var i = 0; i < hits.length; i++) {
      var n = hits[i];
      var block = n.closest(".bitcoin-block");
      if (block) { mark(block, ready); continue; }
      var row = n.closest("tr");
      if (row) { mark(row, false); continue; }
      if (n.tagName === "A") n.classList.add("b2b-gold-link");
      var card = n.closest(".card");
      if (card) card.classList.add("b2b-gold-card");
    }
    // blocks that were gold but got re-used by the page for another block (the strip recycles elements)
    var golds = document.querySelectorAll(".bitcoin-block.b2b-gold");
    for (var j = 0; j < golds.length; j++) {
      if (!golds[j].querySelector(GOLD_SEL)) {
        golds[j].classList.remove("b2b-gold", "b2b-gold-new");
        var old = golds[j].querySelector(".b2b-star"); if (old) old.remove();
      }
    }
  }

  var queued = false;
  function queue() { if (queued) return; queued = true; (window.requestAnimationFrame || setTimeout)(function () { queued = false; addToggle(); scan(); }); }
  function start() {
    addToggle(); scan();
    new MutationObserver(queue).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["src", "href"] });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
