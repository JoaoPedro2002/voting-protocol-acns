from .classes import NMOD_POLY_TYPE
from .compile import shared_library, MODP
from .logger import LOGGER, VERBOSE
from .players import VotingProtocol


def votes_to_poly(votes_per_voter):
    votes_poly = []
    for votes in votes_per_voter:
        vote_poly = []
        for vote in votes:
            v = NMOD_POLY_TYPE()
            shared_library.nmod_poly_init(v, MODP)
            for answer in vote:
                shared_library.nmod_poly_set_coeff_ui(v, answer, 1)
            vote_poly.append(v)
        votes_poly.append(vote_poly)

    return votes_poly


def benchmark_registration_with_rct(n_voters, questions):
    import timeit
    protocol = VotingProtocol()

    LOGGER.info("RUNNING SETUP PHASE")

    setup_t_1 = timeit.default_timer()
    protocol.setup_phase(questions)
    setup_t_2 = timeit.default_timer()

    LOGGER.log(VERBOSE, f"Setup time: {setup_t_2 - setup_t_1}")

    LOGGER.info(f"RUNNING REGISTER PHASE FOR {n_voters} VOTERS")

    registration_t_1 = timeit.default_timer()
    voter_reg_t, rtc_gen_t = protocol.registration_phase(n_voters,
                                                         generate_return_code_tables=True,
                                                         benchmark=True)
    registration_t_2 = timeit.default_timer()

    LOGGER.log(VERBOSE, f"Register time: {registration_t_2 - registration_t_1}")

    # cleanup
    protocol.clear_voters()
    protocol.clear_players()

    return (setup_t_2 - setup_t_1,registration_t_2 - registration_t_1), (voter_reg_t, rtc_gen_t)

def protocol_benchmark(n_voters, questions, votes):
    import timeit
    protocol = VotingProtocol(clear=True)

    LOGGER.info("RUNNING SETUP PHASE")

    setup_t_1 = timeit.default_timer()
    protocol.setup_phase(questions)
    setup_t_2 = timeit.default_timer()

    LOGGER.log(VERBOSE, f"Setup time: {setup_t_2 - setup_t_1}")

    LOGGER.info(f"RUNNING REGISTER PHASE FOR {n_voters} VOTERS")

    registration_t_1 = timeit.default_timer()
    register_t, rct_t = protocol.registration_phase(n_voters, benchmark=True)
    registration_t_2 = timeit.default_timer()

    LOGGER.log(VERBOSE, f"Register time: {registration_t_2 - registration_t_1}")

    votes_as_poly = votes_to_poly(votes)

    LOGGER.info(f"RUNNING CASTING PHASE FOR {n_voters} VOTERS")

    voting_t_1 = timeit.default_timer()
    cast_t, code_t = protocol.casting_phase(votes_as_poly, benchmark=True)
    voting_t_2 = timeit.default_timer()

    LOGGER.info("RUNNING COUNT PHASE FOR {n_voters} VOTERS")

    count_t_1 = timeit.default_timer()
    result, tally, (alg_count_t, ver_t) = protocol.counting_phase(benchmark=True)
    count_t_2 = timeit.default_timer()
    if not result:
        LOGGER.error("Counting failed")

    LOGGER.log(VERBOSE, f"Count time: {count_t_2 - count_t_1}")

    # cleanup
    protocol.clear_players()

    setup_t = setup_t_2 - setup_t_1
    voting_t = voting_t_2 - voting_t_1
    count_t = count_t_2 - count_t_1

    return ((setup_t, registration_t_2 - registration_t_1, voting_t, count_t),
            (setup_t, register_t, cast_t, code_t, alg_count_t, ver_t))
