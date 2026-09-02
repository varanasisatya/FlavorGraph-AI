from pathlib import Path

from src.flavorgraph import FlavorGraphEngine

ROOT = Path(__file__).resolve().parents[1]


def make_engine() -> FlavorGraphEngine:
    return FlavorGraphEngine(ROOT / "data" / "recipes.json", ROOT / "data" / "ingredient_profiles.json")


def test_graph_contains_heterogeneous_nodes_and_edges():
    catalog = make_engine().catalog()
    assert catalog["recipes"] >= 10
    assert catalog["ingredients"] >= 40
    assert catalog["flavors"] >= 10
    assert catalog["edges"] > catalog["recipes"]


def test_complete_pantry_ranks_matching_recipe_first():
    results = make_engine().recommend(["tomato", "onion", "vegetable broth", "cream", "olive oil", "garlic"])
    assert results[0]["id"] == "tomato-soup"
    assert results[0]["coverage"] == 100.0


def test_aliases_and_substitutions_are_explained():
    results = make_engine().recommend(["pasta", "garlic", "butter", "chilli", "parsley", "lemon"])
    pasta = next(item for item in results if item["id"] == "aglio-e-olio")
    assert "spaghetti" in pasta["matched"]
    assert any(item["required"] == "olive oil" for item in pasta["substitutions"])


def test_diet_and_allergy_filters_apply():
    results = make_engine().recommend(
        ["tomatoes", "onion", "garlic", "rice"],
        diet="vegan",
        allergies=["dairy"],
    )
    assert results
    assert all(item["diet"] == "vegan" for item in results)
    assert all("dairy" not in item["allergens"] for item in results)


def test_evaluation_is_reproducible():
    engine = make_engine()
    first = engine.evaluate(k=3)
    second = engine.evaluate(k=3)
    assert first == second
    assert 0 <= first["hybrid"]["hit_rate_at_k"] <= 1
