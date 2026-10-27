BEGIN;
-- Existing attempts require an explicit, reviewed backfill before this migration.
ALTER TABLE control.run_attempt ADD COLUMN partition_id text NOT NULL REFERENCES control.partition;
ALTER TABLE control.run_attempt ADD COLUMN owner uuid NOT NULL;
ALTER TABLE control.run_attempt ADD COLUMN token bigint NOT NULL CHECK (token > 0);
ALTER TABLE control.partition_manifest ADD COLUMN run_attempt_id uuid NOT NULL REFERENCES control.run_attempt;
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
