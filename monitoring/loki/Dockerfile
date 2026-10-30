# Loki with its config built in, so the server needs no files from the repo.
# CI builds this from the monitoring/loki folder.
FROM busybox:1.37.0-musl AS busybox

FROM grafana/loki:3.7.9

COPY loki.yaml /etc/loki/loki.yaml

# The Loki image has no shell, curl or wget, and Loki has no health check
# command of its own, so the static busybox gives the health check a wget.
COPY --from=busybox /bin/busybox /usr/local/bin/busybox
