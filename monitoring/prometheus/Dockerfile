# Prometheus with its config built in, so the server needs no files from the
# repo. CI builds this from the monitoring/prometheus folder.
FROM prom/prometheus:v3.15.0

COPY prometheus.yml /etc/prometheus/prometheus.yml

# Fails the build if the config is invalid, rather than the container at deploy.
RUN ["promtool", "check", "config", "/etc/prometheus/prometheus.yml"]
