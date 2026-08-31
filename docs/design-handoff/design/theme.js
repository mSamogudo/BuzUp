/* Tema claro/escuro do BusUp.
 * Segue o sistema por omissão; a escolha manual fica em localStorage (buzup_theme),
 * a mesma chave que o portal real usa. Qualquer elemento com [data-bz-theme-toggle]
 * na página passa a ser o alternador; só se cria o botão flutuante quando não existe
 * nenhum (nunca se injecta nada dentro do #dc-root). */
(function () {
  if (window.__bzTheme) return;
  window.__bzTheme = true;

  var KEY = "buzup_theme";
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  var floatBtn = null;

  function stored() {
    try {
      var v = localStorage.getItem(KEY);
      return v === "dark" || v === "light" ? v : null;
    } catch (e) { return null; }
  }

  function effective() {
    return stored() || (mq && mq.matches ? "dark" : "light");
  }

  function inPage() {
    return Array.prototype.slice.call(document.querySelectorAll("[data-bz-theme-toggle]"));
  }

  function label(el, th) {
    var glyph = th === "dark" ? "☀" : "☾";
    var mark = el.querySelector("[data-bz-theme-glyph]") || el;
    if (mark.textContent !== glyph) mark.textContent = glyph;
    el.setAttribute("aria-label", th === "dark" ? "Usar tema claro" : "Usar tema escuro");
    el.title = th === "dark" ? "Tema claro" : "Tema escuro";
  }

  function apply() {
    var th = effective();
    document.documentElement.setAttribute("data-theme", th);
    document.documentElement.style.colorScheme = th;
    var page = inPage();
    page.forEach(function (el) {
      if (!el.__bzBound) { el.__bzBound = true; el.addEventListener("click", toggle); }
      label(el, th);
    });
    if (page.length && floatBtn) { floatBtn.remove(); floatBtn = null; }
    if (floatBtn) label(floatBtn, th);
  }

  function toggle() {
    var next = effective() === "dark" ? "light" : "dark";
    try { localStorage.setItem(KEY, next); } catch (e) {}
    apply();
  }

  function mount() {
    if (!floatBtn && !inPage().length) {
      floatBtn = document.createElement("button");
      floatBtn.type = "button";
      floatBtn.setAttribute("data-bz-theme-btn", "");
      floatBtn.style.cssText = [
        "position:fixed", "top:16px", "right:16px", "z-index:2147483000",
        "width:40px", "height:40px", "border-radius:999px",
        "border:1px solid var(--border,#E4EBF3)", "background:var(--surface,#fff)",
        "color:var(--muted,#5B6B7F)", "cursor:pointer", "font:500 16px/1 Inter,sans-serif",
        "display:flex", "align-items:center", "justify-content:center",
        "box-shadow:0 8px 22px rgba(13,59,102,.16)",
      ].join(";");
      floatBtn.addEventListener("click", toggle);
      document.body.appendChild(floatBtn);
    }
    apply();
  }

  apply();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
  if (window.MutationObserver) {
    new MutationObserver(function () { apply(); }).observe(document.documentElement, { childList: true, subtree: true });
  }
  if (mq && mq.addEventListener) mq.addEventListener("change", apply);
})();
