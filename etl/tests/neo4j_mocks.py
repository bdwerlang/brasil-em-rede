"""Neo4j transaction test double for pipeline query construction tests.

These tests assume all relationship endpoints resolve uniquely; integration tests
exercise actual matching, ambiguity, commits and counters against Neo4j.
"""
from unittest.mock import MagicMock


def make_driver():
    driver = MagicMock()
    session = driver.session.return_value.__enter__.return_value
    tx = session.begin_transaction.return_value.__enter__.return_value

    def run(query, parameters):
        result = MagicMock()
        result.single.return_value = {"resolved": len(parameters["rows"]), "ambiguous": 0}
        counters = result.consume.return_value.counters
        for name in ("nodes_created", "relationships_created", "nodes_deleted",
                     "relationships_deleted", "properties_set", "labels_added", "labels_removed"):
            setattr(counters, name, 0)
        return result

    tx.run.side_effect = run
    return driver


def transaction(driver):
    session = driver.session.return_value.__enter__.return_value
    return session.begin_transaction.return_value.__enter__.return_value
