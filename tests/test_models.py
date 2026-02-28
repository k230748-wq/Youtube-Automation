"""Basic model tests."""

import pytest
from app import create_app, db


@pytest.fixture
def app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_create_channel(client):
    response = client.post("/api/channels/", json={"name": "Test Channel", "niche": "technology"})
    assert response.status_code == 201
    assert response.json["name"] == "Test Channel"


def test_list_channels(client):
    client.post("/api/channels/", json={"name": "Ch1", "niche": "tech"})
    response = client.get("/api/channels/")
    assert response.status_code == 200
    assert len(response.json["channels"]) == 1
