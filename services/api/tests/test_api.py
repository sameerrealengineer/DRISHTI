"""API smoke + sim controls (M0 /healthz, M2 sim.tick & risk.updated)."""


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_readyz(client):
    assert client.get("/readyz").json()["checks"]["db"] == "ok"


def test_openapi(client):
    assert client.get("/api/v1/openapi.json").status_code == 200


def test_error_envelope(client):
    r = client.get("/api/v1/areas/nowhere")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_areas_and_geojson(client):
    items = client.get("/api/v1/areas").json()["items"]
    assert len(items) == 22
    fc = client.get("/api/v1/areas/geojson").json()
    assert len(fc["features"]) == 22
    assert all(f["geometry"]["type"] == "MultiPolygon" for f in fc["features"])


def test_locate(client):
    r = client.get("/api/v1/areas/locate", params={"lat": 19.52, "lon": 84.89}).json()
    assert r["block"]["code"] == "purushottampur" and r["method"] == "contains"
    r = client.get("/api/v1/areas/locate", params={"lat": 18.0, "lon": 80.0}).json()
    assert r["method"] == "nearest_centroid"


def test_sim_seek_and_latest(client):
    s = client.post("/api/v1/sim/scenario", json={"key": "titli"}).json()
    assert s["t"] == -24 and not s["playing"]
    client.post("/api/v1/sim/seek", json={"t_hours": 0})
    latest = client.get("/api/v1/risk/latest").json()
    scores = {a["code"]: a["score"] for a in latest["areas"]}
    assert scores["purushottampur"] == 83
    assert latest["early_warning"]["state"] == "NOW"
    ex = client.get("/api/v1/risk/explain/purushottampur").json()
    assert ex["score"] == 83 and ex["drivers"] and "Purushottampur" in ex["text"]
    assert len(client.get("/api/v1/risk/district-curve").json()["points"]) == 49
    gauges = {g["code"]: g for g in client.get("/api/v1/gauges").json()["items"]}
    assert gauges["rushikulya_purushottampur"]["danger_level_m"] == 16.83


def test_sim_validation(client):
    assert client.post("/api/v1/sim/speed", json={"speed": 3}).status_code == 422
    assert client.post("/api/v1/sim/scenario", json={"key": "nope"}).status_code == 404


def test_phailin_switch(client):
    client.post("/api/v1/sim/scenario", json={"key": "phailin"})
    client.post("/api/v1/sim/seek", json={"t_hours": 0})
    scores = {a["code"]: a["score"] for a in client.get("/api/v1/risk/latest").json()["areas"]}
    assert scores["ganjam"] >= 95
    client.post("/api/v1/sim/scenario", json={"key": "titli"})


def test_ws_receives_tick_and_risk(client):
    client.post("/api/v1/sim/scenario", json={"key": "titli"})
    with client.websocket_connect("/api/v1/ws") as ws:
        first = ws.receive_json()
        assert first["type"] == "sim.tick"
        snap = ws.receive_json()
        assert snap["type"] == "risk.updated" and len(snap["data"]["areas"]) == 22
        client.post("/api/v1/sim/seek", json={"t_hours": -5})
        tick = ws.receive_json()
        assert tick["type"] == "sim.tick" and tick["data"]["t"] == -5
        upd = ws.receive_json()
        assert upd["type"] == "risk.updated"
        assert upd["data"]["early_warning"] == {
            "state": "WARNING",
            "area": "purushottampur",
            "name": "Purushottampur",
            "hours": 8,
        }
        assert 0 < len(upd["data"]["areas"]) <= 22


def test_sim_reset(client):
    client.post("/api/v1/sim/seek", json={"t_hours": 5})
    s = client.post("/api/v1/sim/reset").json()
    assert s["t"] == -24
