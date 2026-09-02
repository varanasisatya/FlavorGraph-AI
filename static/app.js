const form = document.querySelector("#recommend-form");
const ingredientsInput = document.querySelector("#ingredients");
const results = document.querySelector("#results");
const emptyState = document.querySelector("#empty-state");
const loading = document.querySelector("#loading");
const resultCount = document.querySelector("#result-count");
const graphFallback = document.querySelector("#graph-fallback");
let graphInstance;

const splitValues = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));

document.querySelectorAll("[data-ingredient]").forEach((button) => {
  button.addEventListener("click", () => {
    const values = splitValues(ingredientsInput.value);
    if (!values.includes(button.dataset.ingredient)) values.push(button.dataset.ingredient);
    ingredientsInput.value = values.join(", ");
  });
});

document.addEventListener("pointermove", (event) => {
  const glow = document.querySelector(".cursor-glow");
  glow.style.left = `${event.clientX}px`;
  glow.style.top = `${event.clientY}px`;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  emptyState.hidden = true;
  results.innerHTML = "";
  loading.hidden = false;
  resultCount.textContent = "Running model…";

  const payload = {
    ingredients: splitValues(ingredientsInput.value),
    diet: document.querySelector("#diet").value,
    max_time: document.querySelector("#max-time").value || null,
    cuisine: document.querySelector("#cuisine").value,
    allergies: splitValues(document.querySelector("#allergies").value),
  };

  try {
    const response = await fetch("/api/recommend", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Inference failed");
    renderResults(data.recommendations);
    renderGraph(data.graph);
  } catch (error) {
    emptyState.hidden = false;
    emptyState.querySelector("h3").textContent = "The inference could not complete.";
    emptyState.querySelector("p").textContent = error.message;
    resultCount.textContent = "Model error";
  } finally {
    loading.hidden = true;
  }
});

function renderResults(items) {
  resultCount.textContent = `${items.length} paths ranked`;
  if (!items.length) {
    emptyState.hidden = false;
    emptyState.querySelector("h3").textContent = "No recipes match these filters.";
    emptyState.querySelector("p").textContent = "Try relaxing the diet, allergy, cuisine or time constraint.";
    return;
  }
  emptyState.hidden = true;
  results.innerHTML = items.map((item, index) => {
    const image = item.image
      ? `<img class="recipe-image" src="${escapeHtml(item.image)}" alt="${escapeHtml(item.name)}">`
      : `<div class="recipe-image recipe-placeholder" role="img" aria-label="Abstract recipe placeholder">✦</div>`;
    const evidence = [
      ...item.matched.slice(0, 4).map((value) => `<span>✓ ${escapeHtml(value)}</span>`),
      ...item.substitutions.slice(0, 2).map((value) => `<span>↻ ${escapeHtml(value.use)} for ${escapeHtml(value.required)}</span>`),
      ...item.missing.slice(0, 2).map((value) => `<span class="missing-chip">− ${escapeHtml(value)}</span>`),
    ].join("");
    return `<article class="recipe-card" style="animation-delay:${index * 70}ms">
      ${image}
      <div><div class="recipe-meta"><span>${escapeHtml(item.cuisine)}</span><span>${item.time_minutes} min</span><span>${escapeHtml(item.diet.replace("_", " "))}</span></div>
      <h3>${escapeHtml(item.name)}</h3><p class="explanation">${escapeHtml(item.explanation)}</p>
      <p>${item.coverage}% pantry coverage · ${item.graph_signal}% graph signal</p><div class="evidence">${evidence}</div></div>
      <div class="score-ring" style="--score:${item.score}" aria-label="Recommendation score ${item.score} percent"><strong>${Math.round(item.score)}%</strong></div>
    </article>`;
  }).join("");
}

function renderGraph(graph) {
  if (!window.cytoscape || !graph.nodes.length) {
    graphFallback.hidden = false;
    return;
  }
  graphFallback.hidden = true;
  if (graphInstance) graphInstance.destroy();
  const elements = [
    ...graph.nodes.map((node) => ({data: node})),
    ...graph.edges.map((edge, index) => ({data: {id: `e-${index}`, source: edge.source, target: edge.target, relation: edge.relation}})),
  ];
  graphInstance = window.cytoscape({
    container: document.querySelector("#knowledge-graph"), elements,
    style: [
      {selector: "node", style: {"background-color": "#f3f0e7", label: "data(label)", color: "#f3f0e7", "font-size": 9, "text-valign": "bottom", "text-margin-y": 8, width: 24, height: 24}},
      {selector: "node[kind = 'recipe']", style: {"background-color": "#7758ff", width: 48, height: 48, "font-size": 11, "font-weight": 700}},
      {selector: "node[kind = 'flavor']", style: {"background-color": "#ff6b4a", shape: "diamond", width: 20, height: 20}},
      {selector: "node[inPantry]", style: {"background-color": "#b7f34a", color: "#b7f34a", width: 34, height: 34}},
      {selector: "edge", style: {width: 1.2, "line-color": "#5b5a62", opacity: 0.55, "curve-style": "bezier"}},
    ],
    layout: {
      name: "concentric",
      animate: false,
      fit: true,
      padding: 48,
      minNodeSpacing: 24,
      concentric: (node) => ({recipe: 4, ingredient: 3, flavor: 2, cuisine: 1}[node.data("kind")] || 0),
      levelWidth: () => 1,
    },
  });
  window.__flavorGraph = graphInstance;
  window.requestAnimationFrame(() => {
    graphInstance.resize();
    graphInstance.fit(undefined, 48);
  });
}

fetch("/api/evaluate").then((response) => response.json()).then((data) => {
  const cards = document.querySelectorAll("#metric-grid article");
  const values = [`${Math.round(data.hybrid.hit_rate_at_k * 100)}%`, data.hybrid.mean_reciprocal_rank.toFixed(2), `${Math.round(data.hybrid.catalog_coverage * 100)}%`, data.hybrid.queries];
  const notes = [`baseline ${Math.round(data.baseline.hit_rate_at_k * 100)}%`, "higher is better", "unique top-3 recipes", data.protocol];
  cards.forEach((card, index) => { card.querySelector("strong").textContent = values[index]; card.querySelector("small").textContent = notes[index]; });
}).catch(() => {});
