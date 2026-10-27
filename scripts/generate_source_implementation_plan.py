#!/usr/bin/env python3
"""Validate and render the per-source implementation roadmap without network access."""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

MODES = {
    "harden_existing": "Completar e corrigir pipeline existente",
    "new_pipeline": "Implementar conector e pipeline",
    "catalog_only": "Descoberta de recursos do catálogo",
    "restricted": "Acesso condicionado / restrito",
}
WAVES = {
    1: "Identidade, dimensões e bases essenciais",
    2: "Contratos, emendas, repasses e despesas",
    3: "Eleições, mandatos e governança",
    4: "Fiscal, crédito e mercado",
    5: "Ambiente, serviços e estatísticas",
    6: "Justiça e fontes internacionais",
    7: "Estados, municípios e cobertura territorial",
    8: "Catálogos e acessos condicionados",
}


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def bullets(items: list[str], *, numbered: bool = False, checks: bool = False) -> str:
    prefix = "1." if numbered else "- [ ]" if checks else "-"
    return "\n".join(f"{prefix} {item}" for item in items)


def require_text(value: object, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing text: {context}")


def require_list(value: object, context: str, minimum: int = 1) -> None:
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"Expected list with at least {minimum} items: {context}")


def validate(root: Path, plan: dict, registry: dict[str, dict]) -> tuple[list[str], dict[str, int]]:
    sources = plan["sources"]
    ids = [source["source_id"] for source in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source_id in implementation plan")
    if set(ids) != set(registry):
        raise ValueError(
            f"Coverage mismatch: missing={sorted(set(registry) - set(ids))}, "
            f"extra={sorted(set(ids) - set(registry))}"
        )
    profiles = {source["source_id"]: source for source in sources}
    for sid, source in profiles.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", sid):
            raise ValueError(f"Unsafe source_id: {sid}")
        require_text(source["objective"], sid + ".objective")
        impl = source["implementation"]
        if impl["mode"] not in MODES or impl["complexity"] not in {"S", "M", "L", "XL"}:
            raise ValueError(f"Invalid mode or complexity: {sid}")
        if type(impl["wave"]) is not int or impl["wave"] not in WAVES:
            raise ValueError(f"Invalid wave: {sid}")
        for key, minimum in [("tasks", 3), ("acceptance", 3), ("deliverables", 1)]:
            require_list(impl[key], sid + "." + key, minimum)
            for item in impl[key]:
                require_text(item, sid + "." + key)
        require_list(source["evidence"], sid + ".evidence")
        require_list(source["risks"], sid + ".risks")
        for artifact in source["current_artifacts"]:
            if not (root / artifact["path"]).exists():
                raise ValueError(f"Claimed existing artifact is absent: {sid}: {artifact['path']}")
            require_text(artifact["role"], sid + ".artifact.role")
        download = source["download"]
        require_list(download["entrypoints"], sid + ".entrypoints")
        for entry in download["entrypoints"]:
            url = urlsplit(entry["url"])
            if url.scheme not in {"http", "https", "ftp"} or not url.netloc:
                raise ValueError(f"Invalid entrypoint URL: {sid}: {entry['url']}")
            require_text(entry["purpose"], sid + ".entrypoint.purpose")
            require_text(entry["evidence"], sid + ".entrypoint.evidence")
        for key in ["method", "authentication", "partitioning", "resume", "raw_format", "refresh"]:
            require_text(download[key], sid + ".download." + key)
        require_list(download["known_limits"], sid + ".known_limits")
        ingestion = source["ingestion"]
        require_text(ingestion["input_contract"], sid + ".input_contract")
        require_text(ingestion["natural_key"], sid + ".natural_key")
        require_list(ingestion["normalization"], sid + ".normalization")
        require_list(ingestion["graph_nodes"], sid + ".graph_nodes")
        require_list(ingestion["graph_relationships"], sid + ".graph_relationships",
                     0 if impl["mode"] in {"restricted", "catalog_only"} else 1)
        for node in ingestion["graph_nodes"]:
            if node["status"] not in {"existing", "proposed"}:
                raise ValueError(f"Invalid node status: {sid}")
            for key in ["label", "key"]:
                require_text(node[key], sid + ".node." + key)
        for relation in ingestion["graph_relationships"]:
            if relation["status"] not in {"existing", "proposed"}:
                raise ValueError(f"Invalid relationship status: {sid}")
            for key in ["from", "type", "to", "join", "rule"]:
                require_text(relation[key], sid + ".relationship." + key)
        deps = source["dependencies"]
        require_list(deps, sid + ".dependencies", 0)
        if len(deps) != len(set(deps)) or sid in deps or set(deps) - set(registry):
            raise ValueError(f"Invalid dependencies: {sid}: {deps}")
    if "patterns" in plan:
        tree = ast.parse((root / "api/src/bracc/models/pattern.py").read_text())
        metadata = next(ast.literal_eval(node.value) for node in tree.body
                        if isinstance(node, ast.AnnAssign)
                        and isinstance(node.target, ast.Name) and node.target.id == "PATTERN_METADATA")
        patterns = plan["patterns"]
        pids = [pattern["pattern_id"] for pattern in patterns]
        if len(pids) != len(set(pids)) or set(pids) != set(metadata):
            raise ValueError("Pattern plan must cover every PATTERN_METADATA entry exactly once")
        for pattern in patterns:
            for key in ["status", "joins", "temporal", "work", "positive_case", "negative_case"]:
                require_text(pattern[key], pattern["pattern_id"] + "." + key)
            require_list(pattern["source_groups"], pattern["pattern_id"] + ".source_groups")
            for group in pattern["source_groups"]:
                if not group or set(group) - set(registry):
                    raise ValueError(f"Invalid pattern source group: {pattern['pattern_id']}: {group}")
            if pattern.get("query_path") and not (root / pattern["query_path"]).is_file():
                raise ValueError(f"Pattern query is absent: {pattern['query_path']}")
    order: list[str] = []
    effective_waves: dict[str, int] = {}
    remaining = set(profiles)
    while remaining:
        ready = sorted(
            (sid for sid in remaining if set(profiles[sid]["dependencies"]) <= set(order)),
            key=lambda sid: (profiles[sid]["implementation"]["wave"], sid),
        )
        if not ready:
            raise ValueError(f"Dependency cycle: {sorted(remaining)}")
        # Consume one ready source at a time so newly released low-wave work is prioritized.
        sid = ready[0]
        effective_waves[sid] = max(
            [profiles[sid]["implementation"]["wave"]]
            + [effective_waves[dep] for dep in profiles[sid]["dependencies"]]
        )
        order.append(sid)
        remaining.remove(sid)
    return order, effective_waves


def source_doc(source: dict, row: dict, number: int, wave: int) -> str:
    sid = source["source_id"]
    impl = source["implementation"]
    download = source["download"]
    ingestion = source["ingestion"]
    artifacts = "\n".join(
        f"- [{a['path']}](../../../{a['path']}): {a['role']}"
        for a in source["current_artifacts"]
    ) or "Nenhum conector específico confirmado; reutilizar somente os componentes citados nas referências."
    endpoints = "\n".join(
        f"| [{cell(e['url'])}]({e['url']}) | {cell(e['purpose'])} | {cell(e['evidence'])} |"
        for e in download["entrypoints"]
    )
    nodes = "\n".join(
        f"| `{cell(n['label'])}` | {cell(n['key'])} | {n['status']} |"
        for n in ingestion["graph_nodes"]
    )
    relationships = "\n".join(
        f"| `{cell(r['from'])}` → `{cell(r['type'])}` → `{cell(r['to'])}` | "
        f"{cell(r['join'])} | {cell(r['rule'])} | {r['status']} |"
        for r in ingestion["graph_relationships"]
    ) or "| Sem relação nominal prevista | — | Registrar recurso/estatística conforme contrato; não inferir identidade | proposed |"
    deps = ", ".join(f"[{dep}]({dep}.md)" for dep in source["dependencies"]) or "Sem dependência obrigatória de outra fonte."
    evidence = "\n".join(
        f"- [{item}]({item})" if urlsplit(item).scheme in {"http", "https", "ftp"}
        else f"- `{item}`"
        for item in source["evidence"]
    )
    return f"""# {sid} — {row['name']}

{source['objective']}

[Índice geral](../README.md) · [Arquitetura e regras comuns](../architecture.md)

## Escopo e ordem

- ID canônico: `{sid}`.
- Ordem topológica: **{number}**; onda de execução: **{wave}**; prioridade temática inicial: {impl['wave']}.
- Tipo de trabalho: **{MODES[impl['mode']]}**; complexidade relativa: **{impl['complexity']}**.
- Registro atual: implementação `{row['implementation_state']}`, carga `{row['load_state']}`; não é certificação do banco local.
- Dependências mínimas para concluir cadastro e ligações: {deps}
- Contrato de acesso catalogado: [{row['primary_url']}]({row['primary_url']}).

## Artefatos existentes auditados

{artifacts}

## Download e atualização

| Entrada | Finalidade | Evidência / validação pendente |
|---|---|---|
{endpoints}

- **Método:** {download['method']}
- **Autenticação:** {download['authentication']}
- **Formato bruto:** {download['raw_format']}
- **Partições e backfill:** {download['partitioning']}
- **Retomada e deduplicação de download:** {download['resume']}
- **Atualização:** {download['refresh']}

Limites e pré-condições:

{bullets(download['known_limits'])}

## Contrato de ingestão

**Entrada esperada:** {ingestion['input_contract']}

**Chave natural / namespace:** {ingestion['natural_key']}

Normalização:

{bullets(ingestion['normalization'])}

## Cadastro no Neo4j

`existing` identifica comportamento/label já encontrado no projeto; `proposed`
é desenho a implementar. As regras da arquitetura prevalecem sobre merges
fracos existentes. Toda nova chave/label exige constraint, migração e fixture.

| Entidade | Chave | Estado no plano |
|---|---|---|
{nodes}

## Ligações e evidências

| Relação | Campos de ligação | Regra e limite | Estado no plano |
|---|---|---|---|
{relationships}

## Pacote de implementação

Os caminhos abaixo são entregáveis a criar ou alterar; não são alegações de
que um novo conector já existe.

{bullets([f'`{path}`' for path in impl['deliverables']])}

Tarefas específicas, em ordem:

{bullets(impl['tasks'], numbered=True)}

Aplicar também os seis marcos comuns da arquitetura: contrato confirmado,
download validado, transformação, cadastro, ligações e operação incremental.

## Critérios de aceite

{bullets(impl['acceptance'], checks=True)}

## Riscos e decisões pendentes

{bullets(source['risks'])}

## Evidências e referências

{evidence}

Ficha gerada a partir de `config/source_implementation_plan.json`. Estado: planejamento.
"""


def render(root: Path, plan: dict, registry: dict[str, dict]) -> dict[Path, str]:
    order, waves = validate(root, plan, registry)
    profiles = {s["source_id"]: s for s in plan["sources"]}
    counts = Counter(waves.values())
    modes = Counter(s["implementation"]["mode"] for s in profiles.values())
    outputs: dict[Path, str] = {}
    matrix = io.StringIO(newline="")
    writer = csv.writer(matrix, lineterminator="\n")
    writer.writerow([
        "sequence", "source_id", "name", "execution_wave", "initial_wave", "mode",
        "complexity", "dependencies", "registry_implementation_state", "registry_load_state",
        "primary_url", "plan_path",
    ])
    index_rows: list[str] = []
    for number, sid in enumerate(order, 1):
        source, row = profiles[sid], registry[sid]
        impl = source["implementation"]
        path = Path("docs/implementation/sources") / f"{sid}.md"
        outputs[path] = source_doc(source, row, number, waves[sid])
        writer.writerow([
            number, sid, row["name"], waves[sid], impl["wave"], impl["mode"],
            impl["complexity"], ";".join(source["dependencies"]), row["implementation_state"],
            row["load_state"], row["primary_url"], str(path),
        ])
        index_rows.append(
            f"| {number} | [{sid}](sources/{sid}.md) | {cell(row['name'])} | {waves[sid]} | "
            f"{impl['complexity']} | {cell(MODES[impl['mode']])} |"
        )
    outputs[Path("docs/implementation/source_matrix.csv")] = matrix.getvalue()
    if "patterns" in plan:
        pattern_parts = [
            "# Plano dos cruzamentos definidos pelo projeto\n",
            "[Índice](README.md) · [Regras de identidade e evidência](architecture.md)\n",
            "Este inventário cobre todos os IDs de `PATTERN_METADATA`. Uma definição em metadados "
            "não significa consulta implementada. Os oito padrões comunitários têm arquivos de consulta "
            "identificados; os demais exigem implementação ou revisão explícita de viabilidade.\n",
            "Em cada requisito, alternativas entre parênteses significam **qualquer uma**; grupos "
            "separados por `+` precisam estar disponíveis em conjunto. Cobertura e vigência devem ser "
            "compatíveis. Amostras sintéticas de aceite não afirmam casos reais.\n",
        ]
        for pattern in plan["patterns"]:
            groups = " + ".join("(" + " ou ".join(
                f"[{sid}](sources/{sid}.md)" for sid in group) + ")" for group in pattern["source_groups"])
            query = pattern.get("query_path")
            reference = f"[{query}](../../{query})" if query else "Sem query específica confirmada no escopo comunitário."
            pattern_parts.append(f"""## {pattern['pattern_id']}

- **Estado auditado / condição:** {pattern['status']}
- **Fontes necessárias:** {groups}
- **Campos e ligações:** {pattern['joins']}
- **Temporalidade:** {pattern['temporal']}
- **Implementação a fazer:** {pattern['work']}
- **Consulta atual:** {reference}
- **Aceite positivo:** {pattern['positive_case']}
- **Aceite negativo:** {pattern['negative_case']}
""")
        outputs[Path("docs/implementation/crossings.md")] = "\n".join(pattern_parts)
    wave_rows = "\n".join(f"| {wave} | {WAVES[wave]} | {counts[wave]} |" for wave in WAVES)
    mode_rows = "\n".join(f"- {MODES[mode]}: **{modes[mode]}**." for mode in MODES)
    outputs[Path("docs/implementation/README.md")] = f"""# Plano de implementação de todas as fontes

Data do planejamento: **{plan['planned_on']}**. Cobertura: **{len(order)} fichas individuais**,
uma para cada ID em [source_registry_br_v1.csv](../source_registry_br_v1.csv),
incluindo fontes implementadas, novas, derivadas, catálogos e acessos restritos.
Não há fonte omitida por estar bloqueada ou ainda sem endpoint validado.

Cada ficha especifica aquisição, autenticação, particionamento, retomada,
contrato de entrada, normalização, chave de identidade, cadastro no Neo4j,
ligações, dependências, arquivos a entregar e critérios de aceite.
Os estados herdados do registro não comprovam carga no ambiente local.

## Como executar o plano

1. Concluir a **etapa zero F01–F10** da [arquitetura](architecture.md): identidade,
   CNPJ alfanumérico, esquema, aquisição, loader, ligações, orquestração,
   dimensões e ambiente. Ela contém as lacunas comprovadas no código atual.
2. Fazer o piloto CNPJ + sanções + contratos; adicionar emenda/candidatura e
   uma dimensão/série para validar os cruzamentos e medir recursos.
3. Seguir a ordem da [matriz CSV](source_matrix.csv), respeitando dependências.
   A onda é ajustada quando uma base necessária pertence a uma onda posterior.
   Dentro da mesma onda, a ordem topológica determina o que vem antes.
4. Para cada ficha, fechar separadamente contrato, download, transformação,
   cadastro, ligações e operação incremental. Só registrar sucesso com evidência.
5. Expandir backfill após medição do piloto; registrar bloqueios e progresso
   por fonte, sem reset global do banco ou suposição de acesso irrestrito.

## Distribuição do trabalho

{mode_rows}

Complexidade **S/M/L/XL** é relativa (pequena/média/grande/muito grande), não uma
promessa de prazo. Volume e tempo de download serão medidos por partição no
piloto; portais indisponíveis e acessos institucionais têm pré-condições próprias.

| Onda | Foco | Fontes na onda efetiva |
|---|---|---|
{wave_rows}

Não há credenciais, scripts novos de download ou cargas executadas por este
documento. Caminhos novos nas fichas são entregáveis propostos. URLs marcadas
como catálogo, descoberta ou pendentes precisam de prova de acesso antes do
desenvolvimento do extrator. Estatísticas ligam território/período; não produzem
vínculos nominais sem chaves. Fontes restritas mantêm uma ficha com seu caminho
de habilitação/exportação e um resultado de bloqueio explícito.

## Entregáveis do planejamento

- [{len(order)} fichas por fonte](#índice-individual), com links abaixo.
- [Arquitetura, fundação, modelo de cadastro e regras de ligação](architecture.md).
- [Plano individual dos {len(plan.get('patterns', []))} cruzamentos definidos pelo projeto](crossings.md).
- [Matriz de ordem, dependências e complexidade](source_matrix.csv).
- [Manifesto estruturado do plano](../../config/source_implementation_plan.json).
- [Gerador e verificador de cobertura](../../scripts/generate_source_implementation_plan.py).

Para atualizar o plano, editar o manifesto e executar, da raiz do repositório:

```bash
python3 scripts/generate_source_implementation_plan.py
python3 scripts/generate_source_implementation_plan.py --check
```

O verificador exige cobertura exata do registro, IDs únicos, dependências
existentes e sem ciclos, artefatos atuais existentes e fichas derivadas
sincronizadas. Ele não testa disponibilidade externa nem faz ingestão.

## Índice individual

| Ordem | Fonte | Descrição | Onda | Complexidade | Trabalho |
|---|---|---|---|---|---|
{chr(10).join(index_rows)}
"""
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    plan = json.loads((root / "config/source_implementation_plan.json").read_text(encoding="utf-8"))
    with (root / "docs/source_registry_br_v1.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    registry = {row["source_id"]: row for row in rows}
    if len(registry) != len(rows):
        raise ValueError("Duplicate source IDs in registry")
    outputs = render(root, plan, registry)
    expected_sources = {root / path for path in outputs if path.parent.name == "sources"}
    stale = set((root / "docs/implementation/sources").glob("*.md")) - expected_sources
    if stale:
        raise ValueError(f"Unexpected source plans; review manually: {sorted(map(str, stale))}")
    mismatches = [path for path, content in outputs.items()
                  if not (root / path).exists() or (root / path).read_text(encoding="utf-8") != content]
    if args.check:
        if mismatches:
            print("FAIL: generated files out of date: " + ", ".join(map(str, mismatches)))
            return 1
        print(f"PASS: {len(registry)} source plans; complete coverage; dependency graph valid")
        return 0
    for path, content in outputs.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    print(f"UPDATED: {len(registry)} source plans, index and matrix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
