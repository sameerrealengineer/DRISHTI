"""M1 Definition of Done: seed loads 22 blocks with geometry, 4 gauges, shelters, teams, users."""

import json

import pytest
from sqlalchemy import func, select, text

from app import models as m
from app.config import get_settings
from app.security.crypto import decrypt_phone, mask_phone, phone_hash, verify_secret
from app.seed.loader import counts

SEED = get_settings().seed_dir


def test_counts(seeded_db):
    with seeded_db() as db:
        c = counts(db)
    shelters = len(json.loads((SEED / "shelters.json").read_text())["shelters"])
    teams = len(json.loads((SEED / "teams.json").read_text())["teams"])
    users = len(json.loads((SEED / "users.json").read_text())["users"])
    assert c == {
        "blocks": 22,
        "blocks_with_polygon": 22,
        "gauges": 4,
        "shelters": shelters,
        "teams": teams,
        "users": users,
        "scenarios": 3,
    }


def test_every_block_has_valid_polygon_containing_centroid(seeded_db):
    with seeded_db() as db:
        rows = db.execute(
            text(
                "SELECT code, ST_IsValid(geom), ST_Contains(geom, centroid), geometry_source FROM area WHERE kind='block'"
            )
        ).all()
    assert len(rows) == 22
    for code, valid, contains, source in rows:
        assert valid and contains, code
        assert source == "voronoi_approx"


def test_polygons_tile_the_district(seeded_db):
    with seeded_db() as db:
        blocks, district, overlap = db.execute(
            text(
                "SELECT (SELECT SUM(ST_Area(geom::geography)) FROM area WHERE kind='block'),"
                " (SELECT ST_Area(geom::geography) FROM district),"
                " (SELECT COALESCE(SUM(ST_Area(ST_Intersection(a.geom, b.geom)::geography)), 0)"
                "    FROM area a JOIN area b ON a.id < b.id AND ST_Overlaps(a.geom, b.geom))"
            )
        ).one()
    assert blocks == pytest.approx(district, rel=1e-3)
    assert overlap < 1e6  # < 1 km² total overlap (numerical slivers only)


def test_secrets_are_hashed(seeded_db):
    with seeded_db() as db:
        admin = db.scalar(select(m.AppUser).where(m.AppUser.email == "admin@drishti.local"))
        team = db.scalar(select(m.Team).where(m.Team.code == "ODRAF3"))
        citizen = db.scalar(select(m.AppUser).where(m.AppUser.role == "CITIZEN"))
        assert verify_secret("Drishti@2026", admin.password_hash)
        assert not verify_secret("wrong", admin.password_hash)
        assert verify_secret("1234", team.pin_hash)
        assert citizen.phone_hash == phone_hash("+91 90000 00002")
        assert decrypt_phone(citizen.phone_enc) == "+919000000002"
        assert "9000000002" not in (citizen.phone_enc or "")
    assert mask_phone("+919876543321") == "98xxxxx321"


def test_audit_log_is_append_only(seeded_db):
    with seeded_db() as db:
        db.add(m.AuditLog(at=func.now(), action="test", entity="test"))
        db.commit()
        with pytest.raises(Exception, match="append-only"):
            db.execute(text("UPDATE audit_log SET action='x'"))
        db.rollback()
        with pytest.raises(Exception, match="append-only"):
            db.execute(text("DELETE FROM audit_log"))
        db.rollback()


def test_risk_scores_materialized(client, seeded_db):
    with seeded_db() as db:
        n = db.scalar(select(func.count()).select_from(m.RiskScore))
    assert n == 22 * 49
