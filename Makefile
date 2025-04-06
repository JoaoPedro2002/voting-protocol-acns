#ELECTION_UUID needs to be set to run vote
CD_DESKTOP = cd desktop
ELECTION_URL := http://localhost:8000
VOTER_URL := http://localhost:8005
ELECTION_PASS := password
VOTER_PHONE := http://localhost:8004
ACTIVATE = source venv/bin/activate

.PHONY: desktop vote lib benchmarks

vote: api/venv
	@if [ -z "$(ELECTION_UUID)" ]; then echo "ELECTION_UUID is not set"; exit 1; fi

	cd api && $(ACTIVATE) && python main.py $(VOTER_URL) $(ELECTION_URL) $(ELECTION_UUID) $(VOTER_PHONE) $(ELECTION_PASS) $(ELECTION_USERS)

desktop: desktop/venv
	$(CD_DESKTOP) && $(ACTIVATE)&& pip install ../lbvs-lib
	$(CD_DESKTOP) && $(ACTIVATE) && python main.py

benchmark: lib helios-pqc/venv
	cd helios-pqc && $(ACTIVATE) && pip install ../lbvs-lib
	cd helios-pqc && $(ACTIVATE) && python benchmark.py

lib: lbvs-lib/src/lbvs_lib/shared_lib.so

lbvs-lib/src/lbvs_lib/shared_lib.so: lattice-primitives/shared_lib.so
	cp $< $@

lattice-primitives/shared_lib.so:
	cd lattice-primitives && make shared-lib

%/venv:
	cd $* && python -m venv venv
	cd $* && $(ACTIVATE) && pip install -r requirements.txt