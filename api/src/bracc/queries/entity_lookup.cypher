MATCH (e)
WHERE (e:Person AND (e.cpf = $identifier OR e.cpf = $identifier_formatted))
   OR (e:Company AND (e.cnpj = $identifier OR e.cnpj = $identifier_formatted))
RETURN e, labels(e) AS entity_labels, coalesce(e.entity_id, elementId(e)) AS entity_id
LIMIT 2
