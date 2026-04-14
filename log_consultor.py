from __future__ import annotations

import json
import re
import uuid
import hashlib
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from typing import Any, Dict, List, Optional

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk


APP_NAME = "Print Consultor"
APP_VERSION = "2.5"
CONFIG_PATH = Path("log_consultor.config.json")

INK_ORDER = ["C", "M", "Y", "K"]


DEFAULT_CONFIG = {
    "papers": [
        {
            "id": "paper-default",
            "name": "Papel 60g",
            "width_m": 1.78,
            "grammage_gm2": 60.0,
            "cost_per_linear_meter": 0.0,
            "cost_per_kg": 0.0,
            "use_cost_per_kg": False,
            "is_default": True,
        }
    ],
    "ink_cost_per_liter": {
        "C": 0.0,
        "M": 0.0,
        "Y": 0.0,
        "K": 0.0,
    },
}


def round_up_2(value: float) -> float:
    q = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    return float(q)


def fmt_num(value: float) -> str:
    return f"{round_up_2(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_money(value: float) -> str:
    return f"R$ {fmt_num(value)}"


def fmt_m(value: float) -> str:
    return f"{fmt_num(value)} m"


def fmt_m_no_suffix(value: float) -> str:
    return f"{fmt_num(value)}"


def fmt_m2(value: float) -> str:
    return f"{fmt_num(value)} m²"


def fmt_ml(value: float) -> str:
    return f"{fmt_num(value)} mL"


def fmt_pct(value: float) -> str:
    return f"{fmt_num(value)}%"


def fmt_speed(value: float) -> str:
    return f"{fmt_num(value)} m/min"


def fmt_seconds(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}h {m:02d}min {s:02d}s"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return default


def ensure_papers(config: Dict[str, Any]) -> Dict[str, Any]:
    papers = config.get("papers")
    if not isinstance(papers, list) or not papers:
        config["papers"] = json.loads(json.dumps(DEFAULT_CONFIG["papers"]))

    normalized: List[Dict[str, Any]] = []
    has_default = False

    for i, raw in enumerate(config["papers"]):
        if not isinstance(raw, dict):
            continue

        paper = {
            "id": str(raw.get("id") or f"paper-{i+1}"),
            "name": str(raw.get("name") or f"Papel {i+1}").strip(),
            "width_m": safe_float(raw.get("width_m"), 0.0),
            "grammage_gm2": safe_float(raw.get("grammage_gm2"), 0.0),
            "cost_per_linear_meter": safe_float(raw.get("cost_per_linear_meter"), 0.0),
            "cost_per_kg": safe_float(raw.get("cost_per_kg"), 0.0),
            "use_cost_per_kg": bool(raw.get("use_cost_per_kg", False)),
            "is_default": bool(raw.get("is_default", False)),
        }

        if paper["is_default"] and not has_default:
            has_default = True
        else:
            paper["is_default"] = False

        normalized.append(paper)

    if not normalized:
        normalized = json.loads(json.dumps(DEFAULT_CONFIG["papers"]))

    if not any(p["is_default"] for p in normalized):
        normalized[0]["is_default"] = True

    config["papers"] = normalized
    return config


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        save_config(config)
        return config

    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        raw = {}

    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    cfg.update({k: v for k, v in raw.items() if k in cfg})

    if "ink_cost_per_liter" in raw and isinstance(raw["ink_cost_per_liter"], dict):
        for k in INK_ORDER:
            cfg["ink_cost_per_liter"][k] = safe_float(raw["ink_cost_per_liter"].get(k), 0.0)

    cfg = ensure_papers(cfg)
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    cfg = ensure_papers(cfg)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def paper_display_name(paper: Dict[str, Any]) -> str:
    suffix = " (padrão)" if paper.get("is_default") else ""
    return f"{paper.get('name', 'Sem nome')}{suffix}"


def get_default_paper(config: Dict[str, Any]) -> Dict[str, Any]:
    papers = config.get("papers", [])
    for paper in papers:
        if paper.get("is_default"):
            return paper
    return papers[0]


def get_paper_by_id(config: Dict[str, Any], paper_id: str) -> Optional[Dict[str, Any]]:
    for paper in config.get("papers", []):
        if paper.get("id") == paper_id:
            return paper
    return None


RE_SECTION = re.compile(r"^\s*\[(.+?)\]\s*$")
RE_KV = re.compile(r"^\s*([^=]+?)\s*=\s*(.*?)\s*$")


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
    source_path: str
    file_size_bytes: int
    file_modified_at: str
    source_fingerprint: str = ""

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

    page_width_mm: float = 0.0
    print_width_mm: float = 0.0
    print_height_mm: float = 0.0
    print_width_dots: int = 0
    print_height_dots: int = 0
    bits_per_pixel: int = 0

    scheme: str = ""
    print_mode: str = ""
    advanced_settings: str = ""
    correction: str = ""
    overprint: str = ""

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

    ink_ml: Dict[str, float] = field(default_factory=dict)
    ink_drop_sizes: Dict[str, List[float]] = field(default_factory=dict)
    kdots_costs: Dict[str, List[int]] = field(default_factory=dict)

    item: LogItem = field(default_factory=LogItem)

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

    paper_id: str = ""
    paper_name: str = ""
    cost_paper: float = 0.0
    cost_ink: float = 0.0
    cost_total: float = 0.0

    raw_sections: Dict[str, Dict[str, str]] = field(default_factory=dict)


def serialize_parsed_log(log: ParsedLog) -> Dict[str, Any]:
    return asdict(log)


def dict_to_log_item(data: Any) -> LogItem:
    raw = data if isinstance(data, dict) else {}
    field_names = {f.name for f in fields(LogItem)}
    clean = {k: v for k, v in raw.items() if k in field_names}

    if not isinstance(clean.get("kdots"), dict):
        clean["kdots"] = {}

    return LogItem(**clean)


def dict_to_parsed_log(data: Any) -> ParsedLog:
    raw = data if isinstance(data, dict) else {}
    field_names = {f.name for f in fields(ParsedLog)}

    clean = {k: v for k, v in raw.items() if k in field_names and k != "item"}

    clean["source_path"] = str(clean.get("source_path", ""))
    clean["file_size_bytes"] = int(clean.get("file_size_bytes", 0) or 0)
    clean["file_modified_at"] = str(clean.get("file_modified_at", ""))
    clean["source_fingerprint"] = str(clean.get("source_fingerprint", ""))

    if not isinstance(clean.get("ink_ml"), dict):
        clean["ink_ml"] = {}

    if not isinstance(clean.get("ink_drop_sizes"), dict):
        clean["ink_drop_sizes"] = {}

    if not isinstance(clean.get("kdots_costs"), dict):
        clean["kdots_costs"] = {}

    if not isinstance(clean.get("raw_sections"), dict):
        clean["raw_sections"] = {}

    clean["item"] = dict_to_log_item(raw.get("item", {}))

    return ParsedLog(**clean)


def build_file_fingerprint(path: str) -> str:
    p = Path(path)

    try:
        sha1 = hashlib.sha1()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                sha1.update(chunk)
        return sha1.hexdigest()
    except Exception:
        try:
            stat = p.stat()
            return f"{p.name}|{stat.st_size}|{int(stat.st_mtime)}"
        except Exception:
            return str(p).lower()


def collect_log_files_from_folder(folder: str, recursive: bool = True) -> List[str]:
    root = Path(folder)
    if not root.exists() or not root.is_dir():
        return []

    pattern = "**/*.txt" if recursive else "*.txt"
    files = [str(p) for p in root.glob(pattern) if p.is_file()]
    files.sort()
    return files


def parse_datetime(text: str) -> Optional[datetime]:
    text = (text or "").strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            pass
    return None


def infer_fabric(document: str) -> str:
    parts = [p.strip() for p in (document or "").split(" - ")]
    if len(parts) >= 2 and parts[1]:
        return parts[1]
    return "DESCONHECIDO"


def parse_drop_sizes(raw: str) -> List[float]:
    if not raw:
        return []
    return [safe_float(x, 0.0) for x in raw.split(",") if str(x).strip()]


def parse_log_file(path: str) -> ParsedLog:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore").splitlines()

    sections: Dict[str, Dict[str, str]] = {}
    current = None

    for line in text:
        msec = RE_SECTION.match(line)
        if msec:
            current = msec.group(1).strip()
            sections[current] = sections.get(current, {})
            continue

        mkv = RE_KV.match(line)
        if not mkv or not current:
            continue

        k = mkv.group(1).strip()
        v = mkv.group(2).strip()
        sections[current][k] = v

    general = sections.get("General", {})
    costs = sections.get("Costs", {})
    print_settings = sections.get("PrintSettings", {})
    color_mgmt = sections.get("ColorManagement", {})
    item1 = sections.get("1", {})

    stat = p.stat()

    parsed = ParsedLog(
        source_path=str(p),
        file_size_bytes=stat.st_size,
        file_modified_at=datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
        source_fingerprint=build_file_fingerprint(str(p)),
        raw_sections=sections,
    )

    parsed.computer_name = general.get("ComputerName", "")
    parsed.software_version = general.get("SoftwareVersion", "")
    parsed.job_id = general.get("JobID", "")
    parsed.document = general.get("Document", "") or item1.get("Name", p.name)
    parsed.file_count = int(safe_float(general.get("FileCount", 0), 0))
    parsed.start_time = general.get("StartTime", "")
    parsed.end_time = general.get("EndTime", "")
    parsed.driver = general.get("Driver", "")
    parsed.copy = int(safe_float(general.get("Copy", 0), 0))
    parsed.total_copies = int(safe_float(general.get("TotalCopies", 0), 0))
    parsed.units = general.get("Units", "")

    parsed.page_width_mm = safe_float(costs.get("PageWidthMM", 0), 0.0)
    parsed.print_width_mm = safe_float(costs.get("PrintWidthMM", 0), 0.0)
    parsed.print_height_mm = safe_float(costs.get("PrintHeightMM", 0), 0.0)
    parsed.print_width_dots = int(safe_float(costs.get("PrintWidth_Dots", 0), 0))
    parsed.print_height_dots = int(safe_float(costs.get("PrintHeight_Dots", 0), 0))
    parsed.bits_per_pixel = int(safe_float(costs.get("BitsPerPixel", 0), 0))

    parsed.scheme = print_settings.get("Scheme", "")
    parsed.print_mode = print_settings.get("PrintMode", "")
    parsed.advanced_settings = print_settings.get("AdvancedSettings", "")
    parsed.correction = print_settings.get("Correction", "")
    parsed.overprint = print_settings.get("DeviceNXCMOverPrint", "")

    parsed.inkset = color_mgmt.get("Inkset", "")
    parsed.ink_limit = color_mgmt.get("InkLimit", "")
    parsed.ink_usage = color_mgmt.get("InkUsage", "")
    parsed.linearization = color_mgmt.get("Linearization", "")
    parsed.post_linearization = color_mgmt.get("PostLinearization", "")
    parsed.icc = color_mgmt.get("ICC", "")
    parsed.hueman_version = color_mgmt.get("HuemanVersion", "")
    parsed.revision = color_mgmt.get("Revision", "")
    parsed.preset = color_mgmt.get("Preset", "")
    parsed.shadow_optimizer = color_mgmt.get("ShadowOptimizer", "")
    parsed.rendering_img = color_mgmt.get("RenderingImg", "")
    parsed.rendering_vect = color_mgmt.get("RenderingVect", "")
    parsed.rendering_spot = color_mgmt.get("RenderingSpot", "")
    parsed.cmm = color_mgmt.get("CMM", "")
    parsed.direct_colors_table = color_mgmt.get("DirectColorsTable", "")
    parsed.halftoning = color_mgmt.get("Halftoning", "")

    for ch in INK_ORDER:
        parsed.ink_ml[ch] = safe_float(costs.get(f"InkML[{ch}]", 0), 0.0)
        parsed.ink_drop_sizes[ch] = parse_drop_sizes(costs.get(f"InkDropsizes[{ch}]", ""))
        parsed.kdots_costs[ch] = [
            int(safe_float(costs.get(f"KDots[{ch}][1]", 0), 0)),
            int(safe_float(costs.get(f"KDots[{ch}][2]", 0), 0)),
            int(safe_float(costs.get(f"KDots[{ch}][3]", 0), 0)),
        ]

    item = LogItem()
    item.name = item1.get("Name", parsed.document)
    item.h_position_mm = safe_float(item1.get("HPositionMM", 0), 0.0)
    item.v_position_mm = safe_float(item1.get("VPositionMM", 0), 0.0)
    item.width_mm = safe_float(item1.get("WidthMM", 0), 0.0)
    item.height_mm = safe_float(item1.get("HeightMM", 0), 0.0)
    item.width_dots = int(safe_float(item1.get("Width_Dots", 0), 0))
    item.height_dots = int(safe_float(item1.get("Height_Dots", 0), 0))
    item.gray_icc = item1.get("GrayIcc", "")
    item.rgb_icc = item1.get("RgbIcc", "")
    item.cmyk_icc = item1.get("CmykIcc", "")
    item.proofing_icc = item1.get("ProofingIcc", "")
    item.brightness = item1.get("Brightness", "")
    item.contrast = item1.get("Contrast", "")
    item.saturation = item1.get("Saturation", "")
    item.color_replacement = item1.get("ColorReplacement", "")
    for ch in INK_ORDER:
        item.kdots[ch] = [
            int(safe_float(item1.get(f"KDots[{ch}][1]", 0), 0)),
            int(safe_float(item1.get(f"KDots[{ch}][2]", 0), 0)),
            int(safe_float(item1.get(f"KDots[{ch}][3]", 0), 0)),
        ]
    parsed.item = item

    start_dt = parse_datetime(parsed.start_time)
    end_dt = parse_datetime(parsed.end_time)
    if start_dt and end_dt and end_dt >= start_dt:
        parsed.duration_seconds = int((end_dt - start_dt).total_seconds())

    parsed.fabric_inferred = infer_fabric(parsed.document)

    parsed.actual_printed_length_m = item.height_mm / 1000.0 if item.height_mm > 0 else parsed.print_height_mm / 1000.0
    parsed.width_printed_m = item.width_mm / 1000.0 if item.width_mm > 0 else parsed.print_width_mm / 1000.0
    parsed.printed_area_m2 = parsed.actual_printed_length_m * parsed.width_printed_m if parsed.actual_printed_length_m > 0 and parsed.width_printed_m > 0 else 0.0

    parsed.gap_before_m = item.v_position_mm / 1000.0 if item.v_position_mm > 0 else 0.0
    parsed.paper_linear_m = parsed.actual_printed_length_m
    parsed.paper_used_length_m = parsed.actual_printed_length_m + parsed.gap_before_m

    if parsed.print_height_mm > 0 and item.height_mm > 0 and item.v_position_mm > 0:
        remaining_mm = parsed.print_height_mm - (item.v_position_mm + item.height_mm)
        if remaining_mm > 0:
            parsed.gap_after_m = remaining_mm / 1000.0

    if parsed.gap_after_m is not None and parsed.gap_after_m > 0:
        parsed.total_paper_until_end_m = parsed.paper_used_length_m + parsed.gap_after_m
    else:
        parsed.total_paper_until_end_m = parsed.paper_used_length_m

    parsed.ink_total_ml = sum(parsed.ink_ml.values())

    if parsed.duration_seconds > 0:
        parsed.speed_m_per_min = parsed.actual_printed_length_m / (parsed.duration_seconds / 60.0) if parsed.actual_printed_length_m > 0 else 0.0

    if parsed.actual_printed_length_m > 0:
        parsed.ink_ml_per_meter = parsed.ink_total_ml / parsed.actual_printed_length_m

    if parsed.printed_area_m2 > 0:
        parsed.ink_ml_per_m2 = parsed.ink_total_ml / parsed.printed_area_m2

    if parsed.print_width_mm > 0 and item.width_mm > 0:
        parsed.width_occupancy_pct = (item.width_mm / parsed.print_width_mm) * 100.0
        parsed.left_margin_mm = item.h_position_mm
        parsed.right_margin_mm = max(parsed.print_width_mm - item.width_mm - item.h_position_mm, 0.0)

    return parsed


def apply_costs(log: ParsedLog, config: Dict[str, Any], paper_id: Optional[str] = None) -> None:
    paper = get_paper_by_id(config, paper_id or log.paper_id) or get_default_paper(config)
    log.paper_id = paper["id"]
    log.paper_name = paper["name"]

    paper_width_m = safe_float(paper.get("width_m", 0), 0.0)
    grammage = safe_float(paper.get("grammage_gm2", 0), 0.0)
    cost_per_linear_meter = safe_float(paper.get("cost_per_linear_meter", 0), 0.0)
    cost_per_kg = safe_float(paper.get("cost_per_kg", 0), 0.0)
    use_cost_per_kg = bool(paper.get("use_cost_per_kg", False))

    log.paper_used_area_m2 = paper_width_m * log.paper_used_length_m if paper_width_m > 0 and log.paper_used_length_m > 0 else 0.0

    if use_cost_per_kg and paper_width_m > 0 and grammage > 0 and log.paper_used_length_m > 0:
        kg = (paper_width_m * log.paper_used_length_m * grammage) / 1000.0
        log.cost_paper = kg * cost_per_kg
    else:
        log.cost_paper = log.paper_used_length_m * cost_per_linear_meter

    ink_costs = config.get("ink_cost_per_liter", {})
    ink_total_cost = 0.0
    for ch in INK_ORDER:
        ml = log.ink_ml.get(ch, 0.0)
        cost_per_liter = safe_float(ink_costs.get(ch, 0), 0.0)
        ink_total_cost += (ml / 1000.0) * cost_per_liter

    log.cost_ink = ink_total_cost
    log.cost_total = log.cost_paper + log.cost_ink


class SimpleLogo(ctk.CTkCanvas):
    def __init__(self, master, size: int = 28, **kwargs):
        super().__init__(
            master,
            width=size,
            height=size,
            bg="#0B1324",
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        pad = 4
        self.create_polygon(
            size / 2, pad,
            size - pad, size / 2,
            size / 2, size - pad,
            pad, size / 2,
            outline="#32A1FF",
            fill="",
            width=2,
        )
        self.create_rectangle(
            size * 0.42,
            size * 0.42,
            size * 0.58,
            size * 0.58,
            outline="#32A1FF",
            fill="",
            width=2,
        )


class DashboardCard(ctk.CTkFrame):
    def __init__(self, master, title: str, value: str = "-", subtitle: str = "", accent: str = "#4B8BFF", **kwargs):
        super().__init__(master, fg_color="#121B2E", corner_radius=14, border_width=1, border_color="#223153", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.lbl_title = ctk.CTkLabel(self, text=title.upper(), font=ctk.CTkFont(size=11), text_color="#7C92C5", anchor="w")
        self.lbl_title.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 4))

        self.lbl_value = ctk.CTkLabel(self, text=value, font=ctk.CTkFont(size=32, weight="bold"), text_color=accent, anchor="w")
        self.lbl_value.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 2))

        self.lbl_subtitle = ctk.CTkLabel(self, text=subtitle, font=ctk.CTkFont(size=12), text_color="#9AAACC", anchor="w")
        self.lbl_subtitle.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))

    def set(self, value: str, subtitle: str = ""):
        self.lbl_value.configure(text=value)
        self.lbl_subtitle.configure(text=subtitle)


class ActionButton(ctk.CTkButton):
    def __init__(self, master, text: str, command, primary: bool = False, **kwargs):
        fg = "#4B8BFF" if primary else "#151F34"
        hover = "#3D73D2" if primary else "#1D2C49"
        border = "#4B8BFF" if primary else "#25375A"
        super().__init__(
            master,
            text=text,
            command=command,
            height=44,
            corner_radius=10,
            fg_color=fg,
            hover_color=hover,
            border_width=1,
            border_color=border,
            text_color="#EAF1FF",
            anchor="w",
            font=ctk.CTkFont(size=14),
            **kwargs,
        )


class LogConsultorDashboard:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1660x940")
        self.root.minsize(1450, 840)

        self.cfg = load_config()
        self.logs: List[ParsedLog] = []
        self.tree_id_to_log_index: Dict[str, int] = {}
        self.paper_name_to_id: Dict[str, str] = {}

        self.current_session_path: Optional[str] = None
        self.session_name: str = "Consulta sem título"
        self.is_dirty: bool = False

        self.build_layout()
        self.refresh_paper_selector()
        self.refresh_clock()
        self.refresh_summary()
        self.update_window_title()

    def update_window_title(self):
        dirty_suffix = " *" if self.is_dirty else ""
        self.root.title(f"{APP_NAME} — {self.session_name}{dirty_suffix}")

    def mark_dirty(self):
        self.is_dirty = True
        self.update_window_title()

    def mark_clean(self):
        self.is_dirty = False
        self.update_window_title()

    def confirm_discard_if_needed(self) -> bool:
        if not self.is_dirty:
            return True

        return messagebox.askyesno(
            APP_NAME,
            "Há alterações não salvas na consulta atual.\n\nDeseja continuar mesmo assim?",
        )

    def build_session_payload(self) -> Dict[str, Any]:
        return {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "session_name": self.session_name,
            "logs": [serialize_parsed_log(log) for log in self.logs],
        }

    def apply_session_payload(self, payload: Dict[str, Any], path: str):
        logs_raw = payload.get("logs", [])
        if not isinstance(logs_raw, list):
            raise ValueError("Estrutura inválida de consulta.")

        self.logs = [dict_to_parsed_log(item) for item in logs_raw if isinstance(item, dict)]
        self.current_session_path = path
        self.session_name = str(payload.get("session_name") or Path(path).stem)

        self.refresh_table()
        self.refresh_summary()
        self.show_consolidated_if_needed()
        self.mark_clean()

        messagebox.showinfo(
            APP_NAME,
            f"Consulta carregada com sucesso.\n\nLogs restaurados: {len(self.logs)}"
        )

    def new_session(self):
        if self.logs or self.is_dirty:
            if not self.confirm_discard_if_needed():
                return

        self.logs.clear()
        self.current_session_path = None
        self.session_name = "Consulta sem título"

        self.refresh_table()
        self.refresh_summary()
        self.show_consolidated_if_needed()
        self.mark_clean()

    def open_session(self):
        if self.logs or self.is_dirty:
            if not self.confirm_discard_if_needed():
                return

        path = filedialog.askopenfilename(
            title="Abrir consulta",
            filetypes=[
                ("Consultas PrintTrace", "*.ptc"),
                ("Arquivos JSON", "*.json"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not path:
            return

        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Arquivo inválido.")
            self.apply_session_payload(raw, path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Não foi possível abrir a consulta.\n\n{exc}")

    def save_session(self):
        if not self.current_session_path:
            self.save_session_as()
            return

        try:
            payload = self.build_session_payload()
            Path(self.current_session_path).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.mark_clean()
            messagebox.showinfo(APP_NAME, "Consulta salva com sucesso.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Não foi possível salvar a consulta.\n\n{exc}")

    def save_session_as(self):
        path = filedialog.asksaveasfilename(
            title="Salvar consulta como",
            defaultextension=".ptc",
            filetypes=[
                ("Consultas PrintTrace", "*.ptc"),
                ("Arquivos JSON", "*.json"),
            ],
        )
        if not path:
            return

        if not path.lower().endswith((".ptc", ".json")):
            path += ".ptc"

        self.current_session_path = path
        self.session_name = Path(path).stem
        self.update_window_title()
        self.save_session()

    def build_layout(self):
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self.root, width=255, corner_radius=0, fg_color="#0B1324", border_width=1, border_color="#1E2A46")
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        self.content = ctk.CTkFrame(self.root, corner_radius=0, fg_color="#060B16")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(2, weight=1)

        self.build_sidebar()
        self.build_topbar()
        self.build_cards()
        self.build_main_area()

    def build_sidebar(self):
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(18, 10))

        logo_row = ctk.CTkFrame(brand, fg_color="transparent")
        logo_row.pack(anchor="w")

        logo = SimpleLogo(logo_row, size=30)
        logo.pack(side="left", padx=(0, 10))

        title_wrap = ctk.CTkFrame(logo_row, fg_color="transparent")
        title_wrap.pack(side="left")

        ctk.CTkLabel(title_wrap, text="Print Consultor", font=ctk.CTkFont(size=24, weight="bold"), text_color="#F2F6FF").pack(anchor="w")
        ctk.CTkLabel(brand, text="Consulta e consolidação de logs", font=ctk.CTkFont(size=12), text_color="#8DA3D1").pack(anchor="w", pady=(6, 0))

        sep = ctk.CTkFrame(self.sidebar, height=1, fg_color="#1B2642")
        sep.pack(fill="x", pady=(10, 14))

        actions = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        actions.pack(fill="x", padx=12)

        ActionButton(actions, "Nova consulta", self.new_session).pack(fill="x", pady=5)
        ActionButton(actions, "Abrir consulta", self.open_session).pack(fill="x", pady=5)
        ActionButton(actions, "Salvar consulta", self.save_session).pack(fill="x", pady=5)
        ActionButton(actions, "Salvar consulta como", self.save_session_as).pack(fill="x", pady=5)

        ActionButton(actions, "Importar arquivos", self.import_logs_dialog, primary=True).pack(fill="x", pady=5)
        ActionButton(actions, "Importar pasta", self.import_folder_dialog).pack(fill="x", pady=5)
        ActionButton(actions, "Atualizar informações", self.recalculate_all).pack(fill="x", pady=5)
        ActionButton(actions, "Configurações", self.open_config).pack(fill="x", pady=5)
        ActionButton(actions, "Remover selecionado", self.remove_selected).pack(fill="x", pady=5)
        ActionButton(actions, "Limpar lista", self.clear_all).pack(fill="x", pady=5)

        ctk.CTkLabel(self.sidebar, text="Papel para os logs selecionados", font=ctk.CTkFont(size=13, weight="bold"), text_color="#C7D4F0").pack(anchor="w", padx=18, pady=(18, 8))

        self.paper_selector = ctk.CTkComboBox(
            self.sidebar,
            values=["Sem papéis cadastrados"],
            state="readonly",
            fg_color="#10192C",
            border_color="#25375A",
            button_color="#243A63",
            button_hover_color="#2C4A7E",
            dropdown_fg_color="#10192C",
            width=220,
        )
        self.paper_selector.pack(anchor="w", padx=18)

        ActionButton(self.sidebar, "Aplicar papel nos selecionados", self.apply_selected_paper).pack(fill="x", padx=18, pady=(10, 0))

        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(expand=True, fill="both")

    def build_topbar(self):
        self.topbar = ctk.CTkFrame(self.content, height=76, corner_radius=0, fg_color="#0C1325", border_width=1, border_color="#1C2945")
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(self.topbar, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=22, pady=12)

        ctk.CTkLabel(left, text="Home", font=ctk.CTkFont(size=26, weight="bold"), text_color="#F2F6FF").pack(anchor="w")
        ctk.CTkLabel(left, text="Consulta de logs com visão consolidada", font=ctk.CTkFont(size=13), text_color="#8DA3D1").pack(anchor="w", pady=(2, 0))

        right = ctk.CTkFrame(self.topbar, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e", padx=18, pady=12)

        self.clock_label = ctk.CTkLabel(right, text="", font=ctk.CTkFont(size=13), text_color="#93A8D0")
        self.clock_label.pack(side="left", padx=(0, 16))

    def build_cards(self):
        self.cards_wrap = ctk.CTkFrame(self.content, fg_color="transparent")
        self.cards_wrap.grid(row=1, column=0, sticky="ew", padx=20, pady=(18, 8))
        for i in range(4):
            self.cards_wrap.grid_columnconfigure(i, weight=1)

        self.card_logs = DashboardCard(self.cards_wrap, "Logs carregados", "0", "nenhum importado", accent="#5FA2FF")
        self.card_logs.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.card_meters = DashboardCard(self.cards_wrap, "Metragem total", "0,00 m", "metro linear impresso", accent="#FFCC33")
        self.card_meters.grid(row=0, column=1, sticky="ew", padx=10)
        self.card_ink = DashboardCard(self.cards_wrap, "Tinta total", "0,00 mL", "estimativa dos logs", accent="#FF6A6A")
        self.card_ink.grid(row=0, column=2, sticky="ew", padx=10)
        self.card_cost = DashboardCard(self.cards_wrap, "Custo estimado", "R$ 0,00", "papel + tinta", accent="#68E59A")
        self.card_cost.grid(row=0, column=3, sticky="ew", padx=(10, 0))

    def build_main_area(self):
        self.main = ctk.CTkFrame(self.content, fg_color="transparent")
        self.main.grid(row=2, column=0, sticky="nsew", padx=20, pady=(8, 20))
        self.main.grid_columnconfigure(0, weight=3)
        self.main.grid_columnconfigure(1, weight=2)
        self.main.grid_rowconfigure(0, weight=1)

        self.build_table_panel()
        self.build_detail_panel()

    def build_table_panel(self):
        self.table_panel = ctk.CTkFrame(self.main, fg_color="#0C1325", corner_radius=14, border_width=1, border_color="#1C2945")
        self.table_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.table_panel.grid_rowconfigure(1, weight=1)
        self.table_panel.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.table_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Logs importados", font=ctk.CTkFont(size=22, weight="bold"), text_color="#F2F6FF").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Arquivo, início, fim e tempo no lugar de informação duplicada.", font=ctk.CTkFont(size=12), text_color="#8DA3D1").grid(row=1, column=0, sticky="w", pady=(4, 0))

        tree_wrap = ctk.CTkFrame(self.table_panel, fg_color="transparent")
        tree_wrap.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        tree_wrap.grid_rowconfigure(0, weight=1)
        tree_wrap.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.Treeview", background="#0E1729", foreground="#E8EEFB", fieldbackground="#0E1729", borderwidth=0, rowheight=30, font=("Segoe UI", 10))
        style.map("Dark.Treeview", background=[("selected", "#1B3B6B")])
        style.configure("Dark.Treeview.Heading", background="#121E34", foreground="#8EA7D6", relief="flat", font=("Segoe UI", 10, "bold"))
        style.map("Dark.Treeview.Heading", background=[("active", "#162540")])

        columns = ("arquivo", "inicio", "fim", "tecido", "papel", "impresso", "tempo", "tinta", "custo")
        self.tree = ttk.Treeview(tree_wrap, columns=columns, show="headings", style="Dark.Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew")

        headings = {
            "arquivo": "Arquivo",
            "inicio": "Início",
            "fim": "Fim",
            "tecido": "Tecido",
            "papel": "Papel",
            "impresso": "Impresso",
            "tempo": "Tempo",
            "tinta": "Tinta total",
            "custo": "Custo total",
        }
        widths = {
            "arquivo": 210,
            "inicio": 145,
            "fim": 145,
            "tecido": 120,
            "papel": 140,
            "impresso": 100,
            "tempo": 120,
            "tinta": 110,
            "custo": 120,
        }

        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor="w")

        scrollbar = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def build_detail_panel(self):
        self.detail_panel = ctk.CTkFrame(self.main, fg_color="#0C1325", corner_radius=14, border_width=1, border_color="#1C2945")
        self.detail_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.detail_panel.grid_rowconfigure(1, weight=1)
        self.detail_panel.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text="Painel de contexto", font=ctk.CTkFont(size=22, weight="bold"), text_color="#F2F6FF").grid(row=0, column=0, sticky="w")

        self.segmented = ctk.CTkSegmentedButton(
            header,
            values=["Resumo", "Campos brutos", "Consolidado"],
            command=self.change_detail_tab,
            selected_color="#2A4F87",
            selected_hover_color="#2A4F87",
            unselected_color="#131D31",
            unselected_hover_color="#182640",
            text_color="#DCE6FB",
            corner_radius=10,
        )
        self.segmented.grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.segmented.set("Resumo")

        self.detail_text = ctk.CTkTextbox(
            self.detail_panel,
            fg_color="#09101F",
            border_width=1,
            border_color="#1D2942",
            text_color="#E8EEFB",
            font=("Consolas", 12),
            corner_radius=12,
            wrap="word",
        )
        self.detail_text.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
        self.set_detail_text("Selecione um log para ver o resumo.")

    def refresh_clock(self):
        self.clock_label.configure(text=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        self.root.after(1000, self.refresh_clock)

    def refresh_paper_selector(self):
        papers = self.cfg.get("papers", [])
        self.paper_name_to_id = {}
        values = []
        default_label = None

        for paper in papers:
            label = paper_display_name(paper)
            values.append(label)
            self.paper_name_to_id[label] = paper["id"]
            if paper.get("is_default"):
                default_label = label

        if not values:
            values = ["Sem papéis cadastrados"]
            default_label = values[0]

        self.paper_selector.configure(values=values)
        self.paper_selector.set(default_label or values[0])

    def selected_log_indexes(self) -> List[int]:
        selection = self.tree.selection()
        indexes = []
        for item in selection:
            idx = self.tree_id_to_log_index.get(item)
            if idx is not None:
                indexes.append(idx)
        return indexes

    def import_logs_dialog(self):
        paths = filedialog.askopenfilenames(title="Selecionar logs .txt", filetypes=[("Logs TXT", "*.txt")])
        self.import_paths(list(paths))

    def import_folder_dialog(self):
        folder = filedialog.askdirectory(title="Selecionar pasta com logs")
        if not folder:
            return

        recursive = messagebox.askyesno(
            APP_NAME,
            "Deseja incluir subpastas?\n\nUse 'Sim' para importar vários dias de uma vez.",
        )

        paths = collect_log_files_from_folder(folder, recursive=recursive)

        if not paths:
            messagebox.showwarning(APP_NAME, "Nenhum arquivo .txt foi encontrado na pasta selecionada.")
            return

        self.import_paths(paths)

    def import_paths(self, paths: List[str]):
        if not paths:
            return

        imported = 0
        skipped = 0
        errors = 0

        default_paper = get_default_paper(self.cfg)

        existing_fingerprints = {
            log.source_fingerprint
            for log in self.logs
            if getattr(log, "source_fingerprint", "")
        }

        session_fingerprints = set(existing_fingerprints)

        for path in paths:
            try:
                p = Path(path)

                if not p.is_file():
                    skipped += 1
                    continue

                if p.suffix.lower() != ".txt":
                    skipped += 1
                    continue

                fingerprint = build_file_fingerprint(str(p))

                if fingerprint in session_fingerprints:
                    skipped += 1
                    continue

                parsed = parse_log_file(str(p))
                parsed.source_fingerprint = fingerprint

                apply_costs(parsed, self.cfg, default_paper["id"])

                self.logs.append(parsed)
                session_fingerprints.add(fingerprint)
                imported += 1

            except Exception:
                errors += 1

        self.refresh_table()
        self.refresh_summary()
        self.show_consolidated_if_needed()

        if imported > 0:
            self.mark_dirty()

        if imported == 0 and skipped > 0 and errors == 0:
            messagebox.showwarning(
                APP_NAME,
                "Nenhum novo log válido foi importado.\n"
                "Os arquivos podem já estar carregados ou não serem logs válidos.",
            )
            return

        messagebox.showinfo(
            APP_NAME,
            f"Importados: {imported}\n"
            f"Ignorados: {skipped}\n"
            f"Erros: {errors}"
        )

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        self.tree_id_to_log_index.clear()

        for idx, log in enumerate(self.logs):
            iid = f"log_{idx}"
            self.tree_id_to_log_index[iid] = idx
            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    Path(log.source_path).name,
                    log.start_time or "—",
                    log.end_time or "—",
                    log.fabric_inferred,
                    log.paper_name or "—",
                    fmt_m(log.actual_printed_length_m),
                    fmt_seconds(log.duration_seconds),
                    fmt_ml(log.ink_total_ml),
                    fmt_money(log.cost_total),
                ),
            )

    def refresh_summary(self):
        total_logs = len(self.logs)
        total_m = sum(x.actual_printed_length_m for x in self.logs)
        total_ink = sum(x.ink_total_ml for x in self.logs)
        total_cost = sum(x.cost_total for x in self.logs)

        self.card_logs.set(str(total_logs), "prontos para análise" if total_logs else "nenhum importado")
        self.card_meters.set(fmt_m(total_m), "metro linear impresso")
        self.card_ink.set(fmt_ml(total_ink), "estimativa total")
        self.card_cost.set(fmt_money(total_cost), "papel + tinta")

    def on_tree_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        idx = self.tree_id_to_log_index.get(selection[0])
        if idx is None or idx >= len(self.logs):
            return
        self.render_current_tab(self.logs[idx])

    def change_detail_tab(self, _value: str):
        selection = self.tree.selection()
        if selection:
            idx = self.tree_id_to_log_index.get(selection[0])
            if idx is not None and idx < len(self.logs):
                self.render_current_tab(self.logs[idx])
                return
        self.show_consolidated_if_needed()

    def render_current_tab(self, log: ParsedLog):
        tab = self.segmented.get()
        if tab == "Resumo":
            self.set_detail_text(self.build_summary(log))
        elif tab == "Campos brutos":
            self.set_detail_text(self.build_raw_summary(log))
        else:
            self.set_detail_text(self.build_consolidated_summary())

    def show_consolidated_if_needed(self):
        if self.segmented.get() == "Consolidado":
            self.set_detail_text(self.build_consolidated_summary())
        elif not self.logs:
            self.set_detail_text("Selecione um log para ver o resumo.")

    def set_detail_text(self, text: str):
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state="disabled")

    def remove_selected(self):
        indexes = sorted(self.selected_log_indexes(), reverse=True)
        if not indexes:
            return

        for idx in indexes:
            if 0 <= idx < len(self.logs):
                self.logs.pop(idx)

        self.refresh_table()
        self.refresh_summary()
        self.show_consolidated_if_needed()
        self.mark_dirty()

    def clear_all(self):
        if not self.logs:
            return

        self.logs.clear()
        self.refresh_table()
        self.refresh_summary()
        self.show_consolidated_if_needed()
        self.mark_dirty()

    def recalculate_all(self):
        self.cfg = load_config()
        self.refresh_paper_selector()
        for log in self.logs:
            apply_costs(log, self.cfg, log.paper_id)
        self.refresh_table()
        self.refresh_summary()
        self.show_consolidated_if_needed()
        self.mark_dirty()
        messagebox.showinfo(APP_NAME, "Informações recalculadas com base nas configurações atuais.")

    def apply_selected_paper(self):
        indexes = self.selected_log_indexes()
        if not indexes:
            messagebox.showwarning(APP_NAME, "Selecione um ou mais logs para aplicar o papel.")
            return

        selected_label = self.paper_selector.get().strip()
        paper_id = self.paper_name_to_id.get(selected_label)
        paper = get_paper_by_id(self.cfg, paper_id) if paper_id else None
        if not paper:
            messagebox.showwarning(APP_NAME, "Selecione um papel válido.")
            return

        for idx in indexes:
            apply_costs(self.logs[idx], self.cfg, paper["id"])

        self.refresh_table()
        self.refresh_summary()
        self.show_consolidated_if_needed()
        self.mark_dirty()
        messagebox.showinfo(APP_NAME, f"Papel aplicado aos logs selecionados: {paper['name']}")

    def open_config(self):
        win = ctk.CTkToplevel(self.root)
        win.title("Configurações")
        win.geometry("980x700")
        win.grab_set()
        win.configure(fg_color="#0A1020")

        state = {
            "config": json.loads(json.dumps(self.cfg)),
            "selected_paper_id": None,
        }

        main = ctk.CTkFrame(win, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=18, pady=18)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(main, text="Configurações", font=ctk.CTkFont(size=28, weight="bold"), text_color="#F2F6FF").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        left = ctk.CTkFrame(main, fg_color="#0F172A", corner_radius=14, border_width=1, border_color="#1E2B48")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(main, fg_color="#0F172A", corner_radius=14, border_width=1, border_color="#1E2B48")
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Papéis cadastrados", font=ctk.CTkFont(size=18, weight="bold"), text_color="#F2F6FF").grid(row=0, column=0, sticky="w", padx=14, pady=(14, 10))

        papers_list = ctk.CTkScrollableFrame(left, fg_color="transparent")
        papers_list.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        paper_vars = {
            "name": ctk.StringVar(),
            "width_m": ctk.StringVar(),
            "grammage_gm2": ctk.StringVar(),
            "cost_per_linear_meter": ctk.StringVar(),
            "cost_per_kg": ctk.StringVar(),
            "use_cost_per_kg": ctk.BooleanVar(value=False),
        }

        ink_vars = {ch: ctk.StringVar(value=str(state["config"]["ink_cost_per_liter"].get(ch, 0.0))) for ch in INK_ORDER}

        def get_selected_paper() -> Optional[Dict[str, Any]]:
            pid = state["selected_paper_id"]
            if not pid:
                return None
            return get_paper_by_id(state["config"], pid)

        def load_paper_into_form(paper: Dict[str, Any]):
            state["selected_paper_id"] = paper["id"]
            paper_vars["name"].set(str(paper.get("name", "")))
            paper_vars["width_m"].set(str(paper.get("width_m", 0)))
            paper_vars["grammage_gm2"].set(str(paper.get("grammage_gm2", 0)))
            paper_vars["cost_per_linear_meter"].set(str(paper.get("cost_per_linear_meter", 0)))
            paper_vars["cost_per_kg"].set(str(paper.get("cost_per_kg", 0)))
            paper_vars["use_cost_per_kg"].set(bool(paper.get("use_cost_per_kg", False)))
            refresh_paper_buttons()

        def save_form_to_selected():
            paper = get_selected_paper()
            if not paper:
                return
            paper["name"] = paper_vars["name"].get().strip() or "Sem nome"
            paper["width_m"] = safe_float(paper_vars["width_m"].get(), 0.0)
            paper["grammage_gm2"] = safe_float(paper_vars["grammage_gm2"].get(), 0.0)
            paper["cost_per_linear_meter"] = safe_float(paper_vars["cost_per_linear_meter"].get(), 0.0)
            paper["cost_per_kg"] = safe_float(paper_vars["cost_per_kg"].get(), 0.0)
            paper["use_cost_per_kg"] = bool(paper_vars["use_cost_per_kg"].get())

        def refresh_paper_buttons():
            for child in papers_list.winfo_children():
                child.destroy()

            for paper in state["config"]["papers"]:
                label = paper_display_name(paper)
                active = paper["id"] == state["selected_paper_id"]
                btn = ctk.CTkButton(
                    papers_list,
                    text=label,
                    height=42,
                    corner_radius=10,
                    anchor="w",
                    fg_color="#1E3A66" if active else "#151F34",
                    hover_color="#1D2C49",
                    border_width=1,
                    border_color="#25375A",
                    text_color="#EAF1FF",
                    command=lambda p=paper: load_paper_into_form(p),
                )
                btn.pack(fill="x", pady=4)

        def field(parent, label, var):
            wrap = ctk.CTkFrame(parent, fg_color="#11192D", corner_radius=12, border_width=1, border_color="#1E2B48")
            wrap.pack(fill="x", pady=7)
            ctk.CTkLabel(wrap, text=label, text_color="#D9E4FB", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=14, pady=(10, 4))
            ctk.CTkEntry(wrap, textvariable=var, height=38, fg_color="#0C1325", border_color="#25385A").pack(fill="x", padx=14, pady=(0, 10))

        tabs = ctk.CTkTabview(right, fg_color="#0F172A", segmented_button_fg_color="#11192D", segmented_button_selected_color="#2A4F87")
        tabs.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        tab_papers = tabs.add("Papéis")
        tab_inks = tabs.add("Tintas")

        ctk.CTkLabel(tab_papers, text="Dados do papel", font=ctk.CTkFont(size=20, weight="bold"), text_color="#F2F6FF").pack(anchor="w", pady=(8, 10))
        field(tab_papers, "Nome do papel", paper_vars["name"])
        field(tab_papers, "Largura do papel (m)", paper_vars["width_m"])
        field(tab_papers, "Gramatura (g/m²)", paper_vars["grammage_gm2"])
        field(tab_papers, "Custo por metro linear", paper_vars["cost_per_linear_meter"])
        field(tab_papers, "Custo por kg", paper_vars["cost_per_kg"])

        check_wrap = ctk.CTkFrame(tab_papers, fg_color="#11192D", corner_radius=12, border_width=1, border_color="#1E2B48")
        check_wrap.pack(fill="x", pady=7)
        ctk.CTkCheckBox(check_wrap, text="Usar custo por kg neste papel", variable=paper_vars["use_cost_per_kg"], text_color="#D9E4FB").pack(anchor="w", padx=14, pady=12)

        def add_new_paper():
            save_form_to_selected()
            new_paper = {
                "id": str(uuid.uuid4()),
                "name": "Novo papel",
                "width_m": 0.0,
                "grammage_gm2": 0.0,
                "cost_per_linear_meter": 0.0,
                "cost_per_kg": 0.0,
                "use_cost_per_kg": False,
                "is_default": False,
            }
            state["config"]["papers"].append(new_paper)
            load_paper_into_form(new_paper)

        def delete_selected_paper():
            paper = get_selected_paper()
            if not paper:
                return
            if len(state["config"]["papers"]) == 1:
                messagebox.showwarning(APP_NAME, "Você precisa manter pelo menos um papel cadastrado.", parent=win)
                return
            state["config"]["papers"] = [p for p in state["config"]["papers"] if p["id"] != paper["id"]]
            if paper.get("is_default") and state["config"]["papers"]:
                state["config"]["papers"][0]["is_default"] = True
            load_paper_into_form(state["config"]["papers"][0])

        def set_default_selected_paper():
            paper = get_selected_paper()
            if not paper:
                return
            save_form_to_selected()
            for p in state["config"]["papers"]:
                p["is_default"] = p["id"] == paper["id"]
            refresh_paper_buttons()

        buttons = ctk.CTkFrame(tab_papers, fg_color="transparent")
        buttons.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(buttons, text="Novo papel", command=add_new_paper, fg_color="#151F34", hover_color="#1D2C49").pack(side="left")
        ctk.CTkButton(buttons, text="Excluir papel", command=delete_selected_paper, fg_color="#4D2030", hover_color="#65293D").pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Definir como padrão", command=set_default_selected_paper, fg_color="#1F5B3D", hover_color="#2A7A52").pack(side="left")

        ctk.CTkLabel(tab_inks, text="Tintas — custo por litro", font=ctk.CTkFont(size=20, weight="bold"), text_color="#F2F6FF").pack(anchor="w", pady=(8, 10))
        for ch in INK_ORDER:
            field(tab_inks, f"Tinta {ch}", ink_vars[ch])

        footer = ctk.CTkFrame(main, fg_color="transparent")
        footer.grid(row=2, column=0, columnspan=2, sticky="e", pady=(14, 0))

        def save_all():
            save_form_to_selected()
            for ch in INK_ORDER:
                state["config"]["ink_cost_per_liter"][ch] = safe_float(ink_vars[ch].get(), 0.0)

            state["config"] = ensure_papers(state["config"])
            save_config(state["config"])
            self.cfg = load_config()
            self.refresh_paper_selector()
            win.destroy()
            messagebox.showinfo(APP_NAME, "Configurações salvas. Use 'Atualizar informações' para recalcular.")

        ctk.CTkButton(footer, text="Cancelar", command=win.destroy, fg_color="#151F34", hover_color="#1D2C49").pack(side="left", padx=(0, 8))
        ctk.CTkButton(footer, text="Salvar configurações", command=save_all, fg_color="#4B8BFF", hover_color="#3D73D2").pack(side="left")

        load_paper_into_form(get_default_paper(state["config"]))

    def build_summary(self, log: ParsedLog) -> str:
        lines = []
        lines.append("Dados do Log")
        lines.append("")
        lines.append("Arquivo:")
        lines.append(f"{Path(log.source_path).name}")
        lines.append("")
        lines.append("Documento:")
        lines.append(f"{log.document}")
        lines.append("")
        lines.append("Job ID:")
        lines.append(f"{log.job_id or '—'}")
        lines.append("")
        lines.append("Computador de origem:")
        lines.append(f"{log.computer_name or '—'}")
        lines.append("")
        lines.append("Driver:")
        lines.append(f"{log.driver or '—'}")
        lines.append("")
        lines.append("Versão do software:")
        lines.append(f"{log.software_version or '—'}")
        lines.append("")
        lines.append("Tecido inferido:")
        lines.append(f"{log.fabric_inferred}")
        lines.append("")
        lines.append("Papel aplicado:")
        lines.append(f"{log.paper_name or '—'}")
        lines.append("")
        lines.append("Início:")
        lines.append(f"{log.start_time or '—'}")
        lines.append("")
        lines.append("Fim:")
        lines.append(f"{log.end_time or '—'}")
        lines.append("")
        lines.append("Tempo de impressão:")
        lines.append(f"{fmt_seconds(log.duration_seconds)}")
        lines.append("")
        lines.append("Velocidade média:")
        lines.append(f"{fmt_speed(log.speed_m_per_min)}")
        lines.append("")
        lines.append("Área impressa:")
        lines.append(f"{fmt_m2(log.printed_area_m2)}")
        lines.append("")
        lines.append("Metro linear impresso:")
        lines.append(f"{fmt_m_no_suffix(log.paper_linear_m)}")
        lines.append("")
        lines.append("Metragem de papel utilizada:")
        lines.append(f"{fmt_m(log.paper_used_length_m)}")
        lines.append("")
        lines.append("Área de papel utilizada:")
        lines.append(f"{fmt_m2(log.paper_used_area_m2)}")
        lines.append("")
        lines.append("Largura efetivamente usada:")
        lines.append(f"{fmt_m(log.width_printed_m)}")
        lines.append("")
        lines.append("Espaço antes da impressão:")
        lines.append(f"{fmt_m(log.gap_before_m)}")
        if log.gap_after_m is not None and log.gap_after_m > 0:
            lines.append("")
            lines.append("Espaço depois da impressão:")
            lines.append(f"{fmt_m(log.gap_after_m)}")
        lines.append("")
        lines.append("Papel até o fim da impressão:")
        lines.append(f"{fmt_m(log.total_paper_until_end_m)}")
        lines.append("")
        lines.append("Tinta total estimada:")
        lines.append(f"{fmt_ml(log.ink_total_ml)}")
        for ch in INK_ORDER:
            ml = log.ink_ml.get(ch, 0.0)
            pct = (ml / log.ink_total_ml * 100.0) if log.ink_total_ml > 0 else 0.0
            lines.append("")
            lines.append(f"Tinta {ch}:")
            lines.append(f"{fmt_ml(ml)} | participação {fmt_pct(pct)}")
        lines.append("")
        lines.append("Consumo por metro:")
        lines.append(f"{fmt_ml(log.ink_ml_per_meter)}")
        lines.append("")
        lines.append("Consumo por m²:")
        lines.append(f"{fmt_ml(log.ink_ml_per_m2)}")
        lines.append("")
        lines.append("Custo estimado do papel:")
        lines.append(f"{fmt_money(log.cost_paper)}")
        lines.append("")
        lines.append("Custo estimado de tinta:")
        lines.append(f"{fmt_money(log.cost_ink)}")
        lines.append("")
        lines.append("Custo total estimado:")
        lines.append(f"{fmt_money(log.cost_total)}")
        return "\n".join(lines)

    def build_raw_summary(self, log: ParsedLog) -> str:
        out = []
        out.append("Campos brutos do log")
        out.append("")
        for section_name, section_data in log.raw_sections.items():
            out.append(f"[{section_name}]")
            if not section_data:
                out.append("(vazio)")
            else:
                for k, v in section_data.items():
                    out.append(f"{k} = {v}")
            out.append("")
        return "\n".join(out)

    def build_consolidated_summary(self) -> str:
        logs = self.logs
        if not logs:
            return "Dados dos Logs Carregados\n\nNenhum log carregado."

        total_logs = len(logs)
        total_area = sum(x.printed_area_m2 for x in logs)
        total_linear = sum(x.paper_linear_m for x in logs)
        total_used = sum(x.paper_used_length_m for x in logs)
        total_used_area = sum(x.paper_used_area_m2 for x in logs)
        total_gap_before = sum(x.gap_before_m for x in logs)
        total_gap_after = sum(x.gap_after_m for x in logs if x.gap_after_m is not None)
        total_ink = sum(x.ink_total_ml for x in logs)
        total_seconds = sum(x.duration_seconds for x in logs)
        total_cost_paper = sum(x.cost_paper for x in logs)
        total_cost_ink = sum(x.cost_ink for x in logs)
        total_cost = sum(x.cost_total for x in logs)
        avg_speed = (total_linear / (total_seconds / 60.0)) if total_seconds > 0 else 0.0

        lines = []
        lines.append("Dados dos Logs Carregados")
        lines.append("")
        lines.append("Quantidade de logs:")
        lines.append(f"{total_logs}")
        lines.append("")
        lines.append("Área total impressa:")
        lines.append(f"{fmt_m2(total_area)}")
        lines.append("")
        lines.append("Metro linear total impresso:")
        lines.append(f"{fmt_m_no_suffix(total_linear)}")
        lines.append("")
        lines.append("Metragem total de papel utilizada:")
        lines.append(f"{fmt_m(total_used)}")
        lines.append("")
        lines.append("Área total de papel utilizada:")
        lines.append(f"{fmt_m2(total_used_area)}")
        lines.append("")
        lines.append("Espaço total antes da impressão:")
        lines.append(f"{fmt_m(total_gap_before)}")
        if any(x.gap_after_m is not None and x.gap_after_m > 0 for x in logs):
            lines.append("")
            lines.append("Espaço total depois da impressão:")
            lines.append(f"{fmt_m(total_gap_after)}")
        lines.append("")
        lines.append("Tinta total estimada:")
        lines.append(f"{fmt_ml(total_ink)}")
        lines.append("")
        lines.append("Tempo total de impressão:")
        lines.append(f"{fmt_seconds(total_seconds)}")
        lines.append("")
        lines.append("Velocidade média dos jobs:")
        lines.append(f"{fmt_speed(avg_speed)}")
        lines.append("")
        lines.append("Custo total estimado do papel:")
        lines.append(f"{fmt_money(total_cost_paper)}")
        lines.append("")
        lines.append("Custo total estimado de tinta:")
        lines.append(f"{fmt_money(total_cost_ink)}")
        lines.append("")
        lines.append("Custo total estimado geral:")
        lines.append(f"{fmt_money(total_cost)}")
        return "\n".join(lines)


def create_root():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    return ctk.CTk()


def main():
    root = create_root()
    LogConsultorDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()