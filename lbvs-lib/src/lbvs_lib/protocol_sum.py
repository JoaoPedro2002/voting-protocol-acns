import ctypes

from .utils import print_nmod_poly

from .compile import WIDTH, MODP, DEGREE
from .classes import Commitment, COMMITMENT_SCHEME_TYPE, NMOD_POLY_TYPE, CommitmentKey


class ProtocolSum:
    """
        This represents a Sigma-protocol to prove the relation x3 = alpha x1 + beta x2, given
        the commitments [[x1]], [[x2]], [[x3]] and the scalars alpha, beta.

        y1:  sample according to a Gaussian distribution in CRT rep
        y2: sample according to a Gaussian distribution in CRT rep
        y3: sample according to a Gaussian distribution in CRT rep
        t1:  sum of the multiplication of y1 with the commitment key (B1)
        t2: sum of the multiplication of y2 with the commitment key (B2)
        t3: sum of the multiplication of y3 with the commitment key (B3)
        u:  sum(y * commitment_key (b2) * alpha) - sum(_y * commitment_key (b2))

        alpha: the scalar alpha
        beta: the scalar beta

        x1:  the commitment to x1
        x2: the commitment to x2
        x3: the commitment to x3
        key: the commitment key
        scheme: the commitment scheme
    """
    @staticmethod
    def prover(shared_library, scheme: COMMITMENT_SCHEME_TYPE, x1: Commitment, x2: Commitment, x3: Commitment,
               key: CommitmentKey, alpha: NMOD_POLY_TYPE, beta: NMOD_POLY_TYPE,
               r1: NMOD_POLY_TYPE * 2 * WIDTH, r2: NMOD_POLY_TYPE * 2 * WIDTH, r3: NMOD_POLY_TYPE * 2 * WIDTH):
        y1 = (NMOD_POLY_TYPE * 2 * WIDTH)()
        y2 = (NMOD_POLY_TYPE * 2 * WIDTH)()
        y3 = (NMOD_POLY_TYPE * 2 * WIDTH)()
        t1 = (NMOD_POLY_TYPE * 2)()
        t2 = (NMOD_POLY_TYPE * 2)()
        t3 = (NMOD_POLY_TYPE * 2)()
        u = (NMOD_POLY_TYPE * 2)()

        for i in range(2):
            shared_library.nmod_poly_init(t1[i], MODP)
            shared_library.nmod_poly_init(t2[i], MODP)
            shared_library.nmod_poly_init(t3[i], MODP)
            shared_library.nmod_poly_init(u[i], MODP)

        for i in range(WIDTH):
            for j in range(2):
                shared_library.nmod_poly_init(y1[i][j], MODP)
                shared_library.nmod_poly_init(y2[i][j], MODP)
                shared_library.nmod_poly_init(y3[i][j], MODP)

        shared_library.sum_prover(y1, y2, y3, t1, t2, t3, u,
                                  scheme, x1, x2, x3, ctypes.byref(key),
                                  alpha, beta, r1, r2, r3)

        return y1, y2, y3, t1, t2, t3, u

    @staticmethod
    def verifier(shared_library, y1: NMOD_POLY_TYPE * 2 * WIDTH, y2: NMOD_POLY_TYPE * 2 * WIDTH,
                 y3: NMOD_POLY_TYPE * 2 * WIDTH, t1: NMOD_POLY_TYPE * 2, t2: NMOD_POLY_TYPE * 2,
                 t3: NMOD_POLY_TYPE * 2, u: NMOD_POLY_TYPE * 2, scheme: COMMITMENT_SCHEME_TYPE,
                 x1: Commitment, x2: Commitment, x3: Commitment, key: CommitmentKey,
                 alpha: NMOD_POLY_TYPE, beta: NMOD_POLY_TYPE):
        return shared_library.sum_verifier(y1, y2, y3, t1, t2, t3, u, scheme, x1, x2, x3, key, alpha, beta)

    @staticmethod
    def print_proof(shared_library, proof):
        y1, y2, y3, t1, t2, t3, u = proof

        print("t1:")
        for i in range(2):
            print_nmod_poly(shared_library, t1[i])

        print("t2:")
        for i in range(2):
            print_nmod_poly(shared_library, t2[i])

        print("t3:")
        for i in range(2):
            print_nmod_poly(shared_library, t3[i])

        print("u:")
        for i in range(2):
            print_nmod_poly(shared_library, u[i])

        print("y1:")
        for i in range(WIDTH):
            for j in range(2):
                print_nmod_poly(shared_library, y1[i][j])

        print("y2:")
        for i in range(WIDTH):
            for j in range(2):
                print_nmod_poly(shared_library, y2[i][j])

        print("y3:")
        for i in range(WIDTH):
            for j in range(2):
                print_nmod_poly(shared_library, y3[i][j])

    @staticmethod
    def proof_clear(shared_library, proof):
        y1, y2, y3, t1, t2, t3, u = proof

        for i in range(2):
            shared_library.nmod_poly_clear(t1[i])
            shared_library.nmod_poly_clear(t2[i])
            shared_library.nmod_poly_clear(t3[i])
            shared_library.nmod_poly_clear(u[i])

        for i in range(WIDTH):
            for j in range(2):
                shared_library.nmod_poly_clear(y1[i][j])
                shared_library.nmod_poly_clear(y2[i][j])
                shared_library.nmod_poly_clear(y3[i][j])


if __name__ == "__main__":
    from .compile import shared_library
    from .commitment_scheme import CommitmentScheme

    wrapper = CommitmentScheme(shared_library)
    with wrapper as commitment_scheme:
        ck = commitment_scheme.keygen()

        m1 = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(m1, MODP)
        shared_library.nmod_poly_randtest(m1, commitment_scheme.rand, DEGREE)

        m2 = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(m2, MODP)
        shared_library.nmod_poly_randtest(m2, commitment_scheme.rand, DEGREE)

        m3 = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(m3, MODP)
        shared_library.nmod_poly_add(m3, m1, m2)

        x1, r1 = commitment_scheme.commit(ck, m1, only_r=True)
        x2, r2 = commitment_scheme.commit(ck, m2, only_r=True)
        x3, r3 = commitment_scheme.commit(ck, m3, only_r=True)

        alpha = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(alpha, MODP)
        shared_library.utils_nmod_poly_one(alpha)

        beta = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(beta, MODP)
        shared_library.utils_nmod_poly_one(beta)

        y1, y2, y3, t1, t2, t3, u = ProtocolSum.prover(shared_library, commitment_scheme.scheme, x1, x2, x3, ck,
                                                       alpha, beta, r1, r2, r3)

        result = ProtocolSum.verifier(shared_library, y1, y2, y3, t1, t2, t3, u, commitment_scheme.scheme, x1, x2, x3, ck, alpha, beta) == 1
        print("ProtocolSum test passed" if result else "ProtocolSum test failed")

        # Cleaning up
        shared_library.nmod_poly_clear(m1)
        shared_library.nmod_poly_clear(m2)
        shared_library.nmod_poly_clear(m3)
        shared_library.nmod_poly_clear(alpha)
        shared_library.nmod_poly_clear(beta)
        shared_library.commit_keyfree(ck)
        shared_library.commit_free(x1)
        shared_library.commit_free(x2)
        shared_library.commit_free(x3)

        for i in range(2):
            shared_library.nmod_poly_clear(t1[i])
            shared_library.nmod_poly_clear(t2[i])
            shared_library.nmod_poly_clear(t3[i])
            shared_library.nmod_poly_clear(u[i])

        for i in range(WIDTH):
            for j in range(2):
                shared_library.nmod_poly_clear(r1[i][j])
                shared_library.nmod_poly_clear(r2[i][j])
                shared_library.nmod_poly_clear(r3[i][j])

                shared_library.nmod_poly_clear(y1[i][j])
                shared_library.nmod_poly_clear(y2[i][j])
                shared_library.nmod_poly_clear(y3[i][j])
