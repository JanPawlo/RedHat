from app.const.card_templates import FIELD_SPECS
from tests.conftest import API_PREFIX

CARDS_URL = f"{API_PREFIX}/cards"


def test_cards_require_login(client):
    assert client.get(CARDS_URL).status_code == 401
    assert client.post(f"{CARDS_URL}/generate").status_code == 401


def test_generate_then_list_cards_within_limits(client, auth_headers):
    generated = client.post(f"{CARDS_URL}/generate", headers=auth_headers)
    assert generated.status_code == 200, generated.text
    assert "created" in generated.json()

    response = client.get(CARDS_URL, headers=auth_headers)
    assert response.status_code == 200, response.text
    for card in response.json():
        if not card.get("template"):
            continue
        assert len(card["title"]) <= FIELD_SPECS["title"]["max_chars"]
        assert len(card["proposal"]) <= FIELD_SPECS["proposal"]["max_chars"]
        assert len(card["back"]["description"]) <= FIELD_SPECS["explanation"]["max_chars"]
        assert card["rank"] and card["rankReason"]
