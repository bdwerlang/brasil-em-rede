MATCH (node:Company)
WHERE node.cnpj IN [$identifier, $identifier_formatted]
  AND ($entity_type IS NULL OR $entity_type = 'company')
WITH node, labels(node) AS node_labels
RETURN node, 1.0 AS score, node_labels, elementId(node) AS node_id, node.cnpj AS document_id
ORDER BY node_id
SKIP $skip LIMIT $limit
