BEGIN;
-- Freeze the old snapshot while validating and applying the reviewed mapping.
LOCK TABLE control.run_attempt, control.partition_manifest IN ACCESS EXCLUSIVE MODE;
ALTER TABLE control.run_attempt ADD COLUMN partition_id text REFERENCES control.partition;
ALTER TABLE control.run_attempt ADD COLUMN owner uuid;
ALTER TABLE control.run_attempt ADD COLUMN token bigint CHECK (token > 0);
ALTER TABLE control.partition_manifest ADD COLUMN run_attempt_id uuid REFERENCES control.run_attempt;
CREATE TABLE control.attempt_backfill_evidence (attempt_id uuid PRIMARY KEY REFERENCES control.run_attempt, evidence_ref text NOT NULL CHECK (length(btrim(evidence_ref)) > 0));
CREATE TABLE control.manifest_backfill_evidence (manifest_id uuid PRIMARY KEY REFERENCES control.partition_manifest, evidence_ref text NOT NULL CHECK (length(btrim(evidence_ref)) > 0));
DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM control.run_attempt) OR EXISTS (SELECT 1 FROM control.partition_manifest) THEN
  IF to_regclass('pg_temp.u03_attempt_backfill') IS NULL OR to_regclass('pg_temp.u03_manifest_backfill') IS NULL THEN RAISE EXCEPTION 'reviewed backfill mappings required'; END IF;
  IF EXISTS (SELECT 1 FROM pg_temp.u03_attempt_backfill WHERE attempt_id IS NULL OR partition_id IS NULL OR owner IS NULL OR token IS NULL OR token <= 0 OR evidence_ref IS NULL OR length(btrim(evidence_ref)) = 0) OR EXISTS (SELECT 1 FROM pg_temp.u03_manifest_backfill WHERE manifest_id IS NULL OR attempt_id IS NULL OR evidence_ref IS NULL OR length(btrim(evidence_ref)) = 0) OR EXISTS (SELECT attempt_id FROM pg_temp.u03_attempt_backfill GROUP BY attempt_id HAVING count(*) > 1) OR EXISTS (SELECT manifest_id FROM pg_temp.u03_manifest_backfill GROUP BY manifest_id HAVING count(*) > 1) THEN RAISE EXCEPTION 'invalid backfill mapping'; END IF;
  IF EXISTS (SELECT id FROM control.run_attempt EXCEPT SELECT attempt_id FROM pg_temp.u03_attempt_backfill) OR EXISTS (SELECT attempt_id FROM pg_temp.u03_attempt_backfill EXCEPT SELECT id FROM control.run_attempt) OR EXISTS (SELECT id FROM control.partition_manifest EXCEPT SELECT manifest_id FROM pg_temp.u03_manifest_backfill) OR EXISTS (SELECT manifest_id FROM pg_temp.u03_manifest_backfill EXCEPT SELECT id FROM control.partition_manifest) THEN RAISE EXCEPTION 'backfill mappings must cover exactly the legacy records'; END IF;
  IF EXISTS (SELECT 1 FROM control.partition_manifest m JOIN pg_temp.u03_manifest_backfill mb ON mb.manifest_id=m.id LEFT JOIN pg_temp.u03_attempt_backfill ab ON ab.attempt_id=mb.attempt_id WHERE ab.attempt_id IS NULL OR ab.partition_id <> m.partition_id OR ab.token <> m.token) THEN RAISE EXCEPTION 'manifest and attempt mapping disagree'; END IF;
  UPDATE control.run_attempt a SET partition_id=b.partition_id, owner=b.owner, token=b.token FROM pg_temp.u03_attempt_backfill b WHERE a.id=b.attempt_id;
  ALTER TABLE control.partition_manifest DISABLE TRIGGER manifest_immutable;
  UPDATE control.partition_manifest m SET run_attempt_id=b.attempt_id FROM pg_temp.u03_manifest_backfill b WHERE m.id=b.manifest_id;
  ALTER TABLE control.partition_manifest ENABLE TRIGGER manifest_immutable;
  INSERT INTO control.attempt_backfill_evidence SELECT attempt_id, evidence_ref FROM pg_temp.u03_attempt_backfill;
  INSERT INTO control.manifest_backfill_evidence SELECT manifest_id, evidence_ref FROM pg_temp.u03_manifest_backfill;
 END IF;
END $$;
ALTER TABLE control.run_attempt ALTER COLUMN partition_id SET NOT NULL;
ALTER TABLE control.run_attempt ALTER COLUMN owner SET NOT NULL;
ALTER TABLE control.run_attempt ALTER COLUMN token SET NOT NULL;
ALTER TABLE control.partition_manifest ALTER COLUMN run_attempt_id SET NOT NULL;
CREATE TRIGGER attempt_backfill_immutable BEFORE UPDATE OR DELETE ON control.attempt_backfill_evidence FOR EACH ROW EXECUTE FUNCTION control.deny_mutation();
CREATE TRIGGER manifest_backfill_immutable BEFORE UPDATE OR DELETE ON control.manifest_backfill_evidence FOR EACH ROW EXECUTE FUNCTION control.deny_mutation();
CREATE TRIGGER run_immutable BEFORE UPDATE OR DELETE ON control.run FOR EACH ROW EXECUTE FUNCTION control.deny_mutation();
CREATE TRIGGER attempt_immutable BEFORE UPDATE OR DELETE ON control.run_attempt FOR EACH ROW EXECUTE FUNCTION control.deny_mutation();
CREATE FUNCTION control.start_attempt(p_run uuid, p_key text, p_attempt uuid, p_partition text, p_owner uuid, p_token bigint)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, control AS $$
BEGIN
 PERFORM control.assert_lease(p_partition, p_owner, p_token);
 INSERT INTO control.run(id, idempotency_key) VALUES(p_run, p_key) ON CONFLICT(id) DO NOTHING;
 IF NOT EXISTS (SELECT 1 FROM control.run WHERE id = p_run AND idempotency_key = p_key) THEN RAISE EXCEPTION 'run identity mismatch'; END IF;
 INSERT INTO control.run_attempt(id, run_id, partition_id, owner, token) VALUES(p_attempt, p_run, p_partition, p_owner, p_token);
END $$;
DROP FUNCTION control.finalize_manifest(uuid, text, uuid[], uuid, bigint);
CREATE FUNCTION control.finalize_manifest(p_id uuid, p_partition text, p_artifacts uuid[], p_owner uuid, p_token bigint, p_attempt uuid)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, control AS $$
BEGIN
 PERFORM control.assert_lease(p_partition, p_owner, p_token);
 IF NOT EXISTS (SELECT 1 FROM control.run_attempt WHERE id = p_attempt AND partition_id = p_partition AND owner = p_owner AND token = p_token) THEN RAISE EXCEPTION 'attempt does not match lease'; END IF;
 IF p_artifacts IS NULL OR cardinality(p_artifacts) = 0 OR array_position(p_artifacts, NULL) IS NOT NULL OR cardinality(p_artifacts) <> (SELECT count(DISTINCT x) FROM unnest(p_artifacts) x) OR cardinality(p_artifacts) <> (SELECT count(*) FROM control.artifact WHERE id = ANY(p_artifacts) AND partition_id = p_partition) THEN RAISE EXCEPTION 'invalid artifact set'; END IF;
 INSERT INTO control.partition_manifest(id, partition_id, token, run_attempt_id) VALUES (p_id, p_partition, p_token, p_attempt);
 INSERT INTO control.manifest_artifact(manifest_id, partition_id, artifact_id) SELECT p_id, p_partition, x FROM unnest(p_artifacts) x;
END $$;
REVOKE ALL ON FUNCTION control.start_attempt(uuid, text, uuid, text, uuid, bigint), control.finalize_manifest(uuid, text, uuid[], uuid, bigint, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION control.start_attempt(uuid, text, uuid, text, uuid, bigint), control.finalize_manifest(uuid, text, uuid[], uuid, bigint, uuid) TO bracc_control_worker;
GRANT SELECT ON control.run, control.run_attempt TO bracc_control_worker, bracc_control_reader;
INSERT INTO control.schema_migration(version) VALUES (4);
COMMIT;
