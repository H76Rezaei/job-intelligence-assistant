import pytest
from sqlalchemy import func, select

from app.models.job_posting_snapshot import JobPostingSnapshot

PASTED = {
    "title": "Python Developer (m/w/d)",
    "company_name": "Example Software GmbH",
    "url": "https://jobs.example.com/python-developer",
    "description": "We build things in Python.",
    "location": "Frankfurt am Main",
    "work_mode": "hybrid",
}


def test_paste_creates_job_with_snapshot_and_source(client):
    response = client.post("/jobs", json=PASTED)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Python Developer (m/w/d)"
    assert body["company"]["name"] == "Example Software GmbH"
    assert body["location"] == "Frankfurt am Main"
    assert body["work_mode"] == "hybrid"
    assert body["description"] == "We build things in Python."
    assert [s["source"] for s in body["sources"]] == ["paste"]
    assert body["sources"][0]["url"] == "https://jobs.example.com/python-developer"

    detail = client.get(f"/jobs/{body['id']}").json()
    assert detail["description"] == "We build things in Python."
    assert [s["source"] for s in detail["sources"]] == ["paste"]


def test_paste_matches_existing_job_across_title_variants_legal_forms_and_cities(client):
    first = client.post("/jobs", json=PASTED).json()

    response = client.post(
        "/jobs",
        json={
            **PASTED,
            "title": "python developer (w/m/d)",
            "company_name": "Example Software",
            "url": "https://careers.example.com/12345",
            "location": "Berlin",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == first["id"]
    assert body["title"] == "Python Developer (m/w/d)"
    assert body["company"]["name"] == "Example Software GmbH"
    assert [s["url"] for s in body["sources"]] == [
        "https://jobs.example.com/python-developer",
        "https://careers.example.com/12345",
    ]
    assert len(client.get("/jobs").json()) == 1


def test_paste_with_different_title_is_a_different_job(client):
    first = client.post("/jobs", json=PASTED).json()

    response = client.post(
        "/jobs",
        json={**PASTED, "title": "Senior Python Developer (m/w/d)", "url": "https://jobs.example.com/senior"},
    )

    assert response.status_code == 201
    assert response.json()["id"] != first["id"]
    assert response.json()["company"]["id"] == first["company"]["id"]


def _snapshot_count(session, job_id):
    return session.scalar(
        select(func.count()).where(JobPostingSnapshot.job_posting_id == job_id)
    )


def test_repasting_the_same_text_adds_no_snapshot_or_source(client, session):
    first = client.post("/jobs", json=PASTED).json()

    response = client.post(
        "/jobs",
        json={**PASTED, "url": "https://JOBS.example.com/python-developer/?utm_source=x"},
    )

    assert response.status_code == 200
    assert len(response.json()["sources"]) == 1
    assert _snapshot_count(session, first["id"]) == 1


def test_repasting_changed_text_shows_new_text_and_keeps_applications_pinned(client, session):
    first = client.post("/jobs", json=PASTED).json()
    application = client.post("/applications", json={"job_posting_id": first["id"]}).json()

    response = client.post("/jobs", json={**PASTED, "description": "Now with FastAPI."})

    assert response.json()["description"] == "Now with FastAPI."
    assert _snapshot_count(session, first["id"]) == 2
    pinned = client.get(f"/applications/{application['id']}").json()
    assert pinned["snapshot_id"] == application["snapshot_id"]


def test_paste_requires_title_company_url_and_text(client):
    for field in ["title", "company_name", "url", "description"]:
        body = {k: v for k, v in PASTED.items() if k != field}
        assert client.post("/jobs", json=body).status_code == 422, field

    assert client.post("/jobs", json={**PASTED, "url": "not a url"}).status_code == 422
    assert client.get("/jobs").json() == []


@pytest.mark.parametrize(
    "title",
    [
        "Python Developer (w/m/d)",
        "Python Developer (m/f/d)",
        "Python Developer (all genders)",
        "Python Developer (m/w/divers)",
        "Python Developer m/w/d",
        "PYTHON  developer",
    ],
)
def test_gender_tags_and_spacing_do_not_make_a_new_job(client, title):
    first = client.post("/jobs", json=PASTED).json()

    response = client.post("/jobs", json={**PASTED, "title": title, "url": "https://x.example/1"})

    assert response.status_code == 200
    assert response.json()["id"] == first["id"]


@pytest.mark.parametrize(
    "company",
    [
        "Example Software",
        "Example Software AG",
        "Example Software SE",
        "Example Software GmbH & Co. KG",
        "Example Software GmbH & Co.KG",
        "Example Software SE & Co. KGaA",
        "Example Software e.V.",
        "Example Software UG (haftungsbeschränkt)",
        "example software, gmbh",
    ],
)
def test_legal_forms_do_not_make_a_new_company(client, company):
    first = client.post("/jobs", json=PASTED).json()

    response = client.post(
        "/jobs", json={**PASTED, "company_name": company, "url": "https://x.example/1"}
    )

    assert response.status_code == 200
    assert response.json()["id"] == first["id"]


@pytest.mark.parametrize(
    ("first_title", "second_title"),
    [
        ("Campaign Manager", "Campai Manager"),
        ("Designer (m/w/d)", "Desi er"),
        ("Backend/Frontend Developer", "Backen rontend Developer"),
    ],
)
def test_words_that_look_like_tags_are_kept(client, first_title, second_title):
    client.post("/jobs", json={**PASTED, "title": first_title})

    response = client.post(
        "/jobs", json={**PASTED, "title": second_title, "url": "https://x.example/1"}
    )

    assert response.status_code == 201


@pytest.mark.parametrize(
    ("first_company", "second_company"),
    [("Tesla", "Tesla EV"), ("Example Software", "Example Software EG")],
)
def test_words_that_look_like_legal_forms_are_kept(client, first_company, second_company):
    client.post("/jobs", json={**PASTED, "company_name": first_company})

    response = client.post(
        "/jobs", json={**PASTED, "company_name": second_company, "url": "https://x.example/1"}
    )

    assert response.status_code == 201
    assert response.json()["company"]["name"] == second_company


def test_query_parameters_that_identify_a_posting_are_kept(client):
    first = client.post("/jobs", json={**PASTED, "url": "https://board.example/view?ref=111"}).json()

    response = client.post(
        "/jobs", json={**PASTED, "url": "https://board.example/view?ref=222"}
    )

    assert len(response.json()["sources"]) == 2
    assert response.json()["id"] == first["id"]
