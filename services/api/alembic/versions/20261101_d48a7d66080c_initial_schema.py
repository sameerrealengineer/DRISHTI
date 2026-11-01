"""initial schema

Revision ID: d48a7d66080c
Revises:
Create Date: 2026-11-01 14:05:53.026707

"""

from typing import Sequence, Union

import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d48a7d66080c"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AUDIT_GUARD = """
CREATE OR REPLACE FUNCTION audit_log_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER audit_log_no_update BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
"""


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "audit_log",
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_role", sa.String(length=24), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("before", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("device", sa.String(length=200), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_log_at"), "audit_log", ["at"], unique=False)
    op.create_index(op.f("ix_audit_log_entity"), "audit_log", ["entity"], unique=False)
    op.create_table(
        "data_source",
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("adapter", sa.String(length=16), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_geospatial_table(
        "district",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column(
            "geom",
            Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_geospatial_index(
        "idx_district_geom", "district", ["geom"], unique=False, postgresql_using="gist", postgresql_ops={}
    )
    op.create_geospatial_table(
        "external_alert",
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("identifier", sa.String(length=200), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("areas_desc", sa.Text(), nullable=True),
        sa.Column(
            "polygon",
            Geometry(
                geometry_type="POLYGON",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("raw_xml", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier"),
    )
    op.create_geospatial_index(
        "idx_external_alert_polygon",
        "external_alert",
        ["polygon"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_table(
        "feature_flag",
        sa.Column("key", sa.String(length=48), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "outbox",
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("to_hash", sa.String(length=64), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider_id", sa.String(length=120), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outbox_channel"), "outbox", ["channel"], unique=False)
    op.create_table(
        "scenario",
        sa.Column("key", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("landfall_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data_uri", sa.Text(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "sim_state",
        sa.Column("scenario_key", sa.String(length=32), nullable=False),
        sa.Column("sim_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("playing", sa.Boolean(), nullable=False),
        sa.Column("speed", sa.Float(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_geospatial_table(
        "area",
        sa.Column("district_id", sa.BigInteger(), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_or", sa.String(length=120), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column(
            "centroid",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "geom",
            Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("geometry_source", sa.String(length=32), nullable=True),
        sa.Column("elevation_m", sa.Float(), nullable=True),
        sa.Column("coast_km", sa.Float(), nullable=True),
        sa.Column("river", sa.String(length=64), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("households", sa.Integer(), nullable=True),
        sa.Column("kutcha_share", sa.Float(), nullable=True),
        sa.Column("attrs_approx", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["district_id"], ["district.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["area.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_geospatial_index(
        "idx_area_centroid", "area", ["centroid"], unique=False, postgresql_using="gist", postgresql_ops={}
    )
    op.create_geospatial_index(
        "idx_area_geom", "area", ["geom"], unique=False, postgresql_using="gist", postgresql_ops={}
    )
    op.create_index(op.f("ix_area_district_id"), "area", ["district_id"], unique=False)
    op.create_index(op.f("ix_area_kind"), "area", ["kind"], unique=False)
    op.create_index(op.f("ix_area_parent_id"), "area", ["parent_id"], unique=False)
    op.create_table(
        "cyclone",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("scenario_id", sa.BigInteger(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenario.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cyclone_scenario_id"), "cyclone", ["scenario_id"], unique=False)
    op.create_table(
        "resource_pool",
        sa.Column("district_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["district_id"], ["district.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("district_id", "kind", name="uq_resource_pool_kind"),
    )
    op.create_index(op.f("ix_resource_pool_district_id"), "resource_pool", ["district_id"], unique=False)
    op.create_table(
        "allocation",
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("area_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("evacuate_estimate", sa.Integer(), nullable=True),
        sa.Column("config_version", sa.Integer(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_allocation_area_id"), "allocation", ["area_id"], unique=False)
    op.create_index(op.f("ix_allocation_at"), "allocation", ["at"], unique=False)
    op.create_table(
        "area_alias",
        sa.Column("area_id", sa.BigInteger(), nullable=False),
        sa.Column("alias", sa.String(length=120), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias", name="uq_area_alias_alias"),
    )
    op.create_index(op.f("ix_area_alias_area_id"), "area_alias", ["area_id"], unique=False)
    op.create_geospatial_table(
        "cyclone_track_point",
        sa.Column("cyclone_id", sa.BigInteger(), nullable=False),
        sa.Column("valid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("vmax_kmh", sa.Float(), nullable=False),
        sa.Column("is_forecast", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cyclone_id"], ["cyclone.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_geospatial_index(
        "idx_cyclone_track_point_location",
        "cyclone_track_point",
        ["location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(
        op.f("ix_cyclone_track_point_cyclone_id"), "cyclone_track_point", ["cyclone_id"], unique=False
    )
    op.create_index(
        op.f("ix_cyclone_track_point_valid_at"), "cyclone_track_point", ["valid_at"], unique=False
    )
    op.create_geospatial_table(
        "gauge",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("river", sa.String(length=64), nullable=False),
        sa.Column("site", sa.String(length=120), nullable=False),
        sa.Column("area_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("danger_level_m", sa.Float(), nullable=False),
        sa.Column("warning_level_m", sa.Float(), nullable=True),
        sa.Column("danger_level_sourced", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_geospatial_index(
        "idx_gauge_location", "gauge", ["location"], unique=False, postgresql_using="gist", postgresql_ops={}
    )
    op.create_index(op.f("ix_gauge_area_id"), "gauge", ["area_id"], unique=False)
    op.create_table(
        "risk_score",
        sa.Column("area_id", sa.BigInteger(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("hazard", sa.Float(), nullable=False),
        sa.Column("exposure", sa.Float(), nullable=False),
        sa.Column("vulnerability", sa.Float(), nullable=False),
        sa.Column("citizen", sa.Float(), nullable=False),
        sa.Column("components", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("drivers", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("contributions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("forecast_max_12h", sa.Integer(), nullable=True),
        sa.Column("hours_to_severe", sa.Integer(), nullable=True),
        sa.Column("config_version", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("scenario_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenario.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("area_id", "at", "mode", "scenario_id", name="uq_risk_score_area_at"),
    )
    op.create_index(op.f("ix_risk_score_area_id"), "risk_score", ["area_id"], unique=False)
    op.create_index("ix_risk_score_at", "risk_score", ["at"], unique=False)
    op.create_index(op.f("ix_risk_score_scenario_id"), "risk_score", ["scenario_id"], unique=False)
    op.create_table(
        "satellite_obs",
        sa.Column("area_id", sa.BigInteger(), nullable=False),
        sa.Column("scene_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("flood_fraction", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("mask_uri", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_satellite_area_time", "satellite_obs", ["area_id", "scene_time"], unique=False)
    op.create_index(op.f("ix_satellite_obs_area_id"), "satellite_obs", ["area_id"], unique=False)
    op.create_geospatial_table(
        "shelter",
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("area_id", sa.BigInteger(), nullable=True),
        sa.Column("gp_name", sa.String(length=120), nullable=True),
        sa.Column(
            "location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("occupancy", sa.Integer(), nullable=False),
        sa.Column("facilities", sa.ARRAY(sa.String(length=24)), nullable=False),
        sa.Column("incharge_name", sa.String(length=120), nullable=True),
        sa.Column("incharge_phone_enc", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("is_sample", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_geospatial_index(
        "idx_shelter_location",
        "shelter",
        ["location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(op.f("ix_shelter_area_id"), "shelter", ["area_id"], unique=False)
    op.create_geospatial_table(
        "team",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("capabilities", sa.ARRAY(sa.String(length=16)), nullable=False),
        sa.Column("members_count", sa.Integer(), nullable=False),
        sa.Column(
            "base_location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("base_area_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "current_location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("last_ping_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("pin_hash", sa.String(length=255), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["base_area_id"], ["area.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_geospatial_index(
        "idx_team_base_location",
        "team",
        ["base_location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_geospatial_index(
        "idx_team_current_location",
        "team",
        ["current_location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(op.f("ix_team_base_area_id"), "team", ["base_area_id"], unique=False)
    op.create_table(
        "weather_obs",
        sa.Column("area_id", sa.BigInteger(), nullable=False),
        sa.Column("valid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_forecast", sa.Boolean(), nullable=False),
        sa.Column("precip_mm", sa.Float(), nullable=True),
        sa.Column("wind_kmh", sa.Float(), nullable=True),
        sa.Column("gust_kmh", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weather_area_time", "weather_obs", ["area_id", "valid_at"], unique=False)
    op.create_index(op.f("ix_weather_obs_area_id"), "weather_obs", ["area_id"], unique=False)
    op.create_table(
        "app_user",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("phone_enc", sa.Text(), nullable=True),
        sa.Column("phone_hash", sa.String(length=64), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("area_id", sa.BigInteger(), nullable=True),
        sa.Column("team_id", sa.BigInteger(), nullable=True),
        sa.Column("language", sa.String(length=4), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone_hash"),
    )
    op.create_index(op.f("ix_app_user_area_id"), "app_user", ["area_id"], unique=False)
    op.create_index(op.f("ix_app_user_role"), "app_user", ["role"], unique=False)
    op.create_index(op.f("ix_app_user_team_id"), "app_user", ["team_id"], unique=False)
    op.create_geospatial_table(
        "alert",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=True),
        sa.Column("area_ids", sa.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column(
            "polygon",
            Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("headline_en", sa.Text(), nullable=True),
        sa.Column("body_en", sa.Text(), nullable=True),
        sa.Column("headline_or", sa.Text(), nullable=True),
        sa.Column("body_or", sa.Text(), nullable=True),
        sa.Column("body_hi", sa.Text(), nullable=True),
        sa.Column("actions", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("drafted_by", sa.BigInteger(), nullable=True),
        sa.Column("approved_by", sa.BigInteger(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("channels", sa.ARRAY(sa.String(length=16)), nullable=False),
        sa.Column("audience_count", sa.Integer(), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cap_xml", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["app_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["drafted_by"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_geospatial_index(
        "idx_alert_polygon", "alert", ["polygon"], unique=False, postgresql_using="gist", postgresql_ops={}
    )
    op.create_index(op.f("ix_alert_approved_by"), "alert", ["approved_by"], unique=False)
    op.create_index(op.f("ix_alert_drafted_by"), "alert", ["drafted_by"], unique=False)
    op.create_index(op.f("ix_alert_status"), "alert", ["status"], unique=False)
    op.create_geospatial_table(
        "citizen_profile",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "home_location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("home_label", sa.String(length=200), nullable=True),
        sa.Column("area_id", sa.BigInteger(), nullable=True),
        sa.Column("fcm_token", sa.Text(), nullable=True),
        sa.Column("family_enc", sa.Text(), nullable=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_geospatial_index(
        "idx_citizen_profile_home_location",
        "citizen_profile",
        ["home_location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(op.f("ix_citizen_profile_area_id"), "citizen_profile", ["area_id"], unique=False)
    op.create_index(op.f("ix_citizen_profile_user_id"), "citizen_profile", ["user_id"], unique=False)
    op.create_table(
        "dispatch",
        sa.Column("allocation_id", sa.BigInteger(), nullable=True),
        sa.Column("area_id", sa.BigInteger(), nullable=True),
        sa.Column("shelter_id", sa.BigInteger(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("ordered_by", sa.BigInteger(), nullable=True),
        sa.Column("team_id", sa.BigInteger(), nullable=True),
        sa.Column("timeline", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocation.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ordered_by"], ["app_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shelter_id"], ["shelter.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dispatch_allocation_id"), "dispatch", ["allocation_id"], unique=False)
    op.create_index(op.f("ix_dispatch_area_id"), "dispatch", ["area_id"], unique=False)
    op.create_index(op.f("ix_dispatch_ordered_by"), "dispatch", ["ordered_by"], unique=False)
    op.create_index(op.f("ix_dispatch_shelter_id"), "dispatch", ["shelter_id"], unique=False)
    op.create_index(op.f("ix_dispatch_team_id"), "dispatch", ["team_id"], unique=False)
    op.create_table(
        "gauge_reading",
        sa.Column("gauge_id", sa.BigInteger(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level_m", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("entered_by", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["entered_by"], ["app_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gauge_id"], ["gauge.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gauge_reading_entered_by"), "gauge_reading", ["entered_by"], unique=False)
    op.create_index(op.f("ix_gauge_reading_gauge_id"), "gauge_reading", ["gauge_id"], unique=False)
    op.create_index("ix_gauge_reading_gauge_time", "gauge_reading", ["gauge_id", "observed_at"], unique=False)
    op.create_geospatial_table(
        "report",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("reporter_user_id", sa.BigInteger(), nullable=True),
        sa.Column("reporter_phone_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("area_id", sa.BigInteger(), nullable=True),
        sa.Column("declared_place", sa.String(length=200), nullable=True),
        sa.Column("hazards", sa.ARRAY(sa.String(length=16)), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=True),
        sa.Column("needs", sa.ARRAY(sa.String(length=16)), nullable=False),
        sa.Column("people_count", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("photo_water_pct", sa.Float(), nullable=True),
        sa.Column("depth_band", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("verified_by", sa.BigInteger(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scenario_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_id"], ["report.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenario.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["verified_by"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_geospatial_index(
        "idx_report_location",
        "report",
        ["location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(op.f("ix_report_area_id"), "report", ["area_id"], unique=False)
    op.create_index(op.f("ix_report_parent_id"), "report", ["parent_id"], unique=False)
    op.create_index(op.f("ix_report_reported_at"), "report", ["reported_at"], unique=False)
    op.create_index(op.f("ix_report_reporter_phone_hash"), "report", ["reporter_phone_hash"], unique=False)
    op.create_index(op.f("ix_report_reporter_user_id"), "report", ["reporter_user_id"], unique=False)
    op.create_index(op.f("ix_report_scenario_id"), "report", ["scenario_id"], unique=False)
    op.create_index(op.f("ix_report_status"), "report", ["status"], unique=False)
    op.create_index(op.f("ix_report_verified_by"), "report", ["verified_by"], unique=False)
    op.create_table(
        "risk_config",
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("thresholds", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version"),
    )
    op.create_index(op.f("ix_risk_config_created_by"), "risk_config", ["created_by"], unique=False)
    op.create_table(
        "safety_status",
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("phone_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("shelter_id", sa.BigInteger(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("set_by", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["set_by"], ["app_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shelter_id"], ["shelter.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_safety_status_phone_hash"), "safety_status", ["phone_hash"], unique=False)
    op.create_index(op.f("ix_safety_status_set_by"), "safety_status", ["set_by"], unique=False)
    op.create_index(op.f("ix_safety_status_shelter_id"), "safety_status", ["shelter_id"], unique=False)
    op.create_index(op.f("ix_safety_status_user_id"), "safety_status", ["user_id"], unique=False)
    op.create_table(
        "shelter_occupancy",
        sa.Column("shelter_id", sa.BigInteger(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occupancy", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=True),
        sa.Column("by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["by_user_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shelter_id"], ["shelter.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_shelter_occupancy_by_user_id"), "shelter_occupancy", ["by_user_id"], unique=False
    )
    op.create_index(
        op.f("ix_shelter_occupancy_shelter_id"), "shelter_occupancy", ["shelter_id"], unique=False
    )
    op.create_table(
        "report_media",
        sa.Column("report_id", sa.BigInteger(), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("mime", sa.String(length=64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["report.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_media_report_id"), "report_media", ["report_id"], unique=False)
    op.create_table(
        "shelter_need",
        sa.Column("shelter_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatch_id", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dispatch_id"], ["dispatch.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shelter_id"], ["shelter.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shelter_need_dispatch_id"), "shelter_need", ["dispatch_id"], unique=False)
    op.create_index(op.f("ix_shelter_need_shelter_id"), "shelter_need", ["shelter_id"], unique=False)
    op.create_geospatial_table(
        "task",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column("report_id", sa.BigInteger(), nullable=True),
        sa.Column("area_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("place_text", sa.String(length=200), nullable=True),
        sa.Column("people_count", sa.Integer(), nullable=False),
        sa.Column("need", sa.String(length=24), nullable=False),
        sa.Column("requester_user_id", sa.BigInteger(), nullable=True),
        sa.Column("requester_phone_enc", sa.Text(), nullable=True),
        sa.Column("requester_phone_hash", sa.String(length=64), nullable=True),
        sa.Column("unverified", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("team_id", sa.BigInteger(), nullable=True),
        sa.Column("eta_min", sa.Integer(), nullable=True),
        sa.Column("rescued_count", sa.Integer(), nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=False),
        sa.Column("timeline", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["area.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["report_id"], ["report.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requester_user_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["team.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_geospatial_index(
        "idx_task_location", "task", ["location"], unique=False, postgresql_using="gist", postgresql_ops={}
    )
    op.create_index(op.f("ix_task_area_id"), "task", ["area_id"], unique=False)
    op.create_index(op.f("ix_task_report_id"), "task", ["report_id"], unique=False)
    op.create_index(op.f("ix_task_requester_phone_hash"), "task", ["requester_phone_hash"], unique=False)
    op.create_index(op.f("ix_task_requester_user_id"), "task", ["requester_user_id"], unique=False)
    op.create_index(op.f("ix_task_status"), "task", ["status"], unique=False)
    op.create_index(op.f("ix_task_team_id"), "task", ["team_id"], unique=False)
    op.create_geospatial_table(
        "task_event",
        sa.Column("task_id", sa.BigInteger(), nullable=False),
        sa.Column("from_status", sa.String(length=16), nullable=True),
        sa.Column("to_status", sa.String(length=16), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_role", sa.String(length=24), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_geospatial_index(
        "idx_task_event_location",
        "task_event",
        ["location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(op.f("ix_task_event_actor_user_id"), "task_event", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_task_event_task_id"), "task_event", ["task_id"], unique=False)
    # ### end Alembic commands ###

    op.execute(AUDIT_GUARD)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_append_only()")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_task_event_task_id"), table_name="task_event")
    op.drop_index(op.f("ix_task_event_actor_user_id"), table_name="task_event")
    op.drop_geospatial_index(
        "idx_task_event_location", table_name="task_event", postgresql_using="gist", column_name="location"
    )
    op.drop_geospatial_table("task_event")
    op.drop_index(op.f("ix_task_team_id"), table_name="task")
    op.drop_index(op.f("ix_task_status"), table_name="task")
    op.drop_index(op.f("ix_task_requester_user_id"), table_name="task")
    op.drop_index(op.f("ix_task_requester_phone_hash"), table_name="task")
    op.drop_index(op.f("ix_task_report_id"), table_name="task")
    op.drop_index(op.f("ix_task_area_id"), table_name="task")
    op.drop_geospatial_index(
        "idx_task_location", table_name="task", postgresql_using="gist", column_name="location"
    )
    op.drop_geospatial_table("task")
    op.drop_index(op.f("ix_shelter_need_shelter_id"), table_name="shelter_need")
    op.drop_index(op.f("ix_shelter_need_dispatch_id"), table_name="shelter_need")
    op.drop_table("shelter_need")
    op.drop_index(op.f("ix_report_media_report_id"), table_name="report_media")
    op.drop_table("report_media")
    op.drop_index(op.f("ix_shelter_occupancy_shelter_id"), table_name="shelter_occupancy")
    op.drop_index(op.f("ix_shelter_occupancy_by_user_id"), table_name="shelter_occupancy")
    op.drop_table("shelter_occupancy")
    op.drop_index(op.f("ix_safety_status_user_id"), table_name="safety_status")
    op.drop_index(op.f("ix_safety_status_shelter_id"), table_name="safety_status")
    op.drop_index(op.f("ix_safety_status_set_by"), table_name="safety_status")
    op.drop_index(op.f("ix_safety_status_phone_hash"), table_name="safety_status")
    op.drop_table("safety_status")
    op.drop_index(op.f("ix_risk_config_created_by"), table_name="risk_config")
    op.drop_table("risk_config")
    op.drop_index(op.f("ix_report_verified_by"), table_name="report")
    op.drop_index(op.f("ix_report_status"), table_name="report")
    op.drop_index(op.f("ix_report_scenario_id"), table_name="report")
    op.drop_index(op.f("ix_report_reporter_user_id"), table_name="report")
    op.drop_index(op.f("ix_report_reporter_phone_hash"), table_name="report")
    op.drop_index(op.f("ix_report_reported_at"), table_name="report")
    op.drop_index(op.f("ix_report_parent_id"), table_name="report")
    op.drop_index(op.f("ix_report_area_id"), table_name="report")
    op.drop_geospatial_index(
        "idx_report_location", table_name="report", postgresql_using="gist", column_name="location"
    )
    op.drop_geospatial_table("report")
    op.drop_index("ix_gauge_reading_gauge_time", table_name="gauge_reading")
    op.drop_index(op.f("ix_gauge_reading_gauge_id"), table_name="gauge_reading")
    op.drop_index(op.f("ix_gauge_reading_entered_by"), table_name="gauge_reading")
    op.drop_table("gauge_reading")
    op.drop_index(op.f("ix_dispatch_team_id"), table_name="dispatch")
    op.drop_index(op.f("ix_dispatch_shelter_id"), table_name="dispatch")
    op.drop_index(op.f("ix_dispatch_ordered_by"), table_name="dispatch")
    op.drop_index(op.f("ix_dispatch_area_id"), table_name="dispatch")
    op.drop_index(op.f("ix_dispatch_allocation_id"), table_name="dispatch")
    op.drop_table("dispatch")
    op.drop_index(op.f("ix_citizen_profile_user_id"), table_name="citizen_profile")
    op.drop_index(op.f("ix_citizen_profile_area_id"), table_name="citizen_profile")
    op.drop_geospatial_index(
        "idx_citizen_profile_home_location",
        table_name="citizen_profile",
        postgresql_using="gist",
        column_name="home_location",
    )
    op.drop_geospatial_table("citizen_profile")
    op.drop_index(op.f("ix_alert_status"), table_name="alert")
    op.drop_index(op.f("ix_alert_drafted_by"), table_name="alert")
    op.drop_index(op.f("ix_alert_approved_by"), table_name="alert")
    op.drop_geospatial_index(
        "idx_alert_polygon", table_name="alert", postgresql_using="gist", column_name="polygon"
    )
    op.drop_geospatial_table("alert")
    op.drop_index(op.f("ix_app_user_team_id"), table_name="app_user")
    op.drop_index(op.f("ix_app_user_role"), table_name="app_user")
    op.drop_index(op.f("ix_app_user_area_id"), table_name="app_user")
    op.drop_table("app_user")
    op.drop_index(op.f("ix_weather_obs_area_id"), table_name="weather_obs")
    op.drop_index("ix_weather_area_time", table_name="weather_obs")
    op.drop_table("weather_obs")
    op.drop_index(op.f("ix_team_base_area_id"), table_name="team")
    op.drop_geospatial_index(
        "idx_team_current_location",
        table_name="team",
        postgresql_using="gist",
        column_name="current_location",
    )
    op.drop_geospatial_index(
        "idx_team_base_location", table_name="team", postgresql_using="gist", column_name="base_location"
    )
    op.drop_geospatial_table("team")
    op.drop_index(op.f("ix_shelter_area_id"), table_name="shelter")
    op.drop_geospatial_index(
        "idx_shelter_location", table_name="shelter", postgresql_using="gist", column_name="location"
    )
    op.drop_geospatial_table("shelter")
    op.drop_index(op.f("ix_satellite_obs_area_id"), table_name="satellite_obs")
    op.drop_index("ix_satellite_area_time", table_name="satellite_obs")
    op.drop_table("satellite_obs")
    op.drop_index(op.f("ix_risk_score_scenario_id"), table_name="risk_score")
    op.drop_index("ix_risk_score_at", table_name="risk_score")
    op.drop_index(op.f("ix_risk_score_area_id"), table_name="risk_score")
    op.drop_table("risk_score")
    op.drop_index(op.f("ix_gauge_area_id"), table_name="gauge")
    op.drop_geospatial_index(
        "idx_gauge_location", table_name="gauge", postgresql_using="gist", column_name="location"
    )
    op.drop_geospatial_table("gauge")
    op.drop_index(op.f("ix_cyclone_track_point_valid_at"), table_name="cyclone_track_point")
    op.drop_index(op.f("ix_cyclone_track_point_cyclone_id"), table_name="cyclone_track_point")
    op.drop_geospatial_index(
        "idx_cyclone_track_point_location",
        table_name="cyclone_track_point",
        postgresql_using="gist",
        column_name="location",
    )
    op.drop_geospatial_table("cyclone_track_point")
    op.drop_index(op.f("ix_area_alias_area_id"), table_name="area_alias")
    op.drop_table("area_alias")
    op.drop_index(op.f("ix_allocation_at"), table_name="allocation")
    op.drop_index(op.f("ix_allocation_area_id"), table_name="allocation")
    op.drop_table("allocation")
    op.drop_index(op.f("ix_resource_pool_district_id"), table_name="resource_pool")
    op.drop_table("resource_pool")
    op.drop_index(op.f("ix_cyclone_scenario_id"), table_name="cyclone")
    op.drop_table("cyclone")
    op.drop_index(op.f("ix_area_parent_id"), table_name="area")
    op.drop_index(op.f("ix_area_kind"), table_name="area")
    op.drop_index(op.f("ix_area_district_id"), table_name="area")
    op.drop_geospatial_index("idx_area_geom", table_name="area", postgresql_using="gist", column_name="geom")
    op.drop_geospatial_index(
        "idx_area_centroid", table_name="area", postgresql_using="gist", column_name="centroid"
    )
    op.drop_geospatial_table("area")
    op.drop_table("sim_state")
    op.drop_table("scenario")
    op.drop_index(op.f("ix_outbox_channel"), table_name="outbox")
    op.drop_table("outbox")
    op.drop_table("feature_flag")
    op.drop_geospatial_index(
        "idx_external_alert_polygon",
        table_name="external_alert",
        postgresql_using="gist",
        column_name="polygon",
    )
    op.drop_geospatial_table("external_alert")
    op.drop_geospatial_index(
        "idx_district_geom", table_name="district", postgresql_using="gist", column_name="geom"
    )
    op.drop_geospatial_table("district")
    op.drop_table("data_source")
    op.drop_index(op.f("ix_audit_log_entity"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_at"), table_name="audit_log")
    op.drop_table("audit_log")
    # ### end Alembic commands ###
