BEGIN;
CREATE FUNCTION control.acquire_lease(p_partition text, p_owner uuid, p_duration interval)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, control AS $$
DECLARE v_token bigint;
BEGIN
 IF NOT EXISTS (SELECT 1 FROM control.worker_identity WHERE login = session_user AND owner = p_owner) THEN RAISE EXCEPTION 'worker identity mismatch'; END IF;
 IF p_duration <= interval '0 seconds' THEN RAISE EXCEPTION 'invalid lease duration'; END IF;
 INSERT INTO control.partition_lease AS l(partition_id, owner, token, expires_at)
 VALUES (p_partition, p_owner, 1, clock_timestamp() + p_duration)
 ON CONFLICT(partition_id) DO UPDATE SET owner = EXCLUDED.owner, token = l.token + 1, expires_at = clock_timestamp() + p_duration
 WHERE l.expires_at <= clock_timestamp()
 RETURNING token INTO v_token;
 RETURN v_token;
END $$;
CREATE FUNCTION control.assert_lease(p_partition text, p_owner uuid, p_token bigint)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, control AS $$
BEGIN
 IF NOT EXISTS (SELECT 1 FROM control.worker_identity WHERE login = session_user AND owner = p_owner) THEN RAISE EXCEPTION 'worker identity mismatch'; END IF;
 PERFORM 1 FROM control.partition_lease WHERE partition_id = p_partition AND owner = p_owner AND token = p_token AND expires_at > clock_timestamp() FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'stale lease'; END IF;
END $$;
CREATE FUNCTION control.finalize_manifest(p_id uuid, p_partition text, p_artifacts uuid[], p_owner uuid, p_token bigint)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, control AS $$
BEGIN
 PERFORM control.assert_lease(p_partition, p_owner, p_token);
 IF p_artifacts IS NULL OR cardinality(p_artifacts) = 0 OR array_position(p_artifacts, NULL) IS NOT NULL OR cardinality(p_artifacts) <> (SELECT count(DISTINCT x) FROM unnest(p_artifacts) x) OR cardinality(p_artifacts) <> (SELECT count(*) FROM control.artifact WHERE id = ANY(p_artifacts) AND partition_id = p_partition) THEN RAISE EXCEPTION 'invalid artifact set'; END IF;
 INSERT INTO control.partition_manifest(id, partition_id, token) VALUES (p_id, p_partition, p_token);
 INSERT INTO control.manifest_artifact(manifest_id, partition_id, artifact_id) SELECT p_id, p_partition, x FROM unnest(p_artifacts) x;
END $$;
CREATE FUNCTION control.promote_release(p_release uuid, p_previous uuid, p_partition text, p_owner uuid, p_token bigint)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, control AS $$
DECLARE v_current uuid;
BEGIN
 PERFORM control.assert_lease(p_partition, p_owner, p_token);
 PERFORM pg_advisory_xact_lock(73903536);
 SELECT release_id INTO v_current FROM control.active_release WHERE singleton FOR UPDATE;
 IF v_current IS DISTINCT FROM p_previous THEN RAISE EXCEPTION 'release changed'; END IF;
 IF NOT EXISTS (SELECT 1 FROM control.release_bundle WHERE id = p_release AND status = 'verified') THEN RAISE EXCEPTION 'release not verified'; END IF;
 IF NOT EXISTS (SELECT 1 FROM control.release_partition WHERE release_id = p_release) THEN RAISE EXCEPTION 'release has no partitions'; END IF;
 IF EXISTS (SELECT partition_id FROM control.release_partition WHERE release_id = p_release EXCEPT SELECT m.partition_id FROM control.release_manifest rm JOIN control.partition_manifest m ON m.id = rm.manifest_id WHERE rm.release_id = p_release) OR EXISTS (SELECT m.partition_id FROM control.release_manifest rm JOIN control.partition_manifest m ON m.id = rm.manifest_id WHERE rm.release_id = p_release EXCEPT SELECT partition_id FROM control.release_partition WHERE release_id = p_release) OR EXISTS (SELECT m.partition_id FROM control.release_manifest rm JOIN control.partition_manifest m ON m.id = rm.manifest_id WHERE rm.release_id = p_release GROUP BY m.partition_id HAVING count(*) <> 1) THEN RAISE EXCEPTION 'release partition set incomplete'; END IF;
 IF NOT EXISTS (SELECT 1 FROM control.release_manifest rm JOIN control.partition_manifest m ON m.id = rm.manifest_id WHERE rm.release_id = p_release AND m.partition_id = p_partition AND m.token = p_token) THEN RAISE EXCEPTION 'lease does not fence release'; END IF;
 -- Lock every lease in deterministic order before checking its current owner and token.
 PERFORM l.partition_id FROM control.release_manifest rm JOIN control.partition_manifest m ON m.id = rm.manifest_id JOIN control.partition_lease l ON l.partition_id = m.partition_id WHERE rm.release_id = p_release ORDER BY l.partition_id FOR UPDATE OF l;
 IF EXISTS (SELECT 1 FROM control.release_manifest rm JOIN control.partition_manifest m ON m.id = rm.manifest_id LEFT JOIN control.partition_lease l ON l.partition_id = m.partition_id WHERE rm.release_id = p_release AND (l.owner IS DISTINCT FROM p_owner OR l.token IS DISTINCT FROM m.token OR l.expires_at <= clock_timestamp() OR l.partition_id IS NULL)) THEN RAISE EXCEPTION 'release has stale partition'; END IF;
 IF EXISTS (SELECT 1 FROM control.release_manifest rm WHERE rm.release_id = p_release AND (NOT EXISTS (SELECT 1 FROM control.quality_result q WHERE q.manifest_id = rm.manifest_id AND q.passed) OR EXISTS (SELECT 1 FROM control.quality_result q WHERE q.manifest_id = rm.manifest_id AND NOT q.passed) OR NOT EXISTS (SELECT 1 FROM control.projection_job j JOIN control.outbox o ON o.job_id = j.id AND o.acknowledged_at IS NOT NULL WHERE j.manifest_id = rm.manifest_id) OR EXISTS (SELECT 1 FROM control.projection_job j LEFT JOIN control.outbox o ON o.job_id = j.id WHERE j.manifest_id = rm.manifest_id AND (o.id IS NULL OR o.acknowledged_at IS NULL)))) THEN RAISE EXCEPTION 'release incomplete'; END IF;
 INSERT INTO control.active_release(singleton, release_id) VALUES (true, p_release) ON CONFLICT(singleton) DO UPDATE SET release_id = EXCLUDED.release_id;
END $$;
CREATE FUNCTION control.deny_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable record'; END $$;
CREATE TRIGGER artifact_immutable BEFORE UPDATE OR DELETE ON control.artifact FOR EACH ROW EXECUTE FUNCTION control.deny_mutation();
CREATE TRIGGER manifest_immutable BEFORE UPDATE OR DELETE ON control.partition_manifest FOR EACH ROW EXECUTE FUNCTION control.deny_mutation();
CREATE TRIGGER manifest_artifact_immutable BEFORE UPDATE OR DELETE ON control.manifest_artifact FOR EACH ROW EXECUTE FUNCTION control.deny_mutation();
CREATE TRIGGER quality_immutable BEFORE UPDATE OR DELETE ON control.quality_result FOR EACH ROW EXECUTE FUNCTION control.deny_mutation();
CREATE TRIGGER job_immutable BEFORE UPDATE OR DELETE ON control.projection_job FOR EACH ROW EXECUTE FUNCTION control.deny_mutation();
CREATE FUNCTION control.freeze_release() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(73903537);
 IF TG_OP = 'DELETE' OR OLD.status = 'verified' THEN RAISE EXCEPTION 'release immutable'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER release_immutable BEFORE UPDATE OR DELETE ON control.release_bundle FOR EACH ROW EXECUTE FUNCTION control.freeze_release();
CREATE FUNCTION control.freeze_release_members() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_release uuid;
BEGIN
 PERFORM pg_advisory_xact_lock(73903537);
 v_release := CASE WHEN TG_OP = 'DELETE' THEN OLD.release_id ELSE NEW.release_id END;
 PERFORM 1 FROM control.release_bundle WHERE id = v_release AND status = 'draft' FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'release is frozen'; END IF;
 IF TG_OP = 'UPDATE' AND OLD.release_id <> NEW.release_id THEN RAISE EXCEPTION 'cannot move member'; END IF;
 RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;
CREATE TRIGGER freeze_release_partition BEFORE INSERT OR UPDATE OR DELETE ON control.release_partition FOR EACH ROW EXECUTE FUNCTION control.freeze_release_members();
CREATE TRIGGER freeze_release_manifest BEFORE INSERT OR UPDATE OR DELETE ON control.release_manifest FOR EACH ROW EXECUTE FUNCTION control.freeze_release_members();
CREATE FUNCTION control.freeze_manifest_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(73903537);
 IF EXISTS (SELECT 1 FROM control.release_manifest rm JOIN control.release_bundle b ON b.id = rm.release_id WHERE rm.manifest_id = NEW.manifest_id AND b.status = 'verified') THEN RAISE EXCEPTION 'manifest evidence frozen'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER quality_insert_guard BEFORE INSERT ON control.quality_result FOR EACH ROW EXECUTE FUNCTION control.freeze_manifest_evidence();
CREATE TRIGGER job_insert_guard BEFORE INSERT ON control.projection_job FOR EACH ROW EXECUTE FUNCTION control.freeze_manifest_evidence();
CREATE FUNCTION control.freeze_ack() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP = 'DELETE' OR OLD.acknowledged_at IS NOT NULL OR NEW.job_id <> OLD.job_id OR NEW.id <> OLD.id THEN RAISE EXCEPTION 'immutable acknowledgement'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER outbox_ack_immutable BEFORE UPDATE OR DELETE ON control.outbox FOR EACH ROW EXECUTE FUNCTION control.freeze_ack();
REVOKE ALL ON SCHEMA control, app FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA control, app FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA control FROM PUBLIC;
INSERT INTO control.schema_migration(version) VALUES (2);
COMMIT;
