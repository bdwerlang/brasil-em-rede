MATCH (n)
WHERE (n.entity_id = $entity_id OR elementId(n) = $entity_id)
  AND (n:Person OR n:Partner OR n:Company OR n:Contract OR n:Sanction OR n:Election
       OR n:Amendment OR n:Finance OR n:Embargo OR n:Health OR n:Education
       OR n:Convenio OR n:LaborStats OR n:PublicOffice)
RETURN COUNT { (n)--() } AS degree
