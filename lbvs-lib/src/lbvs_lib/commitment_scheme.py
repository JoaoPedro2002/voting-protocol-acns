from .compile import WIDTH, DEGREE, MODP, ctypes, HEIGHT
from .classes import FLINT_RAND_T, NMOD_POLY_TYPE, PCRT_POLY_TYPE, CommitmentKey, Commitment, COMMITMENT_SCHEME_TYPE
from .utils import new_flint_random


class CommitmentScheme:
    def __init__(self, shared_library):
        self.clear_rand = False
        self.__shared_library = shared_library
        self.__is_loaded = False
        self.scheme = None
        self.rand = None

    def load(self, rand: FLINT_RAND_T = None):
        if self.__is_loaded:
            return
        self.scheme = COMMITMENT_SCHEME_TYPE()
        self.__shared_library.commit_scheme_init(self.scheme)
        if rand is None:
            rand = new_flint_random(self.__shared_library)
            self.clear_rand = True
        self.rand = rand
        self.__is_loaded = True

    def terminate(self):
        if not self.__is_loaded:
            return
        self.__shared_library.commit_scheme_finish(self.scheme)
        if self.clear_rand:
            self.__shared_library.flint_randclear(self.rand)
        self.__is_loaded = False

    def keygen(self) -> CommitmentKey:
        """
        Generate a key for the commitment scheme
        """
        key = CommitmentKey()
        self.__shared_library.commit_keygen(ctypes.byref(key), self.rand)
        return key

    def commit(self, key: CommitmentKey, message: NMOD_POLY_TYPE,
               rand_zero=False, only_r=False, commit_ref=None) -> tuple:
        """
        Commit to a message
        :param message: the message to commit to
        :param key: the commitment key
        :param rand_zero: if True, the randomness is set to zero (for the linear homomorphism)
        :param only_r: if True, only the commitment and randomness are returned
        :param commit_ref: if not None, the commitment is stored in the provided Commitment object
        :return: the commitment and the opening
        """
        r = self.__commit_randomness(rand_zero)
        if commit_ref is None:
            commitment = Commitment()
            commit_ref = ctypes.byref(commitment)
        else:
            commitment = commit_ref[0]

        self.__shared_library.commit_doit(self.scheme, commit_ref, message, ctypes.byref(key), r)

        if only_r:
            return commitment, r

        one = PCRT_POLY_TYPE()
        for i in range(2):
            self.__shared_library.nmod_poly_init(one[i], MODP)
            self.__shared_library.utils_nmod_poly_one(one[i])
        return commitment, (message, r, one)

    def __commit_randomness(self, zero=False) -> PCRT_POLY_TYPE * WIDTH:
        r = (PCRT_POLY_TYPE * WIDTH)()
        for i in range(WIDTH):
            for j in range(2):
                self.__shared_library.nmod_poly_init(r[i][j], MODP)

        for i in range(WIDTH):
            if zero:
                self.__shared_library.nmod_poly_zero(r[i][0])
                self.__shared_library.nmod_poly_zero(r[i][1])
            else:
                self.__shared_library.commit_sample_short_crt(self.scheme, r[i])

        return r

    def opening_challenge(self) -> PCRT_POLY_TYPE:
        f = PCRT_POLY_TYPE()
        for i in range(2):
            self.__shared_library.nmod_poly_init(f[i], MODP)

        self.__shared_library.commit_sample_chall_crt(self.scheme, f)
        return f

    def opening_randomness(self, r: PCRT_POLY_TYPE * WIDTH, f: PCRT_POLY_TYPE) -> PCRT_POLY_TYPE * WIDTH:
        s = (PCRT_POLY_TYPE * WIDTH)()
        for i in range(WIDTH):
            for j in range(2):
                self.__shared_library.nmod_poly_init(s[i][j], MODP)

        for i in range(WIDTH):
            for j in range(2):
                self.__shared_library.nmod_poly_mulmod(s[i][j], r[i][j], f[j],
                                                       self.__shared_library.commit_irred(self.scheme, j))
        return s

    def open_it(self, key: CommitmentKey, commitment: Commitment, opening):
        return self.open(key, commitment, *opening)

    def open(self, key: CommitmentKey, commitment: Commitment, message: NMOD_POLY_TYPE, s: PCRT_POLY_TYPE * WIDTH,
             f: PCRT_POLY_TYPE) -> bool:
        """
        Open a commitment
        :param commitment: the commitment to open
        :param message: the message to open the commitment on
        :param key: the commitment key
        :param s: the opening randomness
        :param f: the opening challenge
        :return: True if the commitment is valid, False otherwise
        """
        result = self.__shared_library.commit_open(
            self.scheme, ctypes.byref(commitment), message,
            ctypes.byref(key), s, f)
        return result == 1

    def message_rec(self, commitment: Commitment, key: CommitmentKey,
                    r: PCRT_POLY_TYPE * WIDTH) -> NMOD_POLY_TYPE:
        """
        Recovers the message from the commitment and the opening
        :param commitment: the commitment
        :param key: the key used to commit
        :param r: the commitment randomness
        :return: the recovered message
        """
        message = NMOD_POLY_TYPE()
        self.__shared_library.nmod_poly_init(message, MODP)
        result = self.__shared_library.commit_message_rec(self.scheme, message, ctypes.byref(commitment),
                                                          ctypes.byref(key), r)
        assert result == 1, "Message recovery failed"
        return message

    def message_rec_2(self, commitment: Commitment, key: CommitmentKey, r):
        message = NMOD_POLY_TYPE()
        self.__shared_library.nmod_poly_init(message, MODP)

        t = NMOD_POLY_TYPE()
        c1 = PCRT_POLY_TYPE()
        c2 = PCRT_POLY_TYPE()

        self.__shared_library.nmod_poly_init(t, MODP)

        for i in range(2):
            self.__shared_library.nmod_poly_init(c1[i], MODP)
            self.__shared_library.nmod_poly_init(c2[i], MODP)
            self.__shared_library.nmod_poly_zero(c1[i])
            self.__shared_library.nmod_poly_zero(c2[i])

        for i in range(HEIGHT):
            for j in range(WIDTH):
                for k in range(2):
                    self.__shared_library.nmod_poly_mulmod(t, key.B1[i][j][k], r[j][k],
                                                           self.__shared_library.commit_irred(self.scheme, k))
                    self.__shared_library.nmod_poly_add(c1[k], c1[k], t)
                    if i == 0:
                        self.__shared_library.nmod_poly_mulmod(t, key.b2[j][k], r[j][k],
                                                               self.__shared_library.commit_irred(self.scheme, k))
                        self.__shared_library.nmod_poly_add(c2[k], c2[k], t)

        for i in range(2):
            self.__shared_library.nmod_poly_sub(c1[i], commitment.c1[i], c1[i])
            self.__shared_library.nmod_poly_sub(c2[i], commitment.c2[i], c2[i])

        self.__shared_library.pcrt_poly_rec(self.scheme, t, c1)
        is_zero = self.__shared_library.nmod_poly_is_zero(t)

        self.__shared_library.pcrt_poly_rec(self.scheme, message, c2)

        return is_zero, message




    def keyfree(self, key: CommitmentKey):
        self.__shared_library.commit_keyfree(ctypes.byref(key))

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
        return False


if __name__ == "__main__":
    from .compile import shared_library

    wrapper = CommitmentScheme(shared_library)
    with wrapper as commitment_scheme:
        message = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(message, MODP)

        rho = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(rho, MODP)

        # Generate a random message
        shared_library.nmod_poly_randtest(message, commitment_scheme.rand, DEGREE)

        # Generate commitment key
        commit_key = commitment_scheme.keygen()

        # Commit
        commitment, d = commitment_scheme.commit(commit_key, message)
        result = commitment_scheme.open_it(commit_key, commitment, d)
        print("Result with opening with chal = 1:", result)
        r = d[1]

        _m = commitment_scheme.message_rec(commitment, commit_key, r)
        iszero, _m2 = commitment_scheme.message_rec_2(commitment, commit_key, r)
        result = shared_library.nmod_poly_equal(_m, message) == 1
        print("Message recovery from commit and r: ", result)
        result = shared_library.nmod_poly_equal(_m2, message) == 1
        print("Message recovery from commit and r: ", result)

        f = commitment_scheme.opening_challenge()
        shared_library.commit_sample_chall(rho)

        s = commitment_scheme.opening_randomness(r, f)

        # Open
        result = commitment_scheme.open(commit_key, commitment, message, s, f)
        print("Opening result: ", result)

        print("Testing linear homomorphism")
        _commitment, _d = commitment_scheme.commit(commit_key, rho, rand_zero=True, only_r=True)
        for i in range(2):
            shared_library.nmod_poly_sub(commitment.c1[i], commitment.c1[i], _commitment.c1[i])
            shared_library.nmod_poly_sub(commitment.c2[i], commitment.c2[i], _commitment.c2[i])

        shared_library.nmod_poly_sub(message, message, rho)

        result = commitment_scheme.open(commit_key, commitment, message, s, f)
        print("Opening result: ", result)

        shared_library.nmod_poly_clear(message)
        shared_library.nmod_poly_clear(rho)
        for i in range(WIDTH):
            for j in range(2):
                shared_library.nmod_poly_clear(r[i][j])
                shared_library.nmod_poly_clear(s[i][j])
                shared_library.nmod_poly_clear(_d[i][j])
        for i in range(2):
            shared_library.nmod_poly_clear(f[i])
            shared_library.nmod_poly_clear(d[2][i])

        commitment_scheme.keyfree(commit_key)
