MATCH (node:Company)
WHERE node.cnpj IN [$identifier, $identifier_formatted]
  AND ($entity_type IS NULL OR $entity_type = 'company')
RETURN count(node) AS total
