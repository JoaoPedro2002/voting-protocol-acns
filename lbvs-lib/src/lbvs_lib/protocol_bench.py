from .classes import NMOD_POLY_TYPE
from .compile import shared_library, MODP
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


def protocol_benchmark(n_voters, questions, votes):
    import timeit
    protocol = VotingProtocol()

    setup_t_1 = timeit.default_timer()
    protocol.setup_phase(questions)
    setup_t_2 = timeit.default_timer()

    registration_t_1 = timeit.default_timer()
    protocol.registration_phase(n_voters)
    registration_t_2 = timeit.default_timer()

    votes_as_poly = votes_to_poly(votes)
    voting_t_1 = timeit.default_timer()
    protocol.casting_phase(votes_as_poly)
    voting_t_2 = timeit.default_timer()

    count_t_1 = timeit.default_timer()
    result, tally = protocol.counting_phase()
    assert result, "Counting phase failed"
    count_t_2 = timeit.default_timer()

    # cleanup
    protocol.clear_all()

    return (
        setup_t_2 - setup_t_1,
        registration_t_2 - registration_t_1,
        voting_t_2 - voting_t_1,
        count_t_2 - count_t_1
    )
