from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from src.flavorgraph import FlavorGraphEngine

BASE_DIR = Path(__file__).resolve().parent


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    engine = FlavorGraphEngine(
        BASE_DIR / "data" / "recipes.json",
        BASE_DIR / "data" / "ingredient_profiles.json",
    )

    @app.get("/")
    def index():
        return render_template("index.html", catalog=engine.catalog())

    @app.get("/api/health")
    def health():
        return jsonify({"status": "healthy", "model": "flavorgraph-hybrid-v1", **engine.catalog()})

    @app.post("/api/recommend")
    def recommend():
        payload = request.get_json(silent=True) or {}
        ingredients = payload.get("ingredients", [])
        if not isinstance(ingredients, list) or not any(str(item).strip() for item in ingredients):
            return jsonify({"error": "Add at least one pantry ingredient."}), 400

        max_time = payload.get("max_time")
        try:
            max_time = int(max_time) if max_time else None
        except (TypeError, ValueError):
            return jsonify({"error": "max_time must be a whole number."}), 400

        allergies = payload.get("allergies", [])
        if not isinstance(allergies, list):
            return jsonify({"error": "allergies must be a list."}), 400

        cleaned = [str(item)[:80] for item in ingredients[:30]]
        recommendations = engine.recommend(
            cleaned,
            diet=str(payload.get("diet", "any")),
            cuisine=str(payload.get("cuisine", "any")),
            max_time=max_time,
            allergies=[str(item)[:40] for item in allergies[:10]],
            limit=6,
        )
        return jsonify(
            {
                "recommendations": recommendations,
                "graph": engine.graph_payload(cleaned, recommendations),
                "model": {
                    "name": "FlavorGraph Hybrid Ranker",
                    "version": "1.0.0",
                    "signals": ["pantry coverage", "personalized graph propagation", "flavor compatibility"],
                },
            }
        )

    @app.get("/api/evaluate")
    def evaluate():
        return jsonify(engine.evaluate(k=3))

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "Request payload is too large."}), 413

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
