from pathlib import Path

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


class DummyCache:
    def __init__(self):
        self.store = {}

    def get_json(self, key):
        return self.store.get(key)

    def set_json(self, key, value):
        self.store[key] = value

    def invalidate_products(self):
        self.store.clear()


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_background_import_and_cached_reads(monkeypatch, tmp_path):
    dummy_cache = DummyCache()
    monkeypatch.setattr("app.main.cache", dummy_cache)
    monkeypatch.setattr("app.tasks.cache", dummy_cache)

    csv_file = tmp_path / "products.csv"
    csv_file.write_text("name,description,price\nTea,Black tea,3.5\nCoffee,Ground coffee,7\n", encoding="utf-8")

    with TestClient(app) as client:
        response = client.post("/tasks/import-csv", params={"csv_path": str(csv_file)})
        assert response.status_code == 202

        products_response = client.get("/products")
        assert products_response.status_code == 200
        products = products_response.json()
        assert [product["name"] for product in products] == ["Tea", "Coffee"]
        assert "products:list:0:100" in dummy_cache.store

        detail_response = client.get(f"/products/{products[0]['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["name"] == "Tea"
        assert f"products:item:{products[0]['id']}" in dummy_cache.store


def test_background_delete_invalidates_cache(monkeypatch):
    dummy_cache = DummyCache()
    monkeypatch.setattr("app.main.cache", dummy_cache)
    monkeypatch.setattr("app.tasks.cache", dummy_cache)

    with TestClient(app) as client:
        first = client.post("/products", json={"name": "Book", "description": "Novel", "price": 10}).json()
        second = client.post("/products", json={"name": "Pen", "description": "Blue", "price": 1.5}).json()

        assert client.get("/products").status_code == 200
        assert dummy_cache.store

        response = client.post("/tasks/delete-products", json={"ids": [first["id"]]})
        assert response.status_code == 202
        assert dummy_cache.store == {}

        remaining = client.get("/products").json()
        assert [item["id"] for item in remaining] == [second["id"]]
