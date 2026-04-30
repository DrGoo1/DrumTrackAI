from __future__ import annotations

from backend.drummerbrain.phrase_retrieval_sentient import retrieve_phrase_assets


class FakeCard:
    def __init__(self, **kwargs):
        self._data = kwargs

    def to_dict(self):
        return dict(self._data)


class FakeCatalog:
    def __init__(self, cards):
        self.cards = list(cards)

    def search(self, **kwargs):
        return list(self.cards)


def test_selects_ride_lead_groove_asset_from_catalog():
    cards = [
        FakeCard(
            id="egmd:rock_hats_01",
            source="egmd",
            title="Rock Hats",
            style_group="rock",
            tags=["rock", "hihat", "groove"],
            bars=2,
            tempo_bpm=118,
            default_role="groove",
            hat_hits_per_bar=8.0,
            ride_tip_hits_per_bar=0.0,
            ride_bell_hits_per_bar=0.0,
            complexity_tier="simple",
            complexity_score=0.32,
        ),
        FakeCard(
            id="egmd:rock_ride_09",
            source="egmd",
            title="Rock Ride Chorus",
            style_group="rock",
            tags=["rock", "ride", "chorus", "groove"],
            bars=2,
            tempo_bpm=120,
            default_role="groove",
            hat_hits_per_bar=0.0,
            ride_tip_hits_per_bar=6.0,
            ride_bell_hits_per_bar=2.0,
            complexity_tier="intermediate",
            complexity_score=0.58,
        ),
    ]

    out = retrieve_phrase_assets(
        phrase_selection={"grooveFamily": "ride_lead", "fillFamily": "linear_burst"},
        section_type="chorus",
        style_group="rock",
        timekeeper="ride",
        bars=2,
        energy=0.85,
        groove_catalog=FakeCatalog(cards),
    )

    assert out["selectedGrooveAsset"]["assetId"] == "egmd:rock_ride_09"
    assert out["selectedGrooveAsset"]["matchedFamily"] == "ride_lead"
    assert out["selectedFillAsset"]["assetId"] == "Nasty-Lick-34"
    assert out["selectedFillAsset"]["patternSteps"]


def test_fallback_groove_asset_when_no_catalog_available():
    out = retrieve_phrase_assets(
        phrase_selection={"grooveFamily": "pocket_backbeat", "fillFamily": "snare_pickup"},
        section_type="verse",
        style_group="rock",
        timekeeper="hats",
        bars=4,
        energy=0.5,
        groove_catalog=None,
    )

    assert out["selectedGrooveAsset"]["assetId"] == "family:pocket_backbeat"
    assert out["selectedFillAsset"]["assetId"] == "rudiment_midi:drag_tap"
    assert out["retrievalHints"]["timekeeper"] == "hats"
