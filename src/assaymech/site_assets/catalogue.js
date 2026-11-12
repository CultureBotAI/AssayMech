/* Progressive enhancement: every record and link already exists in the HTML. */
"use strict";
(() => {
  const form = document.getElementById("search-form");
  const query = document.getElementById("query");
  const category = document.getElementById("category");
  const kind = document.getElementById("kind");
  const rows = Array.from(document.querySelectorAll("[data-record]"));
  if (!form || !query || !category) return;
  const params = new URLSearchParams(window.location.search);
  query.value = params.get("q") || "";
  category.value = Array.from(category.options).some(o => o.value === params.get("category"))
    ? params.get("category") : "";
  if (kind) kind.value = Array.from(kind.options).some(o => o.value === params.get("kind"))
    ? params.get("kind") : "";
  function filter() {
    const term = query.value.trim().toLocaleLowerCase();
    let count = 0;
    rows.forEach(row => {
      const matches = row.dataset.search.toLocaleLowerCase().includes(term)
        && (!category.value || row.dataset.categories.split("|").includes(category.value))
        && (!kind || !kind.value || row.dataset.kind === kind.value);
      row.hidden = !matches;
      count += Number(matches);
    });
    document.getElementById("result-count").textContent = `Showing ${count} of ${rows.length} records.`;
    document.getElementById("no-results").hidden = count !== 0;
  }
  form.addEventListener("submit", event => { event.preventDefault(); filter(); });
  query.addEventListener("input", filter);
  category.addEventListener("change", filter);
  if (kind) kind.addEventListener("change", filter);
  form.addEventListener("reset", event => {
    event.preventDefault(); query.value = ""; category.value = ""; if (kind) kind.value = ""; filter(); query.focus();
  });
  filter();
  document.getElementById("controls").hidden = false;
})();
