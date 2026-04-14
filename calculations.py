from __future__ import annotations

from typing import Dict, Any, Optional

from .config import get_default_paper, get_paper_by_id
from .formatters import safe_float
from .models import INK_ORDER, ParsedLog, PaperConfig


def compute_log_metrics(log: ParsedLog) -> ParsedLog:
    """
    Calcula todos os campos derivados do log bruto.
    Pode ser chamado logo após o parser.
    """
    item = log.item

    # dimensão impressa real
    log.actual_printed_length_m = item.height_mm / 1000.0 if item.height_mm > 0 else log.print_height_mm / 1000.0
    log.width_printed_m = item.width_mm / 1000.0 if item.width_mm > 0 else log.print_width_mm / 1000.0

    # área efetivamente impressa
    if log.actual_printed_length_m > 0 and log.width_printed_m > 0:
        log.printed_area_m2 = log.actual_printed_length_m * log.width_printed_m
    else:
        log.printed_area_m2 = 0.0

    # espaços antes/depois
    log.gap_before_m = item.v_position_mm / 1000.0 if item.v_position_mm > 0 else 0.0
    log.paper_linear_m = log.actual_printed_length_m
    log.paper_used_length_m = log.actual_printed_length_m + log.gap_before_m

    log.gap_after_m = None
    if log.print_height_mm > 0 and item.height_mm > 0 and item.v_position_mm > 0:
        remaining_mm = log.print_height_mm - (item.v_position_mm + item.height_mm)
        if remaining_mm > 0:
            log.gap_after_m = remaining_mm / 1000.0

    if log.gap_after_m is not None and log.gap_after_m > 0:
        log.total_paper_until_end_m = log.paper_used_length_m + log.gap_after_m
    else:
        log.total_paper_until_end_m = log.paper_used_length_m

    # tinta total
    log.ink_total_ml = sum(log.ink_ml.get(ch, 0.0) for ch in INK_ORDER)

    # velocidade
    if log.duration_seconds > 0 and log.actual_printed_length_m > 0:
        log.speed_m_per_min = log.actual_printed_length_m / (log.duration_seconds / 60.0)
    else:
        log.speed_m_per_min = 0.0

    # consumo por metro e por área
    if log.actual_printed_length_m > 0:
        log.ink_ml_per_meter = log.ink_total_ml / log.actual_printed_length_m
    else:
        log.ink_ml_per_meter = 0.0

    if log.printed_area_m2 > 0:
        log.ink_ml_per_m2 = log.ink_total_ml / log.printed_area_m2
    else:
        log.ink_ml_per_m2 = 0.0

    # ocupação de largura e margens
    if log.print_width_mm > 0 and item.width_mm > 0:
        log.width_occupancy_pct = (item.width_mm / log.print_width_mm) * 100.0
        log.left_margin_mm = item.h_position_mm
        log.right_margin_mm = max(log.print_width_mm - item.width_mm - item.h_position_mm, 0.0)
    else:
        log.width_occupancy_pct = 0.0
        log.left_margin_mm = 0.0
        log.right_margin_mm = 0.0

    return log


def _resolve_paper(config: Dict[str, Any], paper_id: Optional[str]) -> PaperConfig:
    paper = None
    if paper_id:
        paper = get_paper_by_id(config, paper_id)
    if paper is None:
        paper = get_default_paper(config)
    return paper


def apply_costs(log: ParsedLog, config: Dict[str, Any], paper_id: Optional[str] = None) -> ParsedLog:
    """
    Aplica papel e custos ao log.
    Também calcula área de papel utilizada com base na largura do papel escolhido.
    """
    paper = _resolve_paper(config, paper_id or log.paper_id)

    log.paper_id = paper.id
    log.paper_name = paper.name

    paper_width_m = safe_float(paper.width_m, 0.0)
    grammage = safe_float(paper.grammage_gm2, 0.0)
    cost_per_linear_meter = safe_float(paper.cost_per_linear_meter, 0.0)
    cost_per_kg = safe_float(paper.cost_per_kg, 0.0)
    use_cost_per_kg = bool(paper.use_cost_per_kg)

    # área real de papel usada conforme largura do papel cadastrado
    if paper_width_m > 0 and log.paper_used_length_m > 0:
        log.paper_used_area_m2 = paper_width_m * log.paper_used_length_m
    else:
        log.paper_used_area_m2 = 0.0

    # custo do papel
    if use_cost_per_kg and paper_width_m > 0 and grammage > 0 and log.paper_used_length_m > 0:
        kg = (paper_width_m * log.paper_used_length_m * grammage) / 1000.0
        log.cost_paper = kg * cost_per_kg
    else:
        log.cost_paper = log.paper_used_length_m * cost_per_linear_meter

    # custo de tinta
    ink_costs = config.get("ink_cost_per_liter", {})
    ink_total_cost = 0.0
    for ch in INK_ORDER:
        ml = log.ink_ml.get(ch, 0.0)
        cost_per_liter = safe_float(ink_costs.get(ch, 0.0), 0.0)
        ink_total_cost += (ml / 1000.0) * cost_per_liter

    log.cost_ink = ink_total_cost
    log.cost_total = log.cost_paper + log.cost_ink
    return log


def enrich_log(log: ParsedLog, config: Dict[str, Any], paper_id: Optional[str] = None) -> ParsedLog:
    """
    Pipeline completo para um log:
    1. métricas derivadas
    2. papel/custos
    """
    compute_log_metrics(log)
    apply_costs(log, config, paper_id)
    return log


def recalculate_logs(logs: list[ParsedLog], config: Dict[str, Any]) -> list[ParsedLog]:
    """
    Recalcula todos os logs preservando o papel já aplicado quando possível.
    """
    for log in logs:
        enrich_log(log, config, log.paper_id)
    return logs


def summarize_logs(logs: list[ParsedLog]) -> Dict[str, float]:
    """
    Resumo numérico consolidado para cards e painéis.
    """
    return {
        "total_logs": float(len(logs)),
        "total_printed_area_m2": sum(x.printed_area_m2 for x in logs),
        "total_linear_m": sum(x.paper_linear_m for x in logs),
        "total_paper_used_length_m": sum(x.paper_used_length_m for x in logs),
        "total_paper_used_area_m2": sum(x.paper_used_area_m2 for x in logs),
        "total_gap_before_m": sum(x.gap_before_m for x in logs),
        "total_gap_after_m": sum(x.gap_after_m for x in logs if x.gap_after_m is not None),
        "total_ink_ml": sum(x.ink_total_ml for x in logs),
        "total_duration_seconds": float(sum(x.duration_seconds for x in logs)),
        "total_cost_paper": sum(x.cost_paper for x in logs),
        "total_cost_ink": sum(x.cost_ink for x in logs),
        "total_cost": sum(x.cost_total for x in logs),
    }


def average_speed_m_per_min(logs: list[ParsedLog]) -> float:
    total_linear = sum(x.paper_linear_m for x in logs)
    total_seconds = sum(x.duration_seconds for x in logs)
    if total_seconds <= 0:
        return 0.0
    return total_linear / (total_seconds / 60.0)