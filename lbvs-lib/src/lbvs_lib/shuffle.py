from .compile import ctypes, MODP, WIDTH, DEGREE
from .classes import (FLINT_RAND_T, NMOD_POLY_TYPE, CommitmentKey, COMMITMENT_SCHEME_TYPE, Commitment,
                     OPENING_TYPE, PCRT_POLY_TYPE)
from .commitment_scheme import CommitmentScheme


class Shuffle:
    @staticmethod
    def shuffle(shared_library, messages: ctypes.POINTER(NMOD_POLY_TYPE), length: int):
        """
        Shuffle the messages
        :param shared_library: the shared library
        :param messages: the messages to shuffle
        :param length: the length of the messages
        """
        from .utils import random
        permutation = [*range(length)]
        random.shuffle(permutation)

        _messages = (NMOD_POLY_TYPE * length)()
        for i in range(length):
            shared_library.nmod_poly_init(_messages[i], MODP)
            shared_library.nmod_poly_set(_messages[i], messages[permutation[i]])

        return _messages

    @staticmethod
    def prover(shared_library, scheme: COMMITMENT_SCHEME_TYPE, com: ctypes.POINTER(ctypes.POINTER(Commitment)),
               m: ctypes.POINTER(NMOD_POLY_TYPE), _m: ctypes.POINTER(NMOD_POLY_TYPE),
               r: ctypes.POINTER(OPENING_TYPE), key: CommitmentKey, rand: FLINT_RAND_T, length: int):
        d = (Commitment * length)()
        y = (OPENING_TYPE * length)()
        _y = (OPENING_TYPE * length)()
        t = (PCRT_POLY_TYPE * length)()
        _t = (PCRT_POLY_TYPE * length)()
        u = (PCRT_POLY_TYPE * length)()
        s = (NMOD_POLY_TYPE * length)()
        rho = NMOD_POLY_TYPE()
        t0 = NMOD_POLY_TYPE()
        t1 = NMOD_POLY_TYPE()

        shared_library.nmod_poly_init(t0, MODP)
        shared_library.nmod_poly_init(t1, MODP)
        shared_library.nmod_poly_init(rho, MODP)
        for i in range(length):
            shared_library.nmod_poly_init(s[i], MODP)
            for k in range(2):
                shared_library.nmod_poly_init(t[i][k], MODP)
                shared_library.nmod_poly_init(_t[i][k], MODP)
                shared_library.nmod_poly_init(u[i][k], MODP)
                for j in range(WIDTH):
                    shared_library.nmod_poly_init(y[i][j][k], MODP)
                    shared_library.nmod_poly_init(_y[i][j][k], MODP)

        # Verifier samples rho that is different from the messages, and beta.
        flag = True
        while flag:
            flag = False
            shared_library.commit_sample_rand(rho, rand, DEGREE)
            for i in range(length):
                if shared_library.nmod_poly_equal(rho, _m[i]) == 1:
                    flag = True
                    break

        # Verifier shifts the commitments by rho
        shared_library.nmod_poly_rem(t0, rho, scheme[0].irred[0])
        shared_library.nmod_poly_rem(t1, rho, scheme[0].irred[1])
        for i in range(length):
            shared_library.nmod_poly_sub(com[i][0].c2[0], com[i][0].c2[0], t0)
            shared_library.nmod_poly_sub(com[i][0].c2[1], com[i][0].c2[1], t0)

        shared_library.nmod_poly_clear(t0)
        shared_library.nmod_poly_clear(t1)

        shared_library.shuffle_prover(y, _y, t, _t, u, scheme, d, s, com, m, _m,
                                      r, rho, ctypes.byref(key), rand, length)

        return y, _y, t, _t, u, d, s, rho

    @staticmethod
    def verifier(shared_library,
                 y: ctypes.POINTER(OPENING_TYPE), _y: ctypes.POINTER(OPENING_TYPE),
                 t: ctypes.POINTER(PCRT_POLY_TYPE), _t: ctypes.POINTER(PCRT_POLY_TYPE),
                 u: ctypes.POINTER(PCRT_POLY_TYPE), scheme: COMMITMENT_SCHEME_TYPE,
                 d: ctypes.POINTER(Commitment), s: ctypes.POINTER(NMOD_POLY_TYPE),
                 com: ctypes.POINTER(ctypes.POINTER(Commitment)), _m: ctypes.POINTER(NMOD_POLY_TYPE),
                 rho: NMOD_POLY_TYPE, key: CommitmentKey, length: int):
        return shared_library.shuffle_verifier(y, _y, t, _t, u, scheme, d, s, com, _m, rho, ctypes.byref(key), length)

    @staticmethod
    def proof_clear(shared_library, y, _y, t, _t, u, d, s, rho, length):
        shared_library.nmod_poly_clear(rho)
        for i in range(length):
            shared_library.commit_free(ctypes.byref(d[i]))
            shared_library.nmod_poly_clear(s[i])
            for k in range(2):
                shared_library.nmod_poly_clear(t[i][k])
                shared_library.nmod_poly_clear(_t[i][k])
                shared_library.nmod_poly_clear(u[i][k])
                for j in range(WIDTH):
                    shared_library.nmod_poly_clear(y[i][j][k])
                    shared_library.nmod_poly_clear(_y[i][j][k])



if __name__ == "__main__":
    n_messages = 25

    from .compile import shared_library

    wrapper = CommitmentScheme(shared_library)
    with wrapper as commitment_scheme:
        m = (NMOD_POLY_TYPE * n_messages)()
        com = (ctypes.POINTER(Commitment) * n_messages)()
        r = (OPENING_TYPE * n_messages)()

        for i in range(n_messages):
            shared_library.nmod_poly_init(m[i], MODP)
            com[i] = shared_library.commit_ptr_init()

        ck = commitment_scheme.keygen()

        for i in range(n_messages):
            shared_library.commit_sample_short(m[i])
            _, r[i] = commitment_scheme.commit(ck, m[i], only_r=True, commit_ref=com[i])

        _m = Shuffle.shuffle(shared_library, m, n_messages)
        proof = Shuffle.prover(shared_library, commitment_scheme.scheme, com, m, _m, r, ck,
                               commitment_scheme.rand, n_messages)
        result = Shuffle.verifier(shared_library, proof[0], proof[1], proof[2], proof[3], proof[4],
                                  commitment_scheme.scheme, proof[5], proof[6], com, _m, proof[7], ck, n_messages)
        print("Shuffle successful: ", result)


        print("Cleaning up")
        commitment_scheme.keyfree(ck)

        for i in range(n_messages):
            shared_library.commit_free(com[i])
            shared_library.commit_ptr_free(com[i])
            shared_library.nmod_poly_clear(m[i])
            shared_library.nmod_poly_clear(_m[i])
            for j in range(WIDTH):
                for k in range(2):
                    shared_library.nmod_poly_clear(r[i][j][k])
