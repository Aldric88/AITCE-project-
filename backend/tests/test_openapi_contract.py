from app.main import app


def test_critical_api_contract_paths_present():
    schema = app.openapi()
    paths = schema.get("paths", {})

    required = {
        "/notes/",
        "/notes/my",
        "/notes/my-uploads",
        "/purchase/my",
        "/purchases/my",
        "/library/my",
        "/purchase/{note_id}",
        "/purchases/{note_id}",
        "/purchase/has/{note_id}",
        "/purchases/has/{note_id}",
        "/payments/create-order",
        "/payments/verify",
        "/download/{note_id}",
        "/secure/session/start/{note_id}",
        "/secure/session/file/{note_id}",
        "/ops/health",
        "/ai/worker/health",
    }

    missing = sorted(required - set(paths.keys()))
    assert not missing, f"Missing critical API paths: {missing}"


def test_alias_contract_methods():
    schema = app.openapi()
    paths = schema.get("paths", {})

    assert "get" in paths["/purchase/my"]
    assert "get" in paths["/purchases/my"]
    assert "post" in paths["/purchase/{note_id}"]
    assert "post" in paths["/purchases/{note_id}"]
