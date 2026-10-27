MATCH (e) WHERE (e.entity_id = $element_id OR elementId(e) = $element_id)
  AND (e:Person OR e:Partner OR e:Company OR e:Contract OR e:Sanction OR e:Election OR e:Amendment
       OR e:Finance OR e:Embargo OR e:Health OR e:Education OR e:Convenio OR e:LaborStats
       OR e:PublicOffice)
RETURN e, labels(e) AS entity_labels, coalesce(e.entity_id, elementId(e)) AS entity_id
LIMIT 2
