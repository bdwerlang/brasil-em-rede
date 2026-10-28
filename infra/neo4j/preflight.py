#!/usr/bin/env python3
"""Read-only schema preflight. Requires the Neo4j Python driver (version 5)."""
import logging
import os
import re
import sys
from pathlib import Path

from neo4j import GraphDatabase

# Server notifications may contain query details; keep output restricted.
logging.getLogger("neo4j").setLevel(logging.CRITICAL)

SCHEMA = Path(__file__).with_name('init.cypher')



def definitions(text):
    text = re.sub(r'//[^\n]*', '', text)
    result = []
    for statement in text.split(';'):
        s = ' '.join(statement.split())
        m = re.match(r'CREATE (CONSTRAINT|INDEX|FULLTEXT INDEX) (\w+) IF NOT EXISTS FOR (.+?) (?:REQUIRE|ON EACH|ON) (.+)', s)
        if not m:
            if s:
                raise ValueError('Unsupported schema statement')
            continue
        kind, name, pattern, props = m.groups()
        relationship = pattern.startswith('()-[')
        labels = re.findall(r':(\w+)', pattern)
        if kind == 'FULLTEXT INDEX':
            labels = re.findall(r'\w+', pattern.split(':', 1)[1].rstrip(')'))
        properties = re.findall(r'\w+\.(\w+)', props)
        result.append({'name': name, 'kind': kind, 'entity': 'RELATIONSHIP' if relationship else 'NODE',
                       'labels': labels, 'properties': properties})
    return result



def run(tx, expected):
    constraints = [dict(r) for r in tx.run('SHOW CONSTRAINTS YIELD name, type, entityType, labelsOrTypes, properties RETURN name, type, entityType, labelsOrTypes, properties')]
    indexes = [dict(r) for r in tx.run('SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties, state, owningConstraint, options RETURN name, type, entityType, labelsOrTypes, properties, state, owningConstraint, options')]
    issues = []
    for item in expected:
        candidates = constraints if item['kind'] == 'CONSTRAINT' else indexes
        expected_type = {'CONSTRAINT': 'UNIQUENESS', 'INDEX': 'RANGE', 'FULLTEXT INDEX': 'FULLTEXT'}[item['kind']]
        def matches(row, item=item, expected_type=expected_type):
            return (row['type'] == expected_type and row['entityType'] == item['entity']
                    and sorted(row['labelsOrTypes'] or []) == sorted(item['labels'])
                    and (row['properties'] or []) == item['properties']
                    and (item['kind'] != 'FULLTEXT INDEX' or row.get('options', {}).get('indexConfig') == {
                        'fulltext.analyzer': 'standard-no-stop-words',
                        'fulltext.eventually_consistent': False}))
        named = [r for r in constraints + indexes if r['name'] == item['name']]
        # A constraint and its backing index share a name.
        named = [r for r in named if not r.get('owningConstraint')]
        if named and not any(matches(r) for r in named):
            issues.append(f"{item['name']}: conflito de nome ou definição")
        equivalent = [r for r in candidates if r['name'] != item['name'] and matches(r)]
        if equivalent:
            issues.append(f"{item['name']}: definição equivalente com outro nome")
        if item['kind'] == 'FULLTEXT INDEX':
            valid = [r for r in named if matches(r)]
            state = valid[0]['state'] if valid else 'AUSENTE_OU_DIVERGENTE'
            print(f"{item['name']}: estado {state}")
            if valid and state != 'ONLINE':
                issues.append(f"{item['name']}: índice não está ONLINE")
        if item['kind'] == 'CONSTRAINT' and not any(matches(r) for r in constraints):
            # Labels and properties come exclusively from the checked-in schema.
            label = item['labels'][0]
            props = item['properties']
            where = ' AND '.join(f'n.`{p}` IS NOT NULL' for p in props)
            group = ', '.join(f'n.`{p}` AS k{i}' for i, p in enumerate(props))
            query = f'MATCH (n:`{label}`) WHERE {where} WITH {group}, count(*) AS c WHERE c > 1 RETURN count(*) AS groups'
            groups = tx.run(query).single()['groups']
            if groups:
                issues.append(f"{item['name']}: {groups} grupos de chaves duplicadas")
    return issues


def main():
    try:
        uri = os.environ['NEO4J_URI']
        user = os.environ['NEO4J_USER']
        password = os.environ['NEO4J_PASSWORD']
        database = os.environ.get('NEO4J_DATABASE', 'neo4j')
        with GraphDatabase.driver(uri, auth=(user, password)) as driver, driver.session(database=database) as session:
            issues = session.execute_read(run, definitions(SCHEMA.read_text()))
        for issue in issues:
            print(issue)
        print('PREFLIGHT: BLOQUEADO' if issues else 'PREFLIGHT: SEM CONFLITOS DETECTADOS')
        return bool(issues)
    except Exception:  # noqa: BLE001 — errors may contain connection details or query values.
        print('PREFLIGHT: ERRO; verifique conexão, permissões e versão do Neo4j', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
