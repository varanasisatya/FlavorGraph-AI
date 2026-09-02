from app import create_app


def test_health_endpoint():
    client = create_app().test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_recommend_endpoint_returns_explanations_and_graph():
    client = create_app().test_client()
    response = client.post("/api/recommend", json={"ingredients": ["tomatoes", "onion", "garlic"]})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["recommendations"]
    assert payload["graph"]["nodes"]
    assert "explanation" in payload["recommendations"][0]


def test_recommend_endpoint_validates_input():
    client = create_app().test_client()
    response = client.post("/api/recommend", json={"ingredients": []})
    assert response.status_code == 400
