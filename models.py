from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


INK_ORDER = ["C", "M", "Y", "K"]


@dataclass
class LogItem:
    name: str = ""
    h_position_mm: float = 0.0
    v_position_mm: float = 0.0
    width_mm: float = 0.0
    height_mm: float = 0.0
    width_dots: int = 0
    height_dots: int = 0

    gray_icc: str = ""
    rgb_icc: str = ""
    cmyk_icc: str = ""
    proofing_icc: str = ""

    brightness: str = ""
    contrast: str = ""
    saturation: str = ""
    color_replacement: str = ""

    kdots: Dict[str, List[int]] = field(default_factory=dict)


@dataclass
class ParsedLog:
    # origem do arquivo
    source_path: str
    file_size_bytes: int
    file_modified_at: str
    source_fingerprint: str = ""

    # [General]
    computer_name: str = ""
    software_version: str = ""
    job_id: str = ""
    document: str = ""
    file_count: int = 0
    start_time: str = ""
    end_time: str = ""
    driver: str = ""
    copy: int = 0
    total_copies: int = 0
    units: str = ""

    # [Costs]
    page_width_mm: float = 0.0
    print_width_mm: float = 0.0
    print_height_mm: float = 0.0
    print_width_dots: int = 0
    print_height_dots: int = 0
    bits_per_pixel: int = 0

    # [PrintSettings]
    scheme: str = ""
    print_mode: str = ""
    advanced_settings: str = ""
    correction: str = ""
    overprint: str = ""

    # [ColorManagement]
    inkset: str = ""
    ink_limit: str = ""
    ink_usage: str = ""
    linearization: str = ""
    post_linearization: str = ""
    icc: str = ""
    hueman_version: str = ""
    revision: str = ""
    preset: str = ""
    shadow_optimizer: str = ""
    rendering_img: str = ""
    rendering_vect: str = ""
    rendering_spot: str = ""
    cmm: str = ""
    direct_colors_table: str = ""
    halftoning: str = ""

    # consumo e gotas
    ink_ml: Dict[str, float] = field(default_factory=dict)
    ink_drop_sizes: Dict[str, List[float]] = field(default_factory=dict)
    kdots_costs: Dict[str, List[int]] = field(default_factory=dict)

    # item [1]
    item: LogItem = field(default_factory=LogItem)

    # derivados
    duration_seconds: int = 0
    fabric_inferred: str = "DESCONHECIDO"

    actual_printed_length_m: float = 0.0
    width_printed_m: float = 0.0
    printed_area_m2: float = 0.0

    gap_before_m: float = 0.0
    gap_after_m: Optional[float] = None

    paper_linear_m: float = 0.0
    paper_used_length_m: float = 0.0
    total_paper_until_end_m: float = 0.0
    paper_used_area_m2: float = 0.0

    speed_m_per_min: float = 0.0
    ink_total_ml: float = 0.0
    ink_ml_per_meter: float = 0.0
    ink_ml_per_m2: float = 0.0

    width_occupancy_pct: float = 0.0
    left_margin_mm: float = 0.0
    right_margin_mm: float = 0.0

    # papel/custos
    paper_id: str = ""
    paper_name: str = ""
    cost_paper: float = 0.0
    cost_ink: float = 0.0
    cost_total: float = 0.0

    # bruto
    raw_sections: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class PaperConfig:
    id: str
    name: str
    width_m: float
    grammage_gm2: float
    cost_per_linear_meter: float
    cost_per_kg: float
    use_cost_per_kg: bool
    is_default: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "width_m": self.width_m,
            "grammage_gm2": self.grammage_gm2,
            "cost_per_linear_meter": self.cost_per_linear_meter,
            "cost_per_kg": self.cost_per_kg,
            "use_cost_per_kg": self.use_cost_per_kg,
            "is_default": self.is_default,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaperConfig":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            width_m=float(data.get("width_m", 0.0) or 0.0),
            grammage_gm2=float(data.get("grammage_gm2", 0.0) or 0.0),
            cost_per_linear_meter=float(data.get("cost_per_linear_meter", 0.0) or 0.0),
            cost_per_kg=float(data.get("cost_per_kg", 0.0) or 0.0),
            use_cost_per_kg=bool(data.get("use_cost_per_kg", False)),
            is_default=bool(data.get("is_default", False)),
        )