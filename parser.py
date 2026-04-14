from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .formatters import safe_float, safe_int
from .models import INK_ORDER, LogItem, ParsedLog

RE_SECTION = re.compile(r"^\s*\[(.+?)\]\s*$")
RE_KV = re.compile(r"^\s*([^=]+?)\s*=\s*(.*?)\s*$")


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


def parse_sections(path: str | Path) -> Dict[str, Dict[str, str]]:
    p = Path(path)
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()

    sections: Dict[str, Dict[str, str]] = {}
    current_section: Optional[str] = None

    for line in lines:
        match_section = RE_SECTION.match(line)
        if match_section:
            current_section = match_section.group(1).strip()
            sections[current_section] = sections.get(current_section, {})
            continue

        match_kv = RE_KV.match(line)
        if not match_kv or not current_section:
            continue

        key = match_kv.group(1).strip()
        value = match_kv.group(2).strip()
        sections[current_section][key] = value

    return sections


def build_log_item(item_section: Dict[str, str], fallback_name: str = "") -> LogItem:
    item = LogItem()
    item.name = item_section.get("Name", fallback_name)

    item.h_position_mm = safe_float(item_section.get("HPositionMM", 0), 0.0)
    item.v_position_mm = safe_float(item_section.get("VPositionMM", 0), 0.0)
    item.width_mm = safe_float(item_section.get("WidthMM", 0), 0.0)
    item.height_mm = safe_float(item_section.get("HeightMM", 0), 0.0)

    item.width_dots = safe_int(item_section.get("Width_Dots", 0), 0)
    item.height_dots = safe_int(item_section.get("Height_Dots", 0), 0)

    item.gray_icc = item_section.get("GrayIcc", "")
    item.rgb_icc = item_section.get("RgbIcc", "")
    item.cmyk_icc = item_section.get("CmykIcc", "")
    item.proofing_icc = item_section.get("ProofingIcc", "")

    item.brightness = item_section.get("Brightness", "")
    item.contrast = item_section.get("Contrast", "")
    item.saturation = item_section.get("Saturation", "")
    item.color_replacement = item_section.get("ColorReplacement", "")

    for channel in INK_ORDER:
        item.kdots[channel] = [
            safe_int(item_section.get(f"KDots[{channel}][1]", 0), 0),
            safe_int(item_section.get(f"KDots[{channel}][2]", 0), 0),
            safe_int(item_section.get(f"KDots[{channel}][3]", 0), 0),
        ]

    return item


def parse_log_file(path: str | Path) -> ParsedLog:
    p = Path(path)
    sections = parse_sections(p)

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
        raw_sections=sections,
    )

    parsed.computer_name = general.get("ComputerName", "")
    parsed.software_version = general.get("SoftwareVersion", "")
    parsed.job_id = general.get("JobID", "")
    parsed.document = general.get("Document", "") or item1.get("Name", p.name)
    parsed.file_count = safe_int(general.get("FileCount", 0), 0)
    parsed.start_time = general.get("StartTime", "")
    parsed.end_time = general.get("EndTime", "")
    parsed.driver = general.get("Driver", "")
    parsed.copy = safe_int(general.get("Copy", 0), 0)
    parsed.total_copies = safe_int(general.get("TotalCopies", 0), 0)
    parsed.units = general.get("Units", "")

    parsed.page_width_mm = safe_float(costs.get("PageWidthMM", 0), 0.0)
    parsed.print_width_mm = safe_float(costs.get("PrintWidthMM", 0), 0.0)
    parsed.print_height_mm = safe_float(costs.get("PrintHeightMM", 0), 0.0)
    parsed.print_width_dots = safe_int(costs.get("PrintWidth_Dots", 0), 0)
    parsed.print_height_dots = safe_int(costs.get("PrintHeight_Dots", 0), 0)
    parsed.bits_per_pixel = safe_int(costs.get("BitsPerPixel", 0), 0)

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

    for channel in INK_ORDER:
        parsed.ink_ml[channel] = safe_float(costs.get(f"InkML[{channel}]", 0), 0.0)
        parsed.ink_drop_sizes[channel] = parse_drop_sizes(costs.get(f"InkDropsizes[{channel}]", ""))
        parsed.kdots_costs[channel] = [
            safe_int(costs.get(f"KDots[{channel}][1]", 0), 0),
            safe_int(costs.get(f"KDots[{channel}][2]", 0), 0),
            safe_int(costs.get(f"KDots[{channel}][3]", 0), 0),
        ]

    parsed.item = build_log_item(item1, fallback_name=parsed.document)

    start_dt = parse_datetime(parsed.start_time)
    end_dt = parse_datetime(parsed.end_time)
    if start_dt and end_dt and end_dt >= start_dt:
        parsed.duration_seconds = int((end_dt - start_dt).total_seconds())

    parsed.fabric_inferred = infer_fabric(parsed.document)

    return parsed