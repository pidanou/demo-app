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

The `DB_*` values are injected from the Secret `demo-app-db` with `envFrom.secretRef`,
so each key in the Secret becomes an env var of the same name.

## Run locally

```bash
pip install -r requirements.txt
export DB_HOST=localhost DB_NAME=demo DB_USER=demo DB_PASSWORD=secret LOG_LEVEL=DEBUG
python app.py
curl localhost:8080/healthz
```

## Your task: deploy it on Kubernetes

The manifests are intentionally **not** provided: writing them is the exercise.
Below is everything you need to know about the app.

### Prerequisites

A cluster, `kubectl`, a container registry (or kind/minikube image loading), and a
reachable PostgreSQL with a database and user.

### Build the image

```bash
docker build -t <registry>/demo-app:1.0.0 .
docker push <registry>/demo-app:1.0.0
```

On kind/minikube: `kind load docker-image <image>` / `minikube image load <image>`.

### What the app needs from Kubernetes

| Item                | Value                                                                 |
|---------------------|-----------------------------------------------------------------------|
| Container port      | `8080` (change with `PORT`)                                           |
| Liveness probe      | HTTP GET `/healthz`                                                   |
| Readiness probe     | HTTP GET `/readyz`                                                    |
| Log level           | env var `LOG_LEVEL`, plain value (not secret)                         |
| DB settings         | a **Secret** exposed as env vars: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` |
| App config files    | a **ConfigMap** mounted as a volume (files, not env vars) at `/etc/demo-app`; the app reads a file named `greeting` there |
| Image               | the one you built above                                               |

### Objects to create

1. A **Secret** holding the five `DB_*` keys
2. A **ConfigMap** with a key `greeting` (e.g. `Hello from my cluster!`)
3. A **Deployment** running the image, consuming the Secret as env vars, mounting the ConfigMap as a volume, and setting `LOG_LEVEL`
4. A **Service** to reach the pods

### Check your work

```bash
kubectl get pods                       # Running and READY 1/1
kubectl logs <pod>                     # shows the startup line
kubectl port-forward svc/<service> 8080:<service-port>
curl localhost:8080/healthz            # {"status":"ok"}
curl localhost:8080/                   # greeting + PostgreSQL version
curl localhost:8080/config             # files from the ConfigMap
```

### Things to try

- Set `LOG_LEVEL=DEBUG`, roll out, and compare the logs.
- Put a wrong `DB_PASSWORD` in the Secret and restart: pods stay `Running` (liveness OK)
  but are not `Ready` (readiness fails), so the Service sends them no traffic.
- Scale the Deployment to several replicas.
- Edit the ConfigMap's `greeting` and call `/config` again without restarting: the mounted
  file updates in place after up to a minute or so. Add a second key and watch it appear
  as a new file.
- Compare with env vars, which never change until the pod restarts.

### Notes

- Env vars from a Secret are read at container start; after changing the Secret, restart the pods.
- Liveness deliberately does not check the DB, so a DB outage doesn't cause restart loops.
