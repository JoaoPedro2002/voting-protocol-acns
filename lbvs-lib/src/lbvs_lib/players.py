import timeit
import uuid
from typing import Tuple, List

from .shuffle import Shuffle
from .cleanup import clear_ev_and_proof, clear_voter, clear_keys
from .classes import NMOD_POLY_TYPE, PublicKey, CommitmentKey, Commitment, PCRT_POLY_TYPE
from .compile import MODP, WIDTH, shared_library
from .return_code_table import ReturnCodeTable
from .utils import new_random_question, get_all_voting_combinations, nmod_poly_to_string, ev_equals, pv_equals
from .primitives import vericrypt
from .scheme_algorithms import register, setup, code, verify, cast, count
from .utils import random

from .logger import LOGGER, VERBOSE


class Player:
    def __init__(self, players):
        self._players = players

    def receive(self, **kwargs):
        for param_name, item in kwargs.items():
            setattr(self, param_name, item)

    def send_to_player(self, player, **kwargs):
        self._players[player].receive(**kwargs)

    def add_to_params(self, **kwargs):
        for param_name, item in kwargs.items():
            if not hasattr(self, param_name) or getattr(self, param_name) is None:
                setattr(self, param_name, [])
            collection = getattr(self, param_name)
            if isinstance(collection, list):
                if isinstance(item, list):
                    collection.extend(item)
                else:
                    collection.append(item)
            elif isinstance(collection, dict):
                collection[item[0]] = item[1]

    def send_params_to_player(self, player, **kwargs):
        self._players[player].add_to_params(**kwargs)

    def send_to_all(self, **kwargs):
        for player in self._players:
            self.send_params_to_player(player, **kwargs)

    def verify_value(self, value, key):
        # find method verify_{key} and call it with value as argument
        method = getattr(self, f"verify_{key}")
        return method(value)

    def send_value_for_verification(self, player, value, key):
        return self._players[player].verify_value(value=value, key=key)


class Voter(Player):
    def __init__(self, players):
        super().__init__(players)
        self.expected_return_code = []
        # self.return_code_tables = []
        self.vck = None
        self.pk = None
        self.id = str(uuid.uuid4())
        self.computer = VoterComputer(players)

    def cast(self, votes: List[NMOD_POLY_TYPE]):
        # The voter’s computer D runs the casting algorithm Cast
        self.computer.cast(self.id, self.pk, self.vck, votes)
        tmp = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(tmp, MODP)
        for i, v in enumerate(votes):
            shared_library.nmod_poly_add(tmp, v, self.vck[0])
            # table_key = ReturnCodeTable.nmod_table_key(tmp)
            # self.expected_return_code.append(self.return_code_tables[i][table_key])
            """
            Compute on the fly the return codes
            """
            self.expected_return_code.append(ReturnCodeTable.nmod_prf(self._players["R"].prf_key, tmp))
            shared_library.nmod_poly_zero(tmp)
        shared_library.nmod_poly_clear(tmp)

    def verify_return_code(self, return_code):
        # D verifies the return code r
        # The voter V compares the return code to the code in its return code table,
        # and accepts the ballot as cast if and only if the codes match
        correct = return_code == self.expected_return_code
        if not correct:
            self.__refuse_ballot()
        return correct

    def __refuse_ballot(self):
        self._players["B"].refuse_ballot(self.id)

    def clear(self):
        clear_voter((None, self.vck, None))
        self.return_code_tables = None
        self.expected_return_code = None
        self.f = None


class VoterComputer(Player):
    def cast(self, id: str,
             pk: Tuple[CommitmentKey, PublicKey, PublicKey],
             vck: Tuple[NMOD_POLY_TYPE, Commitment, PCRT_POLY_TYPE * WIDTH],
             votes: List[NMOD_POLY_TYPE]):
        ballots = [cast(pk, vck, v) for v in votes]
        # sends the encrypted ballot and the ballot proof to the ballot box B
        self.send_params_to_player("B", encrypted_votes=(id, ballots))


class BallotBox(Player):
    def __init__(self, players):
        super().__init__(players)
        self.pk = None
        self.t = vericrypt.new_t()

        self.voters_vvk = {}
        self.encrypted_votes = {}
        self.election_result: List[List[int]] = []

    def refuse_ballot(self, voter_id):
        # B refuses the ballot
        del self.encrypted_votes[voter_id]

    def code(self, voter_id):
        return_code_generator: ReturnCodeServer = self._players["R"]
        if voter_id not in self.encrypted_votes:
            raise ValueError(f"Voter {voter_id} has not cast a ballot")
        ballots = self.encrypted_votes[voter_id]
        # B sends the encrypted ballot and the ballot proof to the return code generator R
        return_code_generator.code(voter_id, ballots)

    def send_to_auditor(self):
        # B sends the encrypted ballots and proofs to the auditor A
        self.send_to_player("A", encrypted_votes_from_ballot_box=list(self.encrypted_votes.values()))

    def send_votes_to_shuffle_server(self):
        votes = [[q[0] for q in v] for v in self.encrypted_votes.values()]
        self.send_params_to_player("S", encrypted_ballots=votes)


class ReturnCodeServer(Player):

    def __init__(self, players):
        super().__init__(players)
        self.__encrypted_votes = {}
        self.ck = None
        self.pk = None
        self.prf_key = None

    def code(self, voter_id, ballots):
        # R runs the code algorithm Code to get the precode r
        vvk = self._players["B"].voters_vvk[voter_id]
        r = []
        for encrypted_ballot, ballot_proof in ballots:
            r_, result = code(self.pk, self.ck, vvk, encrypted_ballot, ballot_proof)
            assert result, "Ballot proof is invalid"
            # It computes the return code r ← PRF_k(r_)
            r.append(ReturnCodeTable.nmod_prf(self.prf_key, r_))
            shared_library.nmod_poly_clear(r_)
        # and sends r to the voter
        result = self.send_value_for_verification(voter_id, r, "return_code")
        if result:
            self.__encrypted_votes[voter_id] = ballots

    def send_to_auditor(self):
        # B sends the encrypted ballots and proofs to the auditor A
        self.send_to_player("A", encrypted_votes_from_return_code_server=list(self.__encrypted_votes.values()))


class Auditor(Player):
    def __init__(self, players):
        super().__init__(players)
        self.encrypted_votes_from_ballot_box = []
        self.encrypted_votes_from_return_code_server = []
        self.proof = None
        self.pk = None
        self.ballots = None

    def verify_consistence(self):
        # The auditor A verifies consistence of ballots and proofs that it received from B and R
        from_R = self.encrypted_votes_from_return_code_server
        from_B = self.encrypted_votes_from_ballot_box

        assert len(from_R) == len(from_B), "Different ballot lengths between Ballot Box and Return Code Server"

        for i in range(len(from_R)):
            for j in range(len(from_R[i])):
                ev_R, pv_R = from_R[i][j]
                ev_B, pv_B = from_B[i][j]
                assert ev_equals(shared_library, ev_R, ev_B, vericrypt.context), "Encrypted votes are not equal"
                assert pv_equals(shared_library, pv_R, pv_B, vericrypt.context), "Proofs are not equal"

    def verify(self):
        encrypted_ballots = [[q[0] for q in v] for v in self.encrypted_votes_from_ballot_box]
        n_questions = len(encrypted_ballots[0])
        encrypted_ballots = [[encrypted_ballots[j][i]
                              for j in range(len(encrypted_ballots))]
                             for i in range(n_questions)]
        for i in range(len(encrypted_ballots)):
            if not verify(self.pk, encrypted_ballots[i], self.ballots[i], self.proof[i]):
                return False
        return True

    def clear(self):
        from_R = self.encrypted_votes_from_return_code_server
        if from_R is None or len(from_R) == 0:
            return
        n_questions = len(from_R[0])
        for i in range(n_questions):
            Shuffle.proof_clear(shared_library, *self.proof[i], len(from_R))
        for i in range(len(from_R)):
            for j in range(len(from_R[i])):
                ev_R, pv_R = from_R[i][j]
                clear_ev_and_proof(ev_R, pv_R)


class ShuffleServer(Player):
    def __init__(self, players):
        super().__init__(players)
        self.dk = None
        self.encrypted_ballots = None

    def count(self):
        n_questions = len(self.encrypted_ballots[0])
        encrypted_ballots = [[self.encrypted_ballots[j][i]
                              for j in range(len(self.encrypted_ballots))]
                             for i in range(n_questions)]

        ballots_l = []
        proofs_l = []
        for i in range(len(encrypted_ballots)):
            ballots, proof = count(self.dk, encrypted_ballots[i])
            ballots_l.append(ballots)
            proofs_l.append(proof)
        # which is sent to the auditor A
        self.send_to_player("A", ballots=ballots_l, proof=proofs_l)

        election_result = []
        for i, ballots in enumerate(ballots_l):
            t0 = NMOD_POLY_TYPE()
            shared_library.nmod_poly_init(t0, MODP)
            shared_library.nmod_poly_zero(t0)
            for ballot in ballots:
                t1 = NMOD_POLY_TYPE()
                shared_library.nmod_poly_init(t1, MODP)
                shared_library.nmod_poly_add(t1, ballot, proofs_l[i][7])
                shared_library.nmod_poly_add(t0, t0, t1)
                shared_library.nmod_poly_clear(t1)

            s = nmod_poly_to_string(shared_library, t0)
            result_as_list = list(map(lambda x: int(x), s.split(" ")[3:]))
            election_result.append(result_as_list)
            shared_library.nmod_poly_clear(t0)
        self.send_to_player("B", election_result=election_result)


class VotingProtocol:
    def __init__(self, clear=False):
        self.clear = clear
        self.questions = None
        self.combinations: list[list] | None = None
        self.__players = {}
        self.ballot_box: BallotBox = BallotBox(self.__players)
        self.shuffle_server: ShuffleServer = ShuffleServer(self.__players)
        self.return_code_server: ReturnCodeServer = ReturnCodeServer(self.__players)
        self.auditor: Auditor = Auditor(self.__players)
        self.__players["B"] = self.ballot_box
        self.__players["S"] = self.shuffle_server
        self.__players["R"] = self.return_code_server
        self.__players["A"] = self.auditor
        self.__voters: List[Voter] = []

    def setup_phase(self, questions: List[dict]):
        self.questions = questions
        self.combinations = [list(get_all_voting_combinations(question['answers'], question['min'], question["max"]))
                             for question in questions]

        # A trusted set of players run the setup algorithm Setup
        pk, dk, ck = setup()
        # The derived public key pk is given to every player
        for player in self.__players:
            self.__players[player].receive(pk=pk)
        # The decryption key dk is given to the shuffler S
        self.__players["S"].receive(dk=dk)
        # The code key ck is given to the return code generator R
        self.__players["R"].receive(ck=ck)

    def registration_phase(self, voter_size, generate_return_code_tables=False, benchmark=False):
        voter_reg_t, rtc_gen_t = 0, 0
        # The return code generator chooses key k for PRF
        self.return_code_server.receive(prf_key=ReturnCodeTable.new_key())

        self.ballot_box.receive(voters_vvk=dict())
        self.ballot_box.receive(encrypted_votes=dict())

        pk = self.ballot_box.pk
        #  set of trusted players run the register algorithm Reg
        for i in range(voter_size):
            # to generate per-voter keys (vvk, vck, f ) for the voter V
            voter_reg_t1 = timeit.default_timer() if benchmark else 0
            vvk, vck, f = register(pk)
            voter_reg_t2 = timeit.default_timer() if benchmark else 0
            voter_reg_t += voter_reg_t2 - voter_reg_t1
            voter = Voter(self.__players)
            # making every verification key public
            self.ballot_box.add_to_params(voters_vvk=(voter.id, vvk))
            # and giving vck to the voter’s computer
            voter.receive(vvk=vvk, vck=vck, f=f, pk=pk)
            self.__voters.append(voter)
            self.__players[voter.id] = voter

            """
            It is way too memory consuming to compute the return code tables for a large number of options, so when 
            testing the whole protocol we skip this step and measure the time separately
            """
            rtc_gen_t1 = timeit.default_timer() if benchmark else 0
            if generate_return_code_tables:
                # and a set of trusted players compute the return code table. The voter gets the return code table
                tables = [ReturnCodeTable.compute_table(self.return_code_server.prf_key,
                                                    vck[0], combinations=combinations)
                      for combinations in self.combinations]
                voter.receive(return_code_tables=tables)
            rtc_gen_t2 = timeit.default_timer() if benchmark else 0
            rtc_gen_t += rtc_gen_t2 - rtc_gen_t1
        return voter_reg_t, rtc_gen_t


    def casting_phase(self, votes_per_voter=None, benchmark=False):
        cast_t, code_t = 0, 0

        if votes_per_voter is None:
            votes_per_voter = []
            for _ in range(len(self.__voters)):
                votes = []
                for comb in self.combinations:
                    v = NMOD_POLY_TYPE()
                    shared_library.nmod_poly_init(v, MODP)
                    # The voter V chooses a random possible vote v
                    for item in random.choice(comb):
                        shared_library.nmod_poly_set_coeff_ui(v, item, 1)
                    votes.append(v)
                votes_per_voter.append(votes)
        self.combinations = None

        for i, voter in enumerate(self.__voters):
            if i % 10 == 0:
                LOGGER.log(VERBOSE, f"Voter {i + 1}")
            LOGGER.debug(f"Voter {i + 1} is casting their vote")
            votes = votes_per_voter[i]
            # the voter V instructs the voter’s computer D which ballot to cast
            cast_t1 = timeit.default_timer() if benchmark else 0
            voter.cast(votes)
            cast_t2 = timeit.default_timer() if benchmark else 0
            cast_t += cast_t2 - cast_t1
            if self.clear:
                for v in votes:
                    shared_library.nmod_poly_clear(v)
            LOGGER.debug(f"R is recovering the return code for voter {i + 1}")
            # The ballot box B sends the encrypted ballot and the ballot proof to the return code generator
            code_t1 = timeit.default_timer() if benchmark else 0
            self.ballot_box.code(voter.id)
            code_t2 = timeit.default_timer() if benchmark else 0
            code_t += code_t2 - code_t1
            voter.clear()
            # In addition, the voter’s computer will sign the encrypted ballot and ballot
            # proof on behalf of the voter. The ballot box and the return code generator will
            # verify this signature. The return code generator will countersign everything and
            # return this signature to the voter’s computer via the ballot box. The voter’s
            # computer will verify the countersignature
            # TODO
        return cast_t, code_t

    def counting_phase(self, benchmark=False):
        count_t, verify_t = 0, 0

        # In the counting phase, the ballot box B and the return code generator R
        # send the encrypted ballots and ballot proofs they have seen to the auditor A
        self.ballot_box.send_to_auditor()
        self.return_code_server.send_to_auditor()
        # If the data is consistent, the auditor approves
        self.auditor.verify_consistence()

        # The ballot box B then sorts the list of encrypted ballots and sends this to the shuffler S
        self.ballot_box.send_votes_to_shuffle_server()

        # The shuffler S uses the count algorithm Count to compute a list of ballots and a shuffle proof
        LOGGER.log(VERBOSE, "S is counting the votes")
        count_t1 = timeit.default_timer() if benchmark else 0
        self.shuffle_server.count()
        count_t2 = timeit.default_timer() if benchmark else 0
        count_t += count_t2 - count_t1

        # The auditor A uses the verification algorithm Verify to verify the shuffle proof against
        # the encrypted ballots received from B and R
        LOGGER.log(VERBOSE, "A is verifying the shuffle proof")
        verify_t1 = timeit.default_timer() if benchmark else 0
        result = self.auditor.verify()
        verify_t2 = timeit.default_timer() if benchmark else 0
        verify_t += verify_t2 - verify_t1

        pretty_tally = ""
        if result:
            for i, question in enumerate(self.questions):
                if len(question['answers']) > len(self.ballot_box.election_result[i]):
                    while len(question['answers']) > len(self.ballot_box.election_result[i]):
                        self.ballot_box.election_result[i].insert(0, 0)
                pretty_tally += f"Question {i + 1}\n"
                for j, answer in enumerate(question['answers']):
                    pretty_tally += f"{answer}: {self.ballot_box.election_result[i][j]}\n"

        if benchmark:
            return result, pretty_tally, (count_t, verify_t)
        return result, pretty_tally

    def clear_voters(self):
        for voter in self.__voters:
            voter.clear()
        self.__voters = []

    def clear_players(self):
        # clears all ballots, proofs and keys
        self.auditor.clear()
        clear_keys(self.return_code_server.ck, self.shuffle_server.dk, self.ballot_box.pk)


def benchmark(n_voters, questions):
    import timeit

    voting_protocol = VotingProtocol()
    timeit_globals = {"voting_protocol": voting_protocol, "questions": questions, "n_voters": n_voters}
    print(f"Questions: {questions}")
    print(f"Time for setup phase:",
          timeit.timeit("voting_protocol.setup_phase(questions)", number=1, globals=timeit_globals))
    print(f"Time for registration phase with {n_voters} voters:",
          timeit.timeit(f"voting_protocol.registration_phase({n_voters})", number=1, globals=timeit_globals))
    print(f"Time for casting phase with {n_voters} voters:",
          timeit.timeit(voting_protocol.casting_phase, number=1, globals=timeit_globals))
    t1 = timeit.default_timer()
    result, tally = voting_protocol.counting_phase()
    t2 = timeit.default_timer()
    print(tally)
    print(f"Time for counting phase with {n_voters} voters:", t2 - t1)
    print("Counting successful: ", result)


if __name__ == "__main__":
    benchmark(25, [new_random_question() for _ in range(random.randint(1, 5))])
