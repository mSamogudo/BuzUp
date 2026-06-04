/* ============================================================
   BuzUp — shared interactions  (PayUp engine)
   ============================================================ */
(function () {
  /* ---------- Language (PT default, EN toggle) ---------- */
  const saved = localStorage.getItem("buzup-lang") || "pt";
  const applyLang = (lang) => {
    document.documentElement.lang = lang;
    localStorage.setItem("buzup-lang", lang);
    document.querySelectorAll("[data-lang-btn]").forEach((b) =>
      b.classList.toggle("active", b.dataset.langBtn === lang)
    );
    if (document.body.dataset.titlePt) {
      document.title = lang === "en"
        ? (document.body.dataset.titleEn || document.title)
        : document.body.dataset.titlePt;
    }
  };
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-lang-btn]");
    if (btn) applyLang(btn.dataset.langBtn);
  });
  applyLang(saved);

  /* ---------- Theme (dark default, light toggle) ---------- */
  const savedTheme = localStorage.getItem("buzup-theme") || "dark";
  const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("buzup-theme", theme);
    document.querySelectorAll("[data-theme-btn]").forEach((b) =>
      b.setAttribute("aria-pressed", theme === "light")
    );
  };
  applyTheme(savedTheme);
  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-theme-btn]")) {
      const cur = document.documentElement.getAttribute("data-theme");
      applyTheme(cur === "light" ? "dark" : "light");
    }
  });

  /* ---------- Nav scroll state ---------- */
  const nav = document.querySelector(".nav");
  if (nav) {
    const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- Mobile menu ---------- */
  const burger = document.querySelector(".nav__burger");
  const drawer = document.querySelector(".drawer");
  if (burger && drawer) {
    burger.addEventListener("click", () => {
      const open = drawer.classList.toggle("open");
      document.body.style.overflow = open ? "hidden" : "";
    });
    drawer.addEventListener("click", (e) => {
      if (e.target.closest("a") || e.target === drawer) {
        drawer.classList.remove("open");
        document.body.style.overflow = "";
      }
    });
  }

  /* ---------- Scroll reveal ---------- */
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    },
    { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
  );
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

  /* ---------- Count-up stats ---------- */
  const fmt = (n) => n.toLocaleString("pt-PT");
  const animateCount = (el) => {
    const target = parseFloat(el.dataset.count);
    const suffix = el.dataset.suffix || "";
    const dur = 1400, t0 = performance.now();
    const step = (t) => {
      const p = Math.min((t - t0) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const val = target * eased;
      el.textContent = (Number.isInteger(target) ? fmt(Math.round(val)) : val.toFixed(1)) + suffix;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  const countIO = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) { animateCount(en.target); countIO.unobserve(en.target); }
    });
  }, { threshold: 0.6 });
  document.querySelectorAll("[data-count]").forEach((el) => countIO.observe(el));

  /* ---------- Smooth-scroll for in-page anchors ---------- */
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      const id = a.getAttribute("href");
      if (id.length < 2) return;
      const t = document.querySelector(id);
      if (t) {
        e.preventDefault();
        const y = t.getBoundingClientRect().top + window.scrollY - 88;
        window.scrollTo({ top: y, behavior: "smooth" });
      }
    });
  });
})();
