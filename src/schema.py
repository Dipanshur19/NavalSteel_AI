"""
Scientific data model for NavalSteel AI material records.

This mirrors schema/materials.schema.json (the portable JSON Schema used for
external validation) but as Pydantic models, so extraction code gets
type-checked parsing, defaults, and clear validation errors for free.

Design principles encoded here (see project report Sections 7 and 14.3):
  * Every numeric claim carries a status: MEASURED / PREDICTED / TARGET /
    INFERRED / UNKNOWN. Never silently merge these.
  * schema_version is present on every record from day one, so records can
    be migrated instead of silently reinterpreted as the schema evolves.
  * Proxy measurements (e.g. Charpy energy standing in for fracture
    toughness) are flagged explicitly via `is_proxy_for`.
  * Mechanism edges carry an evidence label and a list of supporting papers,
    not a single paper reference, since a mechanism is often corroborated
    across multiple sources as the corpus grows.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0.0"


class EvidenceStatus(str, Enum):
    """Status tag required on every extracted numerical value."""
    MEASURED = "MEASURED"
    PREDICTED = "PREDICTED"
    TARGET = "TARGET"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class RelationLabel(str, Enum):
    """Evidence label required on every mechanism-graph edge."""
    EXPLICIT = "EXPLICIT"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"


class Evidence(BaseModel):
    claim: str
    source_page: Optional[int] = None
    quote_or_span: Optional[str] = Field(
        default=None,
        description="Short paraphrase or span pointer, not a long verbatim quote.",
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class PaperRef(BaseModel):
    title: str
    doi: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    institution: Optional[str] = None
    section: Optional[str] = None


class CompositionEntry(BaseModel):
    element: str
    value: Optional[float] = None
    unit: str = "wt%"
    status: EvidenceStatus = EvidenceStatus.MEASURED
    is_balance: bool = False
    evidence: Optional[Evidence] = None


class ProcessingStep(BaseModel):
    step: str
    temperature_C: Optional[float] = None
    time: Optional[str] = None
    cooling: Optional[str] = None
    notes: Optional[str] = None
    evidence: Optional[Evidence] = None


class MicrostructureFeature(BaseModel):
    feature: str
    phase: Optional[str] = None
    size_nm: Optional[float] = None
    formers: List[str] = Field(default_factory=list)
    status: EvidenceStatus = EvidenceStatus.MEASURED
    evidence: Optional[Evidence] = None


class PropertyValue(BaseModel):
    property: str
    value: Optional[float] = None
    unit: Optional[str] = None
    temperature_C: Optional[float] = None
    status: EvidenceStatus = EvidenceStatus.MEASURED
    is_proxy_for: Optional[str] = Field(
        default=None,
        description="e.g. 'fracture_toughness' when this value is a Charpy "
                    "energy standing in for a direct K_IC measurement.",
    )
    evidence: Optional[Evidence] = None


class WeldabilityIndicators(BaseModel):
    carbon_wt_pct: Optional[float] = None
    rule_of_thumb_limit_wt_pct: Optional[float] = None
    carbon_equivalent: Optional[float] = None
    notes: Optional[str] = None


class MechanismEdge(BaseModel):
    """One edge in the element -> microstructure -> mechanism -> property chain."""
    source: str
    target: str
    relation: str
    label: RelationLabel = RelationLabel.UNKNOWN
    supporting_paper_ids: List[str] = Field(default_factory=list)
    evidence: Optional[Evidence] = None


class Steel(BaseModel):
    name: str
    base_element: str = "Fe"
    alloy_family: Optional[str] = None
    composition: List[CompositionEntry] = Field(default_factory=list)


class MaterialRecord(BaseModel):
    """One experimentally tested material under one processing condition."""
    schema_version: str = SCHEMA_VERSION
    record_id: str
    paper: PaperRef
    steel: Steel
    processing: List[ProcessingStep] = Field(default_factory=list)
    microstructure: List[MicrostructureFeature] = Field(default_factory=list)
    properties: List[PropertyValue] = Field(default_factory=list)
    weldability_indicators: Optional[WeldabilityIndicators] = None
    mechanisms: List[MechanismEdge] = Field(default_factory=list)
    design_rationale: List[str] = Field(default_factory=list)

    def get_property(self, name: str) -> List[PropertyValue]:
        """All recorded values for a property name (there may be several,
        e.g. Charpy at different temperatures)."""
        return [p for p in self.properties if p.property.lower() == name.lower()]

    def get_element(self, symbol: str) -> Optional[CompositionEntry]:
        for c in self.steel.composition:
            if c.element.lower() == symbol.lower():
                return c
        return None
