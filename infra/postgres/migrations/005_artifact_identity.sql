BEGIN;
-- Freeze the catalog while validating legacy rows and installing guards.
LOCK TABLE control.source, control.dataset, control.partition, control.artifact IN SHARE ROW EXCLUSIVE MODE;
DO $$
BEGIN
 IF EXISTS (
  SELECT 1 FROM control.artifact a JOIN control.partition p ON p.id=a.partition_id
  JOIN control.dataset d ON d.id=p.dataset_id JOIN control.source s ON s.id=d.source_id
  WHERE a.access_class <> d.access_class OR d.access_class <> s.access_class
   OR a.object_key NOT IN ('raw/' || s.id || '/' || d.id || '/' || p.id || '/' || a.sha256,
                           'parquet/' || d.id || '/' || d.contract_version || '/' || p.id || '/' || a.sha256 || '.parquet')
 ) THEN RAISE EXCEPTION 'existing artifact identity or access class mismatch'; END IF;
END $$;
CREATE FUNCTION control.validate_artifact_identity() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, control AS $$
DECLARE v_source text; v_dataset text; v_contract text; v_dataset_access text; v_source_access text;
BEGIN
 SELECT s.id, d.id, d.contract_version, d.access_class, s.access_class
 INTO v_source, v_dataset, v_contract, v_dataset_access, v_source_access
 FROM control.partition p JOIN control.dataset d ON d.id=p.dataset_id JOIN control.source s ON s.id=d.source_id
 WHERE p.id=NEW.partition_id FOR SHARE OF p, d, s;
 IF NOT FOUND OR NEW.access_class IS DISTINCT FROM v_dataset_access OR v_dataset_access IS DISTINCT FROM v_source_access
 OR NEW.object_key NOT IN ('raw/' || v_source || '/' || v_dataset || '/' || NEW.partition_id || '/' || NEW.sha256,
                           'parquet/' || v_dataset || '/' || v_contract || '/' || NEW.partition_id || '/' || NEW.sha256 || '.parquet') THEN
  RAISE EXCEPTION 'artifact identity or access class mismatch';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER artifact_identity BEFORE INSERT ON control.artifact FOR EACH ROW EXECUTE FUNCTION control.validate_artifact_identity();
-- Parent identity cannot drift after an artifact has been registered.
CREATE FUNCTION control.freeze_artifact_parent() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, control AS $$
BEGIN
 IF (TG_TABLE_NAME = 'partition' AND EXISTS (SELECT 1 FROM control.artifact a WHERE a.partition_id=OLD.id))
 OR (TG_TABLE_NAME = 'dataset' AND EXISTS (SELECT 1 FROM control.partition p JOIN control.artifact a ON a.partition_id=p.id WHERE p.dataset_id=OLD.id))
 OR (TG_TABLE_NAME = 'source' AND EXISTS (SELECT 1 FROM control.dataset d JOIN control.partition p ON p.dataset_id=d.id JOIN control.artifact a ON a.partition_id=p.id WHERE d.source_id=OLD.id)) THEN
  RAISE EXCEPTION 'artifact parent immutable';
 END IF;
 RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER artifact_parent_freeze BEFORE UPDATE OR DELETE ON control.source FOR EACH ROW EXECUTE FUNCTION control.freeze_artifact_parent();
CREATE TRIGGER artifact_parent_freeze BEFORE UPDATE OR DELETE ON control.dataset FOR EACH ROW EXECUTE FUNCTION control.freeze_artifact_parent();
CREATE TRIGGER artifact_parent_freeze BEFORE UPDATE OR DELETE ON control.partition FOR EACH ROW EXECUTE FUNCTION control.freeze_artifact_parent();
REVOKE ALL ON FUNCTION control.validate_artifact_identity(), control.freeze_artifact_parent() FROM PUBLIC;
INSERT INTO control.schema_migration(version) VALUES (5);
COMMIT;
