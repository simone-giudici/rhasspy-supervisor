ARG BUILD_ARCH=amd64
FROM ${BUILD_ARCH}/debian:buster-slim
ARG BUILD_ARCH=amd64

COPY pyinstaller/dist/* /usr/lib/rhasspysupervisor/
COPY debian/bin/* /usr/bin/

ENTRYPOINT ["/usr/bin/rhasspy-supervisor"]
