FROM python:3.12-bullseye AS compile-flint

RUN apt-get update \
    && apt-get install -y -q \
        libmpfr-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /var/flint-build/

COPY flint/ ./

RUN ./bootstrap.sh \
    && ./configure \
    && make -j \
    && make install

FROM compile-flint AS compile-lbvs-backend

ADD lattice-primitives/*.c /var/lbvs-backend/
ADD lattice-primitives/*.cpp /var/lbvs-backend/
ADD lattice-primitives/vcl/ /var/lbvs-backend/vcl/
ADD lattice-primitives/*.h /var/lbvs-backend/
COPY lattice-primitives/Makefile /var/lbvs-backend/

WORKDIR /var/lbvs-backend/

RUN export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib \
    && ldconfig \
    && make shared-lib

FROM compile-lbvs-backend AS lbvs-frontend

ADD lbvs-lib/src /var/lbvs-frontend/src
ADD lbvs-lib/pyproject.toml /var/lbvs-frontend/
ADD lbvs-lib/LICENSE.txt /var/lbvs-frontend/
ADD lbvs-lib/README.md /var/lbvs-frontend/

WORKDIR /var/lbvs-frontend/

RUN cp /var/lbvs-backend/shared_lib.so src/lbvs_lib/

FROM lbvs-frontend AS players-api

COPY players-api/*.py /var/players-api/
COPY players-api/players/ /var/players-api/players/
COPY players-api/db/ /var/players-api/db/
COPY players-api/requirements.txt /var/players-api/

WORKDIR /var/players-api/

RUN pip install --no-compile --no-cache-dir -r requirements.txt \
    && pip install /var/lbvs-frontend

CMD ["python", "main.py"]

FROM lbvs-frontend AS helios

RUN apt-get update \
    && apt-get install -y -q \
        libsasl2-dev libldap2-dev netcat \
    && rm -rf /var/lib/apt/lists/*

COPY helios-pqc/*.py /var/helios-server/
COPY helios-pqc/requirements.txt /var/helios-server/
COPY helios-pqc/helios/ /var/helios-server/helios/
COPY helios-pqc/helios_auth/ /var/helios-server/helios_auth/
COPY helios-pqc/heliosbooth/ /var/helios-server/heliosbooth/
COPY helios-pqc/heliosverifier/ /var/helios-server/heliosverifier/
COPY helios-pqc/plainscript/ /var/helios-server/plainscript/
COPY helios-pqc/server_ui/ /var/helios-server/server_ui/
COPY helios-pqc/templates/ /var/helios-server/templates/

WORKDIR /var/helios-server/

RUN pip install --no-compile --no-cache-dir -r requirements.txt \
    && pip install /var/lbvs-frontend

COPY helios-pqc/docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
