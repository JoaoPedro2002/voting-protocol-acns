FROM python:3.12-bullseye as compile-flint

RUN \
    apt-get update && \
    apt-get -y dist-upgrade && \
    apt-get install -y -q \
    wget \
    m4 \
    build-essential \
    libgmp-dev libmpfr-dev &&\
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

COPY compile-flint/Makefile /var/flint-build/

WORKDIR /var/flint-build/

RUN make libflint

FROM compile-flint as compile-lbvs-backend

ADD lattice-voting-ctrsa21/src /var/lbvs-backend/src
COPY lattice-voting-ctrsa21/Makefile /var/lbvs-backend/

WORKDIR /var/lbvs-backend/

RUN export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
RUN ldconfig

RUN make shared_lib.so

FROM compile-lbvs-backend as lbvs-frontend

RUN \
    apt-get update && \
    apt-get install -y -q \
    python3-dev &&\
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

ADD lbvs-lib/src /var/lbvs-frontend/src
ADD lbvs-lib/pyproject.toml /var/lbvs-frontend/
ADD lbvs-lib/LICENSE.txt /var/lbvs-frontend/
ADD lbvs-lib/README.md /var/lbvs-frontend/

WORKDIR /var/lbvs-frontend/

RUN cp /var/lbvs-backend/shared_lib.so src/lbvs_lib/

RUN pip install hatch

RUN hatch build

FROM lbvs-frontend as players-api

COPY platers-api/*.py /var/players-api/
COPY platers-api/players/ /var/players-api/players/
COPY players-api/requirements.txt /var/players-api/

WORKDIR /var/players-api/

RUN python3 -m venv venv
RUN source venv/bin/activate

RUN pip install --no-compile --no-cache-dir -r requirements.txt
RUN pip install $(find /var/lbvs-frontend/dist/ -name *.whl)

CMD ["python", "main.py"]