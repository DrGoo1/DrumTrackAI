from backend.drummerbrain.production_consolidation import build_sentient_runtime_config


def test_runtime_config_defaults():
    cfg = build_sentient_runtime_config()
    assert cfg["sentientFlags"]["sentient_enabled"] is True
    assert cfg["routing"]["defaultGenerateRoute"] == "/v1/render_sentient_take"
