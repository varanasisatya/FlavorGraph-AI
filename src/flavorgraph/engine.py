from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import networkx as nx

ALIASES = {
    "tomato": "tomatoes",
    "egg": "eggs",
    "carrot": "carrots",
    "pea": "peas",
    "avocado": "avocados",
    "scallion": "spring onion",
    "green onion": "spring onion",
    "chilli": "jalapeno",
    "chili": "jalapeno",
    "pasta": "spaghetti",
    "cheese": "cheddar cheese",
    "chickpea": "chickpeas",
    "garbanzo beans": "chickpeas",
    "yoghurt": "yogurt",
}


def normalize_ingredient(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    return ALIASES.get(normalized, normalized)


class FlavorGraphEngine:
    """Builds and queries a heterogeneous culinary knowledge graph.

    The model intentionally combines a graph signal with interpretable pantry
    coverage and flavor compatibility. It is deterministic, inspectable, and
    suitable as a baseline before training learned graph embeddings.
    """

    def __init__(self, recipes_path: Path | str, profiles_path: Path | str) -> None:
        self.recipes = self._load_json(recipes_path)
        self.profiles = self._load_json(profiles_path)
        self.recipe_by_id = {recipe["id"]: recipe for recipe in self.recipes}
        self.graph = self._build_graph()

    @staticmethod
    def _load_json(path: Path | str) -> Any:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _build_graph(self) -> nx.Graph:
        graph = nx.Graph()

        for ingredient, profile in self.profiles.items():
            ingredient_id = f"ingredient:{ingredient}"
            graph.add_node(
                ingredient_id,
                label=ingredient.title(),
                kind="ingredient",
                category=profile.get("category", "other"),
            )
            for flavor in profile.get("flavors", []):
                flavor_id = f"flavor:{flavor}"
                graph.add_node(flavor_id, label=flavor.title(), kind="flavor")
                graph.add_edge(ingredient_id, flavor_id, relation="expresses", weight=0.65)

        for ingredient, profile in self.profiles.items():
            for substitute in profile.get("substitutes", []):
                if substitute in self.profiles:
                    graph.add_edge(
                        f"ingredient:{ingredient}",
                        f"ingredient:{substitute}",
                        relation="substitutes",
                        weight=0.35,
                    )

        for recipe in self.recipes:
            recipe_id = f"recipe:{recipe['id']}"
            graph.add_node(recipe_id, label=recipe["name"], kind="recipe")

            cuisine_id = f"cuisine:{recipe['cuisine'].lower()}"
            graph.add_node(cuisine_id, label=recipe["cuisine"], kind="cuisine")
            graph.add_edge(recipe_id, cuisine_id, relation="belongs_to", weight=0.25)

            for ingredient in recipe["ingredients"]:
                ingredient_id = f"ingredient:{ingredient}"
                if ingredient_id not in graph:
                    graph.add_node(
                        ingredient_id,
                        label=ingredient.title(),
                        kind="ingredient",
                        category="other",
                    )
                graph.add_edge(recipe_id, ingredient_id, relation="contains", weight=1.0)

            for flavor in recipe["flavors"]:
                flavor_id = f"flavor:{flavor}"
                graph.add_node(flavor_id, label=flavor.title(), kind="flavor")
                graph.add_edge(recipe_id, flavor_id, relation="tastes_like", weight=0.45)

        return graph

    def _personalized_pagerank(
        self,
        seeds: Iterable[str],
        damping: float = 0.85,
        max_iterations: int = 80,
        tolerance: float = 1e-9,
    ) -> dict[str, float]:
        nodes = list(self.graph.nodes)
        seed_nodes = [node for node in seeds if node in self.graph]
        if not seed_nodes:
            return {node: 0.0 for node in nodes}

        personalization = {node: 0.0 for node in nodes}
        for node in seed_nodes:
            personalization[node] = 1.0 / len(seed_nodes)
        scores = personalization.copy()

        for _ in range(max_iterations):
            next_scores = {
                node: (1.0 - damping) * personalization[node]
                for node in nodes
            }
            dangling_mass = 0.0

            for node, score in scores.items():
                neighbors = list(self.graph[node].items())
                total_weight = sum(float(data.get("weight", 1.0)) for _, data in neighbors)
                if total_weight == 0:
                    dangling_mass += score
                    continue
                for neighbor, edge_data in neighbors:
                    weight = float(edge_data.get("weight", 1.0))
                    next_scores[neighbor] += damping * score * (weight / total_weight)

            if dangling_mass:
                for node, probability in personalization.items():
                    next_scores[node] += damping * dangling_mass * probability

            delta = sum(abs(next_scores[node] - scores[node]) for node in nodes)
            scores = next_scores
            if delta < tolerance:
                break

        return scores

    def _substitute_for(self, missing: str, pantry: set[str]) -> str | None:
        direct = set(self.profiles.get(missing, {}).get("substitutes", []))
        for candidate in sorted(pantry):
            reverse = set(self.profiles.get(candidate, {}).get("substitutes", []))
            if candidate in direct or missing in reverse:
                return candidate
        return None

    def _pantry_flavors(self, pantry: set[str]) -> set[str]:
        return {
            flavor
            for ingredient in pantry
            for flavor in self.profiles.get(ingredient, {}).get("flavors", [])
        }

    def recommend(
        self,
        ingredients: Iterable[str],
        *,
        diet: str = "any",
        max_time: int | None = None,
        cuisine: str = "any",
        allergies: Iterable[str] = (),
        limit: int = 6,
        strategy: str = "hybrid",
    ) -> list[dict[str, Any]]:
        pantry = {normalize_ingredient(item) for item in ingredients if item and item.strip()}
        allergy_set = {item.strip().lower() for item in allergies if item.strip()}
        graph_scores = self._personalized_pagerank(f"ingredient:{item}" for item in pantry)
        raw_recipe_graph_scores = {
            recipe["id"]: graph_scores.get(f"recipe:{recipe['id']}", 0.0)
            for recipe in self.recipes
        }
        max_graph_score = max(raw_recipe_graph_scores.values(), default=0.0) or 1.0
        pantry_flavors = self._pantry_flavors(pantry)
        recommendations: list[dict[str, Any]] = []

        for recipe in self.recipes:
            if diet != "any" and recipe["diet"] != diet:
                continue
            if cuisine != "any" and recipe["cuisine"].lower() != cuisine.lower():
                continue
            if max_time and recipe["time_minutes"] > max_time:
                continue
            if allergy_set.intersection(recipe.get("allergens", [])):
                continue

            required = set(recipe["ingredients"])
            exact_matches = required.intersection(pantry)
            missing = sorted(required - exact_matches)
            substitutions: list[dict[str, str]] = []
            unresolved: list[str] = []
            for item in missing:
                substitute = self._substitute_for(item, pantry)
                if substitute:
                    substitutions.append({"required": item, "use": substitute})
                else:
                    unresolved.append(item)

            covered = len(exact_matches) + len(substitutions)
            coverage = covered / max(len(required), 1)
            graph_signal = raw_recipe_graph_scores[recipe["id"]] / max_graph_score
            shared_flavors = sorted(pantry_flavors.intersection(recipe["flavors"]))
            flavor_alignment = len(shared_flavors) / max(len(set(recipe["flavors"])), 1)
            convenience = 1.0 / (1.0 + math.log1p(recipe["time_minutes"]))

            if strategy == "coverage":
                score = len(exact_matches) / max(len(required), 1)
            else:
                score = (
                    0.52 * coverage
                    + 0.25 * graph_signal
                    + 0.18 * flavor_alignment
                    + 0.05 * convenience
                    - 0.035 * len(unresolved)
                )
            score = max(0.0, min(1.0, score))

            if coverage == 1 and not substitutions:
                explanation = "Complete pantry match"
            elif coverage == 1:
                explanation = "Makeable with intelligent substitutions"
            elif shared_flavors:
                explanation = f"Connected through {', '.join(shared_flavors[:3])} flavor notes"
            else:
                explanation = "Ranked by ingredient coverage and graph proximity"

            recommendations.append(
                {
                    **recipe,
                    "score": round(score * 100, 1),
                    "coverage": round(coverage * 100, 1),
                    "graph_signal": round(graph_signal * 100, 1),
                    "flavor_alignment": round(flavor_alignment * 100, 1),
                    "matched": sorted(exact_matches),
                    "missing": unresolved,
                    "substitutions": substitutions,
                    "shared_flavors": shared_flavors,
                    "explanation": explanation,
                }
            )

        recommendations.sort(
            key=lambda result: (result["score"], result["coverage"], -result["time_minutes"]),
            reverse=True,
        )
        return recommendations[: max(1, min(limit, 12))]

    def graph_payload(
        self,
        ingredients: Iterable[str],
        recommendations: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        pantry = {normalize_ingredient(item) for item in ingredients if item.strip()}
        selected_nodes: set[str] = {
            f"ingredient:{item}"
            for item in pantry
            if f"ingredient:{item}" in self.graph
        }

        for recommendation in recommendations[:4]:
            recipe_node = f"recipe:{recommendation['id']}"
            selected_nodes.add(recipe_node)
            for ingredient in recommendation["matched"]:
                selected_nodes.add(f"ingredient:{ingredient}")
            for flavor in recommendation["shared_flavors"][:3]:
                selected_nodes.add(f"flavor:{flavor}")

        for node in list(selected_nodes):
            if node.startswith("recipe:"):
                selected_nodes.update(
                    neighbor
                    for neighbor in self.graph.neighbors(node)
                    if neighbor.startswith("flavor:")
                )

        nodes = [
            {
                "id": node,
                "label": self.graph.nodes[node].get("label", node),
                "kind": self.graph.nodes[node].get("kind", "other"),
                "inPantry": node.removeprefix("ingredient:") in pantry,
            }
            for node in sorted(selected_nodes)
            if node in self.graph
        ]
        edges = [
            {
                "source": source,
                "target": target,
                "relation": data.get("relation", "connected"),
            }
            for source, target, data in self.graph.edges(data=True)
            if source in selected_nodes and target in selected_nodes
        ]
        return {"nodes": nodes, "edges": edges}

    def evaluate(self, k: int = 3) -> dict[str, Any]:
        """Evaluate noisy pantry queries against an exact-overlap baseline.

        Each query observes roughly half a recipe and replaces one observed
        ingredient with a known substitute. This measures whether graph and
        ontology signals recover a relevant recipe when literal overlap is
        incomplete.
        """
        results: dict[str, Any] = {}
        for strategy in ("coverage", "hybrid"):
            reciprocal_rank = 0.0
            hits = 0
            recommended_catalog: set[str] = set()

            for recipe in self.recipes:
                ordered = sorted(recipe["ingredients"])
                observed_count = max(2, math.ceil(len(ordered) * 0.45))
                pantry = ordered[:observed_count]
                for index, ingredient in enumerate(pantry):
                    substitutes = [
                        item
                        for item in self.profiles.get(ingredient, {}).get("substitutes", [])
                        if item in self.profiles
                    ]
                    if substitutes:
                        pantry[index] = substitutes[0]
                        break
                ranked = self.recommend(pantry, limit=len(self.recipes), strategy=strategy)
                ids = [item["id"] for item in ranked]
                recommended_catalog.update(ids[:k])
                if recipe["id"] in ids:
                    rank = ids.index(recipe["id"]) + 1
                    reciprocal_rank += 1.0 / rank
                    if rank <= k:
                        hits += 1

            query_count = len(self.recipes)
            results[strategy] = {
                "hit_rate_at_k": round(hits / query_count, 3),
                "precision_at_k": round(hits / (query_count * k), 3),
                "mean_reciprocal_rank": round(reciprocal_rank / query_count, 3),
                "catalog_coverage": round(len(recommended_catalog) / query_count, 3),
                "k": k,
                "queries": query_count,
            }

        return {
            "protocol": "Deterministic 45% pantry holdout with substitution noise",
            "baseline": results["coverage"],
            "hybrid": results["hybrid"],
        }

    def catalog(self) -> dict[str, Any]:
        return {
            "recipes": len(self.recipes),
            "ingredients": len([node for node in self.graph if node.startswith("ingredient:")]),
            "flavors": len([node for node in self.graph if node.startswith("flavor:")]),
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "cuisines": sorted({recipe["cuisine"] for recipe in self.recipes}),
        }
