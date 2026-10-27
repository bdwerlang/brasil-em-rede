MATCH (center)
WHERE (center.entity_id = $entity_id OR elementId(center) = $entity_id)
  AND (center:Person OR center:Partner OR center:Company OR center:Contract OR center:Sanction OR center:Election
       OR center:Amendment OR center:Finance OR center:Embargo OR center:Health OR center:Education
       OR center:Convenio OR center:LaborStats OR center:PublicOffice)
OPTIONAL MATCH p=(center)-[:SOCIO_DE|DOOU|CANDIDATO_EM|VENCEU|AUTOR_EMENDA|SANCIONADA|OPERA_UNIDADE|DEVE|RECEBEU_EMPRESTIMO|EMBARGADA|MANTEDORA_DE|BENEFICIOU|GEROU_CONVENIO|SAME_AS|POSSIBLE_SAME_AS*1..4]-(connected)
WHERE length(p) <= $depth
  AND all(x IN nodes(p) WHERE NOT (x:User OR x:Investigation OR x:Annotation OR x:Tag))
WITH center, p
UNWIND CASE WHEN p IS NULL THEN [] ELSE relationships(p) END AS r
WITH DISTINCT center, r, startNode(r) AS src, endNode(r) AS tgt
WHERE coalesce($include_probable, false) OR type(r) <> "POSSIBLE_SAME_AS"
RETURN center AS e,
       r,
       labels(center) AS source_labels,
       src AS source_node, labels(src) AS source_node_labels,
       tgt AS target_node, labels(tgt) AS target_node_labels,
       coalesce(center.entity_id, elementId(center)) AS center_id,
       type(r) AS rel_type,
       coalesce(startNode(r).entity_id, elementId(startNode(r))) AS source_id,
       coalesce(endNode(r).entity_id, elementId(endNode(r))) AS target_id,
       elementId(r) AS rel_id
