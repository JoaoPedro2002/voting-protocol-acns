from .compile import WIDTH, DEGREE, MODP, ctypes
from .classes import NMOD_POLY_TYPE, COMMITMENT_SCHEME_TYPE, Commitment, CommitmentKey


class ProtocolLin:
    """
    This represents a Sigma-protocol to prove the relation _x = alpha x + beta, given
    the commitments [[x]], [[_x]] and the scalars alpha, beta.

    y:  sample according to a Gaussian distribution in CRT rep
    _y: sample according to a Gaussian distribution in CRT rep
    t:  sum of the multiplication of y with the commitment key (B1)
    _t: sum of the multiplication of _y with the commitment key (B2)
    u:  sum(y * commitment_key (b2) * alpha) - sum(_y * commitment_key (b2))

    alpha: the scalar alpha
    beta: the scalar beta

    x:  the commitment to x
    _x: the commitment to _x
    key: the commitment key
    scheme: the commitment scheme
    """
    def __init__(self, shared_library):
        self.shared_library = shared_library
        self.y = None
        self._y = None
        self.t = None
        self._t = None
        self.u = None

        self.alpha = None
        self.beta = None

        self.x = None
        self._x = None
        self.key = None
        self.scheme = None

        self.__state = 0

    def set_alpha_beta(self, alpha: NMOD_POLY_TYPE, beta: NMOD_POLY_TYPE):
        self.alpha = alpha
        self.beta = beta

    def set_commitments(self, x: Commitment, _x: Commitment, key: CommitmentKey, scheme: COMMITMENT_SCHEME_TYPE):
        self.x = x
        self._x = _x
        self.key = key
        self.scheme = scheme

    def load(self):
        self.y = (NMOD_POLY_TYPE * 2 * WIDTH)()
        self._y = (NMOD_POLY_TYPE * 2 * WIDTH)()
        self.t = (NMOD_POLY_TYPE * 2)()
        self._t = (NMOD_POLY_TYPE * 2)()
        self.u = (NMOD_POLY_TYPE * 2)()

        for i in range(2):
            shared_library.nmod_poly_init(self.t[i], MODP)
            shared_library.nmod_poly_init(self._t[i], MODP)
            shared_library.nmod_poly_init(self.u[i], MODP)

        for i in range(WIDTH):
            for j in range(2):
                shared_library.nmod_poly_init(self.y[i][j], MODP)
                shared_library.nmod_poly_init(self._y[i][j], MODP)

        self.__state = 1

    def terminate(self):
        for i in range(2):
            self.shared_library.nmod_poly_clear(self.t[i])
            self.shared_library.nmod_poly_clear(self._t[i])
            self.shared_library.nmod_poly_clear(self.u[i])

        for i in range(WIDTH):
            for j in range(2):
                self.shared_library.nmod_poly_clear(self.y[i][j])
                self.shared_library.nmod_poly_clear(self._y[i][j])

        if self.alpha is not None:
            self.shared_library.nmod_poly_clear(self.alpha)
        if self.beta is not None:
            self.shared_library.nmod_poly_clear(self.beta)

        if self.x is not None:
            self.shared_library.commit_free(ctypes.byref(self.x))
        if self._x is not None:
            self.shared_library.commit_free(ctypes.byref(self._x))

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
        return False

    def lin_prover(self, r: NMOD_POLY_TYPE * 2 * WIDTH, _r: NMOD_POLY_TYPE * 2 * WIDTH, l: ctypes.c_int = 0):
        """
        Prover for the linear protocol
        :param r: the x commitment randomness
        :param _r: the _x commitment randomness
        :param l: # TODO what is this? probably number of msgs
        """
        assert self.__state == 1, "The protocol is not loaded"
        for v in [self.alpha, self.beta, self.x, self._x, self.key, self.scheme]:
            assert v is not None
        self.shared_library.lin_prover(self.y, self._y, self.t, self._t, self.u, self.scheme, self.x, self._x,
                                  ctypes.byref(self.key), self.alpha, self.beta, r, _r, l)
        self.__state = 2

    def lin_verifier(self, l: ctypes.c_int = 0, len=0):
        """
        Prover for the linear protocol
        :param l: # Not used, it's for the shuffle protocol
        :param len: # shuffle protocol msg length
        :return: 1 if the proof is valid, 0 otherwise
        """
        assert self.__state == 2, "The prover has not run yet"
        return self.shared_library.lin_verifier(self.y, self._y, self.t, self._t, self.u, self.scheme, self.x, self._x,
                                           ctypes.byref(self.key), self.alpha, self.beta, l, len)

    @staticmethod
    def prover(shared_library, scheme, x, _x, key, alpha, beta, r, _r, l=0):
        y = (NMOD_POLY_TYPE * 2 * WIDTH)()
        _y = (NMOD_POLY_TYPE * 2 * WIDTH)()
        t = (NMOD_POLY_TYPE * 2)()
        _t = (NMOD_POLY_TYPE * 2)()
        u = (NMOD_POLY_TYPE * 2)()

        for i in range(2):
            shared_library.nmod_poly_init(t[i], MODP)
            shared_library.nmod_poly_init(_t[i], MODP)
            shared_library.nmod_poly_init(u[i], MODP)

        for i in range(WIDTH):
            for j in range(2):
                shared_library.nmod_poly_init(y[i][j], MODP)
                shared_library.nmod_poly_init(_y[i][j], MODP)

        shared_library.lin_prover(y, _y, t, _t, u, scheme, x, _x, ctypes.byref(key), alpha, beta, r, _r, l)
        return y, _y, t, _t, u

    @staticmethod
    def verifier(shared_library, y, _y, t, _t, u, scheme, x, _x, key, alpha, beta, l=0, len=0):
        return shared_library.lin_verifier(y, _y, t, _t, u, scheme, x, _x, ctypes.byref(key), alpha, beta, l, len)

if __name__ == "__main__":
    from .commitment_scheme import CommitmentScheme
    from .compile import shared_library
    wrapper = CommitmentScheme(shared_library)
    with wrapper as commitment_scheme:
        print("Starting test")

        print("Keygen")
        ck = commitment_scheme.keygen()

        m = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(m, MODP)
        shared_library.nmod_poly_randtest(m, commitment_scheme.rand, DEGREE)
        x, d_x = commitment_scheme.commit(ck, m)

        alpha = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(alpha, MODP)
        shared_library.utils_nmod_poly_one(alpha)

        beta = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(beta, MODP)
        shared_library.utils_nmod_poly_one(beta)

        _m = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(_m, MODP)
        shared_library.utils_nmod_poly_zero(_m)
        # _m = alpha m + beta
        # in this case _m = m + 1
        shared_library.nmod_poly_mul(_m, m, alpha)
        shared_library.nmod_poly_add(_m, _m, beta)
        _x, _d_x = commitment_scheme.commit(ck, _m)

        r = d_x[1]
        _r = _d_x[1]

        protocol = ProtocolLin(shared_library)
        with protocol as prover:
            prover.set_alpha_beta(alpha, beta)
            prover.set_commitments(x, _x, ck, commitment_scheme.scheme)
            prover.lin_prover(r, _r)
            print("Proof is valid: ", prover.lin_verifier())

        print("Prover variables cleared")

        print("Cleaning up")
        shared_library.nmod_poly_clear(m)
        shared_library.nmod_poly_clear(_m)

        for i in range(WIDTH):
            for j in range(2):
                shared_library.nmod_poly_clear(r[i][j])
                shared_library.nmod_poly_clear(_r[i][j])

        for i in range(2):
            shared_library.nmod_poly_clear(d_x[2][i])
            shared_library.nmod_poly_clear(_d_x[2][i])
