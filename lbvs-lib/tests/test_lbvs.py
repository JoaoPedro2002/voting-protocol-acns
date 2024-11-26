from lbvs_lib import protocol_bench
from lbvs_lib.utils import new_random_question, get_all_voting_combinations, random


def test_protocol_bench():
    n_voters = 25
    question = new_random_question()
    voting_comb = list(get_all_voting_combinations(question['answers'], question['min'], question['max']))
    votes = []
    for _ in range(n_voters):
        votes.append(random.sample(voting_comb, 1))

    protocol_bench.protocol_benchmark(n_voters, [question], votes)