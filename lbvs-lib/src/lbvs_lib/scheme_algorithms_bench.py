from .classes import NMOD_POLY_TYPE
from .compile import shared_library, MODP, DEGREE
from .cleanup import clear_ev_and_proof, clear_voter, clear_keys
from .shuffle import Shuffle
from .scheme_algorithms import (flint_rand, setup, register,
                               cast, code, count, verify)


def benchmark(n_voters, verbose=False):
    import timeit
    if verbose:
        print(f"RUNNING SETUP ALGORITHM")
    setup_time_1 = timeit.default_timer()
    public_key, decryption_key, code_key = setup()
    setup_time_2 = timeit.default_timer()

    if verbose:
        print(f"RUNNING REGISTER ALGORITHM FOR {n_voters} VOTERS")
    register_time_1 = timeit.default_timer()
    voters = []
    for _ in range(n_voters):
        voter_verification_key, voter_casting_key, func = register(public_key)
        voters.append((voter_verification_key, voter_casting_key, func))
    register_time_2 = timeit.default_timer()

    enc_ballots = []
    proofs = []
    total_cast_time = 0
    total_code_time = 0
    if verbose:
        print(f"RUNNING CAST AND CODE ALGORITHMS FOR {n_voters} VOTERS")
    for voter_verification_key, voter_casting_key, func in voters:
        vote = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(vote, MODP)
        shared_library.nmod_poly_randtest(vote, flint_rand, DEGREE)

        cast_time_1 = timeit.default_timer()
        ecn_vote, vote_proof = cast(public_key, voter_casting_key, vote)
        cast_time_2 = timeit.default_timer()
        total_cast_time += cast_time_2 - cast_time_1

        enc_ballots.append(ecn_vote)
        proofs.append(vote_proof)

        code_time_1 = timeit.default_timer()
        pre_code = code(public_key, code_key, voter_verification_key, ecn_vote, vote_proof)
        code_time_2 = timeit.default_timer()
        total_code_time += code_time_2 - code_time_1

        assert shared_library.nmod_poly_equal(func(vote), pre_code), "Code failed"
        shared_library.nmod_poly_clear(vote)
        shared_library.nmod_poly_clear(pre_code)

    if verbose:
        print(f"RUNNING COUNT ALGORITHM FOR {n_voters} VOTERS")
    count_time_1 = timeit.default_timer()
    dec_ballots, shuffle_proof = count(decryption_key, enc_ballots)
    count_time_2 = timeit.default_timer()

    verify_time_1 = timeit.default_timer()
    if verbose:
        print(f"RUNNING VERIFY ALGORITHM FOR {n_voters} VOTERS")
    final_result = verify(public_key, enc_ballots, dec_ballots, shuffle_proof)
    verify_time_2 = timeit.default_timer()

    assert final_result, "Verification Failed"

    Shuffle.proof_clear(shared_library, *shuffle_proof, n_voters)

    for ballot in dec_ballots:
        shared_library.nmod_poly_clear(ballot)

    for i in range(len(enc_ballots)):
        clear_ev_and_proof(enc_ballots[i], proofs[i])

    for voter in voters:
        clear_voter(voter)

    clear_keys(code_key, decryption_key, public_key)

    return (setup_time_2 - setup_time_1,
            register_time_2 - register_time_1,
            total_cast_time,
            total_code_time,
            count_time_2 - count_time_1,
            verify_time_2 - verify_time_1)


if __name__ == "__main__":
    import timeit
    n_voters = 25
    n_executions = 1

    results = [0] * 6
    alg_name = ["SETUP", "REGISTER", "CAST", "CODE", "COUNT", "VERIFY"]
    for j in range(n_executions):
        print(f"EXECUTION {j}")
        times = benchmark(n_voters, verbose=False)
        for i in range(len(results)):
            results[i] += times[i]

    for i in range(len(results)):
        results[i] /= n_executions
        print(f"Time for {alg_name[i]}: {results[i]}")



