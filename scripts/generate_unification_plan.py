#!/usr/bin/env python3
"""Validate and render planning metadata; never connect to a data source or DB."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODES = {
    "entity_records": "Registros de entidades e fatos",
    "aggregate_series": "Séries e estatísticas agregadas",
    "geospatial": "Dados geoespaciais",
    "document_evidence": "Documentos e evidências",
    "derived_view": "Visão secundária/derivada",
    "catalog_discovery": "Descoberta de recursos",
    "restricted_access": "Acesso condicionado/restrito",
}


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def nonempty_strings(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def validate(plan: dict, mapping: dict, source_plan: dict, root: Path = ROOT) -> None:
    """Check coverage and planning contracts independently of runtime readiness."""
    require(plan["status"] == mapping["status"] == "planning", "Status deve ser planning")
    registry = root / "docs/source_registry_br_v1.csv"
    rows = list(csv.DictReader(registry.read_text(encoding="utf-8").splitlines()))
    expected_ids = {row["source_id"] for row in rows}
    require(len(rows) == len(expected_ids), "IDs duplicados no catálogo")
    require(mapping["registry_sha256"] == hashlib.sha256(registry.read_bytes()).hexdigest(),
            "Revisão do catálogo desatualizada")
    source_path = root / plan["source_plan"]
    require(mapping["source_plan_sha256"] == hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "Revisão das fichas desatualizada")
    source_by_id = {source["source_id"]: source for source in source_plan["sources"]}
    require(set(source_by_id) == expected_ids, "Fichas e catálogo divergem")
    sources = mapping["sources"]
    ids = [source["source_id"] for source in sources]
    require(len(ids) == len(set(ids)) and set(ids) == expected_ids,
            "Mapa deve cobrir todos os IDs exatamente uma vez")
    scope = plan["scope"]
    require(scope["registered_sources"] == len(rows), "Contagem de fontes divergente")
    require(scope["public_universe_sources"] == sum(
        row["in_universe_v1"].lower() == "true" for row in rows
    ), "Contagem pública divergente")
    require(scope["current_pipeline_modules"] == sum(
        row["implementation_state"] == "implemented" for row in rows
    ), "Contagem de módulos divergente")
    require(scope["crossing_plans"] == len(source_plan["patterns"]),
            "Contagem de cruzamentos divergente")
    family_ids = [family["id"] for family in mapping["families"]]
    require(len(family_ids) == len(set(family_ids)), "Famílias duplicadas")
    for family in mapping["families"]:
        require(family["title"] and family["integration_goal"], "Família sem objetivo")
    for source in sources:
        sid = source["source_id"]
        require(source["family_id"] in family_ids, f"Família desconhecida: {sid}")
        require(source["integration_mode"] in MODES, f"Modo desconhecido: {sid}")
        for field in ["entity_targets", "join_keys", "blockers"]:
            require(nonempty_strings(source[field]), f"{sid}: falta {field}")
        require(isinstance(source["notes"], str) and source["notes"].strip(),
                f"{sid}: falta contexto")
        planned_labels = {node["label"] for node in source_by_id[sid]["ingestion"]["graph_nodes"]}
        require(set(source["entity_targets"]) <= planned_labels,
                f"{sid}: label não descrita na ficha de origem")
        require((root / f"docs/implementation/sources/{sid}.md").is_file(),
                f"{sid}: ficha ausente")
    for old_mode, new_mode in [("restricted", "restricted_access"),
                               ("catalog_only", "catalog_discovery")]:
        expected = {sid for sid, source in source_by_id.items()
                    if source["implementation"]["mode"] == old_mode}
        actual = {source["source_id"] for source in sources
                  if source["integration_mode"] == new_mode}
        require(actual == expected, f"Modo {new_mode} diverge do plano das fontes")
    phases = plan["phases"]
    by_phase = {phase["id"]: phase for phase in phases}
    require(len(phases) == len(by_phase) and set(by_phase) == {
        f"U{number:02d}" for number in range(1, 13)
    }, "Etapas U01–U12 devem ser únicas e completas")
    existing_backlog = json.loads((root / "config/github_backlog.json").read_text())
    existing_keys = {issue["key"] for issue in existing_backlog["issues"]}
    for phase in phases:
        pid = phase["id"]
        require(phase["status"] == "planned", f"{pid}: estado não planejado")
        require(phase["owner_role"] and phase["relative_effort"] in {"S", "M", "L", "XL"},
                f"{pid}: responsabilidade/esforço ausente")
        for field in ["tasks", "acceptance", "current_evidence", "proposed_deliverables"]:
            require(nonempty_strings(phase[field]), f"{pid}: falta {field}")
        for path in phase["current_evidence"]:
            require((root / path).exists(), f"{pid}: evidência atual não existe: {path}")
        require(all(ref["key"] in existing_keys and isinstance(ref["number"], int)
                    for ref in phase["existing_issues"]), f"{pid}: issue de origem inválida")
        require(all(dep in by_phase for dep in phase["depends_on"]),
                f"{pid}: dependência desconhecida")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(pid: str) -> None:
        require(pid not in visiting, f"Ciclo de etapas em {pid}")
        if pid in visited:
            return
        visiting.add(pid)
        for dependency in by_phase[pid]["depends_on"]:
            visit(dependency)
        visiting.remove(pid)
        visited.add(pid)

    for pid in by_phase:
        visit(pid)
    for path in plan["documentation"]:
        if path not in {"docs/unification/roadmap.md", "docs/unification/source-map.md"}:
            require((root / path).is_file(), f"Documentação ausente: {path}")


def cell(value: str) -> str:
    return value.replace("|", " / ").replace("\n", " ")


def render_roadmap(plan: dict) -> str:
    lines = ["# Etapas de implementação da unificação", "",
             "Gerado de `config/unification_plan.json`. Estado: **planejamento**.", "",
             "F00 ([issue #1](https://github.com/bdwerlang/brasil-em-rede/issues/1)) "
             "trata as dependências antes da introdução dos novos serviços e de release. "
             "Inventário e desenho podem ocorrer em paralelo.", "",
             "As dependências definem a ordem; trabalhos independentes podem ocorrer "
             "em paralelo conforme equipe e recursos. M/L/XL expressam esforço relativo, "
             "sem compromisso de datas. Papéis são propostos, ainda sem pessoas atribuídas.", "",
             "| Etapa | Depende de | Papel responsável | Esforço |", "|---|---|---|---|"]
    for phase in plan["phases"]:
        lines.append(f'| [{phase["id"]} — {phase["title"]}](#{phase["id"].lower()}) | '
                     f'{", ".join(phase["depends_on"]) or "Inventário inicial"} | '
                     f'{phase["owner_role"]} | {phase["relative_effort"]} |')
    for phase in plan["phases"]:
        lines += ["", f'<a id="{phase["id"].lower()}"></a>', "",
                  f'## {phase["id"]} — {phase["title"]}', "",
                  "Backlog existente: " + ", ".join(
                      f'[{ref["key"]} / #{ref["number"]}]'
                      f'(https://github.com/{plan["repository"]}/issues/{ref["number"]})'
                      for ref in phase["existing_issues"]
                  ) + ".", "", "Trabalho:", ""]
        lines += [f"- {task}" for task in phase["tasks"]]
        lines += ["", "Entregáveis propostos:", ""]
        lines += [f"- `{path}`" for path in phase["proposed_deliverables"]]
        lines += ["", "Evidência atual:", ""]
        lines += [f"- [{path}](../../{path})" for path in phase["current_evidence"]]
        lines += ["", "Critérios de aceite:", ""]
        lines += [f"- [ ] {item}" for item in phase["acceptance"]]
    return "\n".join(lines) + "\n"


def render_sources(mapping: dict) -> str:
    families = {family["id"]: family for family in mapping["families"]}
    counts = Counter(source["family_id"] for source in mapping["sources"])
    modes = Counter(source["integration_mode"] for source in mapping["sources"])
    lines = ["# Mapa de integração de todas as fontes", "",
             f'**{len(mapping["sources"])} fontes em {len(families)} famílias**. '
             "Estado: planejamento, sem carga certificada.", "",
             "Gerado de [source_unification_map.json](../../config/source_unification_map.json), "
             "que também registra todas as chaves de ligação, bloqueios e notas por fonte.", "",
             "O modo é a rota principal; fontes mistas exigem contratos separados por dataset. "
             "Alvos listados são labels descritas nas fichas atuais, existentes ou propostas, "
             "não uma afirmação de implementação. A projeção final segue o "
             "[modelo comum](canonical-model.md).", "", "## Famílias", "",
             "| Família | Fontes | Objetivo de integração |", "|---|---|---|"]
    for family in mapping["families"]:
        lines.append(f'| {family["title"]} | {counts[family["id"]]} | '
                     f'{cell(family["integration_goal"])} |')
    lines += ["", "## Rotas principais", "", "| Rota | Fontes |", "|---|---|"]
    lines += [f"| {title} | {modes[mode]} |" for mode, title in MODES.items()]
    lines += ["", "## Mapa individual", "",
              "| Fonte / ficha de aquisição | Família | Rota principal | "
              "Alvos na ficha | Chave/grão |",
              "|---|---|---|---|---|"]
    for source in sorted(mapping["sources"], key=lambda item: item["source_id"]):
        sid = source["source_id"]
        lines.append(f'| [{sid}](../implementation/sources/{sid}.md) | '
                     f'{families[source["family_id"]]["title"]} | '
                     f'{MODES[source["integration_mode"]]} | '
                     f'{cell(", ".join(source["entity_targets"]))} | '
                     f'{cell(source["join_keys"][0])} |')
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        plan = json.loads((ROOT / "config/unification_plan.json").read_text())
        mapping = json.loads((ROOT / plan["source_mapping"]).read_text())
        sources = json.loads((ROOT / plan["source_plan"]).read_text())
        validate(plan, mapping, sources)
        outputs = {"docs/unification/roadmap.md": render_roadmap(plan),
                   "docs/unification/source-map.md": render_sources(mapping)}
        for relative, content in outputs.items():
            path = ROOT / relative
            if args.check:
                require(path.exists() and path.read_text() == content,
                        f"Arquivo gerado desatualizado: {relative}")
            else:
                path.write_text(content, encoding="utf-8")
    except (KeyError, ValueError, TypeError, OSError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f'PASS: {len(mapping["sources"])} fontes; {len(mapping["families"])} famílias; '
          f'{len(plan["phases"])} etapas sem ciclos')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
