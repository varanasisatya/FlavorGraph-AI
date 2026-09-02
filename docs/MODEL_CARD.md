# FlavorGraph AI — Model Card

## Model overview

FlavorGraph AI is a deterministic hybrid recommender for recipe discovery. It combines a weighted culinary knowledge graph with explicit pantry-coverage and flavor-compatibility signals. It is a portfolio and learning project, not a trained large language model or a medical nutrition system.

## Intended use

- Explore recipes from ingredients a user already has
- Demonstrate explainable graph-based recommendation
- Provide a reproducible baseline for later embedding or GNN experiments
- Teach how graph signals and product constraints can be combined

## Inputs and outputs

Inputs include pantry ingredients and optional diet, cuisine, maximum-time, and allergen constraints. Outputs include ranked recipes, component scores, matched and missing ingredients, suggested substitutions, flavor bridges, and a focused inference graph.

## Data

The included dataset is a hand-curated catalog of 12 recipes and an ingredient profile ontology. Recipe records include cuisine, dietary category, preparation time, allergens, ingredients, flavor notes, instructions, and image paths. Ingredient profiles include category, flavor notes, and substitutions.

The data is intentionally small and inspectable. It is not representative of global food traditions, regional ingredient names, nutrition needs, availability, or all allergy risks.

## Method

The graph contains Recipe, Ingredient, Flavor, and Cuisine nodes connected by typed, weighted edges. Weighted Personalized PageRank starts from normalized pantry ingredients. The final score blends pantry coverage, normalized graph relevance, flavor alignment, and convenience, with a penalty for unresolved missing ingredients.

All scoring is deterministic. No external AI service, prompt, user profiling, or hidden training data is used.

## Evaluation

The benchmark exposes 45% of each recipe's ingredients and injects one available substitution. It reports Hit Rate@3, Precision@3, Mean Reciprocal Rank, and catalog coverage against an exact-overlap baseline. Both methods currently score equally on the 12-query benchmark, so no performance improvement is claimed.

## Limitations

- The dataset is too small for strong generalization or statistical conclusions.
- Substitution relationships are curated rules and may not work for every preparation.
- Allergy filtering depends entirely on catalog labels and must not be used as a safety guarantee.
- The ranking formula and weights are heuristic rather than learned from user interactions.
- Cuisine labels and flavor descriptions simplify diverse culinary traditions.
- Recipe instructions are illustrative and have not been professionally validated.

## Responsible use

Users should independently verify ingredients, allergens, food safety, and dietary suitability. The system should not be used for clinical nutrition, allergy-sensitive meal planning, or emergency guidance.

## Recommended next evaluation

Use a licensed public recipe corpus, deduplicate records, establish train/validation/test splits, and compare exact-overlap, content-based embeddings, graph embeddings, and a learned ranker. Report NDCG@K, Recall@K, MRR, catalog coverage, novelty, diversity, latency, and ablations with confidence intervals.
