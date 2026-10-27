MATCH (e)
WHERE e.entity_id = $entity_id
  AND (e:Person OR e:Partner OR e:Company OR e:Contract OR e:Sanction OR e:Election OR e:Amendment
       OR e:Finance OR e:Embargo OR e:Health OR e:Education OR e:Convenio OR e:LaborStats OR e:PublicOffice)
RETURN e, labels(e) AS entity_labels, e.entity_id AS entity_id
LIMIT 2
