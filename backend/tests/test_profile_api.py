def test_get_profile_returns_404_when_none_exists(client):
    response = client.get("/profile")

    assert response.status_code == 404
    assert response.json() == {"detail": "Profile not found"}


def test_put_profile_creates_profile(client):
    response = client.put(
        "/profile",
        json={"full_name": "Jane Doe", "headline": "Python developer"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Jane Doe"
    assert body["headline"] == "Python developer"
    assert body["summary"] is None

    assert client.get("/profile").json()["full_name"] == "Jane Doe"


def test_put_profile_replaces_existing_profile(client):
    client.put("/profile", json={"full_name": "Jane Doe", "headline": "Old"})

    response = client.put("/profile", json={"full_name": "Jane Roe"})

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Jane Roe"
    assert body["headline"] is None


def test_put_profile_rejects_empty_name(client):
    response = client.put("/profile", json={"full_name": ""})

    assert response.status_code == 422