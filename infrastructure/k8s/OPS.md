# DrumTracKAI on k3s (Single-Node, On-Prem) — Day-2 Ops

This document describes day-2 operations for the DrumTracKAI Kubernetes deployment:

- Backups (Postgres + MinIO)
- Restore procedures
- Retention verification (MinIO lifecycle rules)
- Updates/rollbacks
- GPU node labeling for MVSEP jobs

## Deploy (prod overlay)

1) Create `infrastructure/k8s/overlays/prod/secrets.yml` from the template:

- Copy `infrastructure/k8s/overlays/prod/secrets.template.yml` to `secrets.yml`
- Fill in strong passwords

2) Update GHCR image names in:

- `infrastructure/k8s/overlays/prod/kustomization.yml`

3) Apply:

```bash
kubectl apply -k infrastructure/k8s/overlays/prod
```

## GPU node labeling

MVSEP jobs are scheduled using:

- Node label: `drumtrack.io/gpu=true`
- Toleration key: `drumtrack.io/gpu`

On your GPU node:

```bash
kubectl label node <GPU_NODE_NAME> drumtrack.io/gpu=true
kubectl taint node <GPU_NODE_NAME> drumtrack.io/gpu=true:NoSchedule
```

## Backup strategy (recommended)

Recommended minimum:

- Postgres backup nightly
- MinIO backup nightly
- Keep backups on a separate disk or another machine

### Postgres backup (logical dump)

```bash
kubectl -n drumtrackai exec -it statefulset/postgres -- \
  pg_dump -U drumtrackai -d drumtrackai \
  --format=custom \
  --file=/tmp/drumtrackai.dump

kubectl -n drumtrackai cp \
  postgres-0:/tmp/drumtrackai.dump \
  ./backups/postgres/drumtrackai-$(date +%F).dump
```

### MinIO backup (bucket mirror)

This uses the MinIO client (`mc`) in a one-shot pod.

1) Create an `mc` pod (temporary):

```bash
kubectl -n drumtrackai run mc-tmp --rm -it --restart=Never \
  --image=minio/mc:RELEASE.2025-01-17T02-10-45Z -- /bin/sh
```

2) In the shell, set an alias and mirror the bucket:

```sh
mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mirror local/user-uploads /backup/user-uploads
```

Notes:

- For a real backup, mount `/backup` to a persistent path or copy the results off-node.
- For v1, stems expire, but you may still want backups for debugging/forensics.

## Restore

### Restore Postgres

1) Copy dump into the pod:

```bash
kubectl -n drumtrackai cp \
  ./backups/postgres/drumtrackai.dump \
  postgres-0:/tmp/drumtrackai.dump
```

2) Restore:

```bash
kubectl -n drumtrackai exec -it statefulset/postgres -- \
  pg_restore -U drumtrackai -d drumtrackai --clean --if-exists /tmp/drumtrackai.dump
```

### Restore MinIO objects

Mirror back into MinIO with `mc mirror`:

```sh
mc mirror /backup/user-uploads local/user-uploads
```

## Retention verification (MinIO lifecycle)

Retention is enforced at the bucket level using lifecycle rules:

- `uploads/` expires after 30 days
- `stems/` expires after 30 days
- `logs/` expires after 7 days

To verify lifecycle rules are present:

1) Start a temporary `mc` shell:

```bash
kubectl -n drumtrackai run mc-tmp --rm -it --restart=Never \
  --image=minio/mc:RELEASE.2025-01-17T02-10-45Z -- /bin/sh
```

2) Inspect lifecycle:

```sh
mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc ilm export local/user-uploads
```

## Updates and rollbacks

### Update images (recommended approach)

- Use immutable tags (e.g. git SHA) instead of `latest`.
- Update `newTag` in `infrastructure/k8s/overlays/prod/kustomization.yml`.

Then apply:

```bash
kubectl apply -k infrastructure/k8s/overlays/prod
```

### Roll back deployments

For `api`:

```bash
kubectl -n drumtrackai rollout undo deployment/api
kubectl -n drumtrackai rollout status deployment/api
```

For `job-launcher`:

```bash
kubectl -n drumtrackai rollout undo deployment/job-launcher
kubectl -n drumtrackai rollout status deployment/job-launcher
```

### MVSEP job failures

MVSEP runs as Kubernetes Jobs. Inspect logs:

```bash
kubectl -n drumtrackai get jobs
kubectl -n drumtrackai logs job/<job-name>
```

If a job is stuck pending, check GPU scheduling:

```bash
kubectl -n drumtrackai describe pod <pod>
```

Common causes:

- GPU label/taint mismatch
- NVIDIA device plugin not installed
- Resource requests too high for the node
