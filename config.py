from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .formatters import safe_float
from .models import INK_ORDER, PaperConfig

CONFIG_PATH = Path("log_consultor.config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
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


def build_default_config() -> Dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_CONFIG))


def ensure_papers(config: Dict[str, Any]) -> Dict[str, Any]:
    papers_raw = config.get("papers")
    if not isinstance(papers_raw, list) or not papers_raw:
        config["papers"] = build_default_config()["papers"]
        return config

    normalized: List[Dict[str, Any]] = []
    has_default = False

    for index, raw in enumerate(papers_raw, start=1):
        if not isinstance(raw, dict):
            continue

        paper = {
            "id": str(raw.get("id") or f"paper-{index}"),
            "name": str(raw.get("name") or f"Papel {index}").strip(),
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
        normalized = build_default_config()["papers"]

    if not any(p["is_default"] for p in normalized):
        normalized[0]["is_default"] = True

    config["papers"] = normalized
    return config


def ensure_ink_costs(config: Dict[str, Any]) -> Dict[str, Any]:
    ink_costs = config.get("ink_cost_per_liter")
    if not isinstance(ink_costs, dict):
        config["ink_cost_per_liter"] = build_default_config()["ink_cost_per_liter"]
        return config

    normalized = {}
    for channel in INK_ORDER:
        normalized[channel] = safe_float(ink_costs.get(channel), 0.0)

    config["ink_cost_per_liter"] = normalized
    return config


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = build_default_config()
    normalized.update({k: v for k, v in config.items() if k in normalized})
    normalized = ensure_papers(normalized)
    normalized = ensure_ink_costs(normalized)
    return normalized


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        config = build_default_config()
        save_config(config)
        return config

    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}

    return normalize_config(raw)


def save_config(config: Dict[str, Any]) -> None:
    normalized = normalize_config(config)
    CONFIG_PATH.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_papers(config: Dict[str, Any]) -> List[PaperConfig]:
    papers = config.get("papers", [])
    return [PaperConfig.from_dict(item) for item in papers if isinstance(item, dict)]


def get_default_paper(config: Dict[str, Any]) -> PaperConfig:
    papers = get_papers(config)
    for paper in papers:
        if paper.is_default:
            return paper
    return papers[0]


def get_paper_by_id(config: Dict[str, Any], paper_id: str) -> Optional[PaperConfig]:
    for paper in get_papers(config):
        if paper.id == paper_id:
            return paper
    return None


def set_default_paper(config: Dict[str, Any], paper_id: str) -> Dict[str, Any]:
    normalized = normalize_config(config)
    found = False

    for paper in normalized["papers"]:
        is_match = paper.get("id") == paper_id
        paper["is_default"] = is_match
        if is_match:
            found = True

    if not found and normalized["papers"]:
        normalized["papers"][0]["is_default"] = True

    return normalized


def paper_display_name(paper: PaperConfig) -> str:
    suffix = " (padrão)" if paper.is_default else ""
    return f"{paper.name}{suffix}"