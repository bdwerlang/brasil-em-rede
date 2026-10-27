BEGIN;
-- Cluster-wide roles are created explicitly: a name collision aborts the migration.
CREATE ROLE bracc_control_worker NOLOGIN;
CREATE ROLE bracc_control_projector NOLOGIN;
CREATE ROLE bracc_control_reader NOLOGIN;
GRANT USAGE ON SCHEMA control TO bracc_control_worker, bracc_control_projector, bracc_control_reader;
GRANT EXECUTE ON FUNCTION control.acquire_lease(text, uuid, interval), control.finalize_manifest(uuid, text, uuid[], uuid, bigint), control.promote_release(uuid, uuid, text, uuid, bigint) TO bracc_control_worker;
GRANT SELECT ON control.source, control.dataset, control.partition, control.artifact, control.partition_manifest, control.manifest_artifact, control.quality_result, control.projection_job, control.outbox, control.release_bundle, control.release_partition, control.release_manifest, control.active_release TO bracc_control_worker;
GRANT INSERT ON control.artifact, control.quality_result, control.projection_job, control.release_bundle, control.release_partition, control.release_manifest TO bracc_control_worker;
GRANT INSERT (id, job_id) ON control.outbox TO bracc_control_worker;
GRANT UPDATE (status) ON control.release_bundle TO bracc_control_worker;
GRANT SELECT ON control.projection_job, control.outbox, control.partition_manifest TO bracc_control_projector;
GRANT UPDATE (acknowledged_at) ON control.outbox TO bracc_control_projector;
GRANT SELECT ON control.active_release, control.release_bundle, control.release_manifest, control.partition_manifest, control.manifest_artifact, control.artifact TO bracc_control_reader;
INSERT INTO control.schema_migration(version) VALUES (3);
COMMIT;
