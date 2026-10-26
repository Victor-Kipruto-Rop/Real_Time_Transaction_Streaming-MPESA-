# Runtime package migration target

This package is the target location for the streaming subsystem's Python runtime modules.

The existing `app/`, `ingestion/`, `streaming/` and root `kafka.py` paths remain in use until their entry points, imports, Docker images, Airflow DAGs, CI workflows and deployment manifests are migrated and tested together.

Do not duplicate production logic here. During the migration, move a cohesive module and its tests, update all references, and keep a compatibility shim only when a known caller still requires it. This README intentionally does not claim that the runtime has already been moved.
