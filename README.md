# demo-app

A tiny Flask app for a Kubernetes introduction. It shows three basics:
health probes, configuration via env vars, credentials from a Secret, and
config files from a mounted ConfigMap.

## Endpoints

| Path       | Purpose                                          | Touches DB |
|------------|--------------------------------------------------|------------|
| `/healthz` | Liveness probe – returns `200 {"status":"ok"}`   | no         |
| `/readyz`  | Readiness probe – `200` if DB reachable, else `503` | yes     |
| `/`        | Returns a greeting and the PostgreSQL version. The greeting is the content of the file `greeting` in the config dir (default: `Hello from Kubernetes!`) | yes |
| `/config`  | Lists every file found in the config dir with its content | no |

## Configuration (environment variables)

| Variable      | Required | Default | Source (on k8s)  | Description                                   |
|---------------|----------|---------|------------------|-----------------------------------------------|
| `LOG_LEVEL`   | no       | `INFO`  | Deployment `env` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `PORT`        | no       | `8080`  | Deployment `env` | HTTP listen port                              |
| `CONFIG_DIR`  | no       | `/etc/demo-app` | Deployment `env` | Directory where the ConfigMap is mounted |
| `DB_HOST`     | yes      |         | Secret           | PostgreSQL host                               |
| `DB_PORT`     | no       | `5432`  | Secret           | PostgreSQL port                               |
| `DB_NAME`     | yes      |         | Secret           | Database name                                 |
| `DB_USER`     | yes      |         | Secret           | Database user                                 |
| `DB_PASSWORD` | yes      |         | Secret           | Database password                             |


## Test it

```bash
curl localhost:8080/healthz            # {"status":"ok"}
curl localhost:8080/                   # greeting + PostgreSQL version
curl localhost:8080/config             # files from the ConfigMap
```


## Notes

- Env vars from a Secret are read at container start; after changing the Secret, restart the pods.
- Liveness deliberately does not check the DB, so a DB outage doesn't cause restart loops.
