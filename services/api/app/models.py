"""Data model — PRD §14. PostgreSQL 16 + PostGIS, geometry SRID 4326.

IDs are bigint identity columns. Every table inherits id/created_at/updated_at.
Phone numbers are never stored raw: `*_hash` (SHA-256 + pepper) for lookup and
`*_enc` (AES-GCM) for sending.
"""

from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import TimestampedBase

POINT = Geometry("POINT", srid=4326, spatial_index=True)
MULTIPOLYGON = Geometry("MULTIPOLYGON", srid=4326, spatial_index=True)
POLYGON = Geometry("POLYGON", srid=4326, spatial_index=True)


def fk(target: str, nullable: bool = True, ondelete: str | None = "SET NULL") -> Any:
    if not nullable and ondelete == "SET NULL":
        ondelete = "CASCADE"
    return mapped_column(BigInteger, ForeignKey(target, ondelete=ondelete), nullable=nullable, index=True)


# ---------------------------------------------------------------- geography


class District(TimestampedBase):
    __tablename__ = "district"
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(32), unique=True)
    geom = mapped_column(MULTIPOLYGON, nullable=True)


class Area(TimestampedBase):
    """Block / GP / village. Blocks are the primary scoring unit."""

    __tablename__ = "area"
    district_id: Mapped[int] = fk("district.id", nullable=False)
    parent_id: Mapped[int | None] = fk("area.id")
    kind: Mapped[str] = mapped_column(String(16), index=True)  # block | gp | village
    name: Mapped[str] = mapped_column(String(120))
    name_or: Mapped[str | None] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    centroid = mapped_column(POINT, nullable=True)
    geom = mapped_column(MULTIPOLYGON, nullable=True)
    geometry_source: Mapped[str | None] = mapped_column(String(32))  # official | voronoi_approx
    elevation_m: Mapped[float | None] = mapped_column(Float)
    coast_km: Mapped[float | None] = mapped_column(Float)
    river: Mapped[str | None] = mapped_column(String(64))
    population: Mapped[int | None] = mapped_column(Integer)
    households: Mapped[int | None] = mapped_column(Integer)
    kutcha_share: Mapped[float | None] = mapped_column(Float)
    attrs_approx: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    aliases: Mapped[list["AreaAlias"]] = relationship(back_populates="area", cascade="all, delete-orphan")


class AreaAlias(TimestampedBase):
    __tablename__ = "area_alias"
    __table_args__ = (UniqueConstraint("alias", name="uq_area_alias_alias"),)
    area_id: Mapped[int] = fk("area.id", nullable=False)
    alias: Mapped[str] = mapped_column(String(120))  # stored lower-case
    area: Mapped[Area] = relationship(back_populates="aliases")


class Gauge(TimestampedBase):
    __tablename__ = "gauge"
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    river: Mapped[str] = mapped_column(String(64))
    site: Mapped[str] = mapped_column(String(120))
    area_id: Mapped[int | None] = fk("area.id")
    location = mapped_column(POINT, nullable=True)
    danger_level_m: Mapped[float] = mapped_column(Float)
    warning_level_m: Mapped[float | None] = mapped_column(Float)
    danger_level_sourced: Mapped[bool] = mapped_column(Boolean, default=False)


class GaugeReading(TimestampedBase):
    __tablename__ = "gauge_reading"
    __table_args__ = (Index("ix_gauge_reading_gauge_time", "gauge_id", "observed_at"),)
    gauge_id: Mapped[int] = fk("gauge.id", nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    level_m: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(16))  # manual | file | scraper | scenario
    entered_by: Mapped[int | None] = fk("app_user.id")


class WeatherObs(TimestampedBase):
    __tablename__ = "weather_obs"
    __table_args__ = (Index("ix_weather_area_time", "area_id", "valid_at"),)
    area_id: Mapped[int] = fk("area.id", nullable=False)
    valid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_forecast: Mapped[bool] = mapped_column(Boolean, default=False)
    precip_mm: Mapped[float | None] = mapped_column(Float)
    wind_kmh: Mapped[float | None] = mapped_column(Float)
    gust_kmh: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SatelliteObs(TimestampedBase):
    __tablename__ = "satellite_obs"
    __table_args__ = (Index("ix_satellite_area_time", "area_id", "scene_time"),)
    area_id: Mapped[int] = fk("area.id", nullable=False)
    scene_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    flood_fraction: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32))
    mask_uri: Mapped[str | None] = mapped_column(Text)


class Cyclone(TimestampedBase):
    __tablename__ = "cyclone"
    name: Mapped[str] = mapped_column(String(64))
    scenario_id: Mapped[int | None] = fk("scenario.id")
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class CycloneTrackPoint(TimestampedBase):
    __tablename__ = "cyclone_track_point"
    cyclone_id: Mapped[int] = fk("cyclone.id", nullable=False)
    valid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    location = mapped_column(POINT)
    vmax_kmh: Mapped[float] = mapped_column(Float)
    is_forecast: Mapped[bool] = mapped_column(Boolean, default=False)


class ExternalAlert(TimestampedBase):
    __tablename__ = "external_alert"
    source: Mapped[str] = mapped_column(String(16))  # SACHET | IMD
    identifier: Mapped[str] = mapped_column(String(200), unique=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    severity: Mapped[str | None] = mapped_column(String(32))
    headline: Mapped[str | None] = mapped_column(Text)
    areas_desc: Mapped[str | None] = mapped_column(Text)
    polygon = mapped_column(POLYGON, nullable=True)
    raw_xml: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------- risk


class RiskConfig(TimestampedBase):
    __tablename__ = "risk_config"
    version: Mapped[int] = mapped_column(Integer, unique=True)
    weights: Mapped[dict] = mapped_column(JSONB)
    thresholds: Mapped[dict] = mapped_column(JSONB)
    created_by: Mapped[int | None] = fk("app_user.id")
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class RiskScore(TimestampedBase):
    __tablename__ = "risk_score"
    __table_args__ = (
        UniqueConstraint("area_id", "at", "mode", "scenario_id", name="uq_risk_score_area_at"),
        Index("ix_risk_score_at", "at"),
    )
    area_id: Mapped[int] = fk("area.id", nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    score: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(16))
    hazard: Mapped[float] = mapped_column(Float)
    exposure: Mapped[float] = mapped_column(Float)
    vulnerability: Mapped[float] = mapped_column(Float)
    citizen: Mapped[float] = mapped_column(Float)
    components: Mapped[dict] = mapped_column(JSONB)
    drivers: Mapped[list[str]] = mapped_column(ARRAY(Text))
    contributions: Mapped[dict] = mapped_column(JSONB)
    forecast_max_12h: Mapped[int | None] = mapped_column(Integer)
    hours_to_severe: Mapped[int | None] = mapped_column(Integer)
    config_version: Mapped[int] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(8))  # live | demo
    scenario_id: Mapped[int | None] = fk("scenario.id")


# ---------------------------------------------------------------- reports


class Report(TimestampedBase):
    __tablename__ = "report"
    code: Mapped[str] = mapped_column(String(16), unique=True)  # R-xxxx
    channel: Mapped[str] = mapped_column(String(16))  # app | whatsapp | sms | field | scenario
    text: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(8))
    reporter_user_id: Mapped[int | None] = fk("app_user.id")
    reporter_phone_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    location = mapped_column(POINT, nullable=True)
    area_id: Mapped[int | None] = fk("area.id")
    declared_place: Mapped[str | None] = mapped_column(String(200))
    hazards: Mapped[list[str]] = mapped_column(ARRAY(String(16)), default=list)
    severity: Mapped[int | None] = mapped_column(Integer)
    needs: Mapped[list[str]] = mapped_column(ARRAY(String(16)), default=list)
    people_count: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float)
    photo_water_pct: Mapped[float | None] = mapped_column(Float)
    depth_band: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="NEW", index=True)
    parent_id: Mapped[int | None] = fk("report.id")
    verified_by: Mapped[int | None] = fk("app_user.id")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    scenario_id: Mapped[int | None] = fk("scenario.id")


class ReportMedia(TimestampedBase):
    __tablename__ = "report_media"
    report_id: Mapped[int] = fk("report.id", nullable=False)
    uri: Mapped[str] = mapped_column(Text)
    mime: Mapped[str] = mapped_column(String(64))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))


# ---------------------------------------------------------------- response


class Team(TimestampedBase):
    __tablename__ = "team"
    name: Mapped[str] = mapped_column(String(120))
    type: Mapped[str] = mapped_column(String(16))  # ODRAF | NDRF | Fire | Medical | Volunteer
    capabilities: Mapped[list[str]] = mapped_column(ARRAY(String(16)), default=list)
    members_count: Mapped[int] = mapped_column(Integer, default=0)
    base_location = mapped_column(POINT, nullable=True)
    base_area_id: Mapped[int | None] = fk("area.id")
    status: Mapped[str] = mapped_column(String(16), default="available")  # available | busy | offline
    current_location = mapped_column(POINT, nullable=True)
    last_ping_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    code: Mapped[str] = mapped_column(String(32), unique=True)
    pin_hash: Mapped[str | None] = mapped_column(String(255))


class Task(TimestampedBase):
    __tablename__ = "task"
    code: Mapped[str] = mapped_column(String(16), unique=True)  # GJM-xxxx
    source: Mapped[str] = mapped_column(String(8))  # SOS | REPORT | MANUAL
    report_id: Mapped[int | None] = fk("report.id")
    area_id: Mapped[int | None] = fk("area.id")
    location = mapped_column(POINT, nullable=True)
    place_text: Mapped[str | None] = mapped_column(String(200))
    people_count: Mapped[int] = mapped_column(Integer, default=1)
    need: Mapped[str] = mapped_column(String(24))
    requester_user_id: Mapped[int | None] = fk("app_user.id")
    requester_phone_enc: Mapped[str | None] = mapped_column(Text)
    requester_phone_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    unverified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="SENT", index=True)
    team_id: Mapped[int | None] = fk("team.id")
    eta_min: Mapped[int | None] = mapped_column(Integer)
    rescued_count: Mapped[int | None] = mapped_column(Integer)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    timeline: Mapped[list] = mapped_column(JSONB, default=list)


class TaskEvent(TimestampedBase):
    __tablename__ = "task_event"
    task_id: Mapped[int] = fk("task.id", nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16))
    actor_user_id: Mapped[int | None] = fk("app_user.id")
    actor_role: Mapped[str | None] = mapped_column(String(24))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)
    location = mapped_column(POINT, nullable=True)


class Shelter(TimestampedBase):
    __tablename__ = "shelter"
    code: Mapped[str] = mapped_column(String(48), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    type: Mapped[str] = mapped_column(String(16))  # MPCS | school | other
    area_id: Mapped[int | None] = fk("area.id")
    gp_name: Mapped[str | None] = mapped_column(String(120))
    location = mapped_column(POINT, nullable=True)
    capacity: Mapped[int] = mapped_column(Integer)
    occupancy: Mapped[int] = mapped_column(Integer, default=0)
    facilities: Mapped[list[str]] = mapped_column(ARRAY(String(24)), default=list)
    incharge_name: Mapped[str | None] = mapped_column(String(120))
    incharge_phone_enc: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="ready")  # ready | open | full | closed
    is_sample: Mapped[bool] = mapped_column(Boolean, default=True)


class ShelterOccupancy(TimestampedBase):
    __tablename__ = "shelter_occupancy"
    shelter_id: Mapped[int] = fk("shelter.id", nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    occupancy: Mapped[int] = mapped_column(Integer)
    delta: Mapped[int | None] = mapped_column(Integer)
    by_user_id: Mapped[int | None] = fk("app_user.id")


class ShelterNeed(TimestampedBase):
    __tablename__ = "shelter_need"
    shelter_id: Mapped[int] = fk("shelter.id", nullable=False)
    kind: Mapped[str] = mapped_column(String(16))  # food | water | medicine | bedding | power
    status: Mapped[str] = mapped_column(String(16), default="open")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatch_id: Mapped[int | None] = fk("dispatch.id")


class Alert(TimestampedBase):
    __tablename__ = "alert"
    code: Mapped[str] = mapped_column(String(32), unique=True)
    kind: Mapped[str] = mapped_column(String(16))  # risk | early | all_clear | do_not_return | custom
    level: Mapped[str | None] = mapped_column(String(16))
    area_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), default=list)
    polygon = mapped_column(MULTIPOLYGON, nullable=True)
    headline_en: Mapped[str | None] = mapped_column(Text)
    body_en: Mapped[str | None] = mapped_column(Text)
    headline_or: Mapped[str | None] = mapped_column(Text)
    body_or: Mapped[str | None] = mapped_column(Text)
    body_hi: Mapped[str | None] = mapped_column(Text)
    actions: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    status: Mapped[str] = mapped_column(String(16), default="DRAFT", index=True)
    drafted_by: Mapped[int | None] = fk("app_user.id")
    approved_by: Mapped[int | None] = fk("app_user.id")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    channels: Mapped[list[str]] = mapped_column(ARRAY(String(16)), default=list)
    audience_count: Mapped[int | None] = mapped_column(Integer)
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    cap_xml: Mapped[str | None] = mapped_column(Text)


class ResourcePool(TimestampedBase):
    __tablename__ = "resource_pool"
    __table_args__ = (UniqueConstraint("district_id", "kind", name="uq_resource_pool_kind"),)
    district_id: Mapped[int] = fk("district.id", nullable=False)
    kind: Mapped[str] = mapped_column(String(16))  # teams | boats | med | kits
    total: Mapped[int] = mapped_column(Integer)


class Allocation(TimestampedBase):
    __tablename__ = "allocation"
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    area_id: Mapped[int] = fk("area.id", nullable=False)
    kind: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[int] = mapped_column(Integer)
    evacuate_estimate: Mapped[int | None] = mapped_column(Integer)
    config_version: Mapped[int | None] = mapped_column(Integer)


class Dispatch(TimestampedBase):
    __tablename__ = "dispatch"
    allocation_id: Mapped[int | None] = fk("allocation.id")
    area_id: Mapped[int | None] = fk("area.id")
    shelter_id: Mapped[int | None] = fk("shelter.id")
    kind: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="ORDERED")  # ORDERED | IN_TRANSIT | DELIVERED
    ordered_by: Mapped[int | None] = fk("app_user.id")
    team_id: Mapped[int | None] = fk("team.id")
    timeline: Mapped[list] = mapped_column(JSONB, default=list)


# ---------------------------------------------------------------- people


class AppUser(TimestampedBase):
    __tablename__ = "app_user"
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(24), index=True)
    email: Mapped[str | None] = mapped_column(String(200), unique=True)
    phone_enc: Mapped[str | None] = mapped_column(Text)
    phone_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    area_id: Mapped[int | None] = fk("area.id")
    team_id: Mapped[int | None] = fk("team.id")
    language: Mapped[str] = mapped_column(String(4), default="or")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CitizenProfile(TimestampedBase):
    __tablename__ = "citizen_profile"
    user_id: Mapped[int] = fk("app_user.id", nullable=False)
    home_location = mapped_column(POINT, nullable=True)
    home_label: Mapped[str | None] = mapped_column(String(200))
    area_id: Mapped[int | None] = fk("area.id")
    fcm_token: Mapped[str | None] = mapped_column(Text)
    family_enc: Mapped[str | None] = mapped_column(Text)  # encrypted JSON list
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SafetyStatus(TimestampedBase):
    __tablename__ = "safety_status"
    user_id: Mapped[int | None] = fk("app_user.id")
    phone_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))  # safe | unknown | need_help
    shelter_id: Mapped[int | None] = fk("shelter.id")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    set_by: Mapped[int | None] = fk("app_user.id")


class Outbox(TimestampedBase):
    __tablename__ = "outbox"
    channel: Mapped[str] = mapped_column(String(16), index=True)
    to_hash: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    provider_id: Mapped[str | None] = mapped_column(String(120))
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(TimestampedBase):
    """Append-only. Never UPDATE or DELETE rows (enforced by trigger in migration)."""

    __tablename__ = "audit_log"
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(BigInteger)
    actor_role: Mapped[str | None] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(32), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(64))
    device: Mapped[str | None] = mapped_column(String(200))


# ---------------------------------------------------------------- demo / config


class Scenario(TimestampedBase):
    __tablename__ = "scenario"
    key: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    landfall_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text)
    data_uri: Mapped[str] = mapped_column(Text)


class SimState(TimestampedBase):
    __tablename__ = "sim_state"
    scenario_key: Mapped[str] = mapped_column(String(32))
    sim_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    playing: Mapped[bool] = mapped_column(Boolean, default=False)
    speed: Mapped[float] = mapped_column(Float, default=1.0)


class FeatureFlag(TimestampedBase):
    __tablename__ = "feature_flag"
    key: Mapped[str] = mapped_column(String(48), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)


class DataSource(TimestampedBase):
    """Adapter selection + freshness per source (BE-ING-7, BE-ADM-3)."""

    __tablename__ = "data_source"
    key: Mapped[str] = mapped_column(String(32), unique=True)  # weather | gauges | satellite | sachet
    adapter: Mapped[str] = mapped_column(String(16))  # live | file | scenario | manual
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
