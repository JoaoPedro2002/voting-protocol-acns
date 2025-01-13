import base64

from .compile import MODP, shared_library, DEGREE
from .classes import NMOD_POLY_TYPE
from .utils import nmod_poly_to_string, get_all_voting_combinations
from Crypto.Hash import HMAC, SHA512


class ReturnCodeTable:
    @staticmethod
    def new_key():
        from .utils import random
        return random.getrandbits(512).to_bytes(64, byteorder='big')

    @staticmethod
    def encode_key(key: bytes):
        return base64.b64encode(key).decode('ascii')

    @staticmethod
    def decode_key(key: str):
        return base64.b64decode(key)

    @staticmethod
    def prf(key: bytes, message: bytes):
        h = HMAC.new(key, digestmod=SHA512)
        h.update(message)
        return h.digest()

    @staticmethod
    def compute_table(key: bytes, blinding_key: NMOD_POLY_TYPE, question: dict=None, combinations: iter=None, b64=False):
        if question and not combinations:
            answers = range(len(question['answers']))
            minimum = question['min']
            maximum = question['max']
            combinations = get_all_voting_combinations(answers, minimum, maximum)
        elif not combinations:
            raise ValueError("Either question or combinations must be provided")

        poly = NMOD_POLY_TYPE()
        shared_library.nmod_poly_init(poly, MODP)

        # generate all polynomials possible for the given question
        table = {}
        for combination in combinations:
            shared_library.nmod_poly_zero(poly)
            for item in combination:
                shared_library.nmod_poly_set_coeff_ui(poly, item, 1)

            s = nmod_poly_to_string(shared_library, poly)

            shared_library.nmod_poly_add(poly, blinding_key, poly)
            r_bytes = str.encode(s, encoding='utf-8')
            code = ReturnCodeTable.prf(key, r_bytes)

            if b64:
                b64_s = base64.b64encode(s.encode('utf-8')).decode('utf-8')
                table[b64_s] = base64.b64encode(code).decode('utf-8')
            else:
                table[s] = code

        shared_library.nmod_poly_clear(poly)
        return table

    @staticmethod
    def nmod_table_key(poly: NMOD_POLY_TYPE, b64=False):
        s = nmod_poly_to_string(shared_library, poly)
        return base64.b64encode(s.encode('utf-8')).decode('utf-8') if b64 else s

    @staticmethod
    def nmod_prf(key: bytes, message: NMOD_POLY_TYPE, b64=False):
        s = nmod_poly_to_string(shared_library, message)
        byte_array = str.encode(s, encoding='utf-8')
        prf = ReturnCodeTable.prf(key, byte_array)
        if b64:
            prf = base64.b64encode(prf).decode('utf-8')
        return prf


if __name__ == "__main__":
    from .utils import new_flint_random

    code_key = ReturnCodeTable.new_key()
    print(f"Code key: {code_key.hex()}")

    rand = new_flint_random(shared_library)

    a = NMOD_POLY_TYPE()
    shared_library.nmod_poly_init(a, MODP)
    shared_library.nmod_poly_randtest(a, rand, DEGREE)

    table = ReturnCodeTable.compute_table(code_key, a, {
                                              "answers": range(5),
                                              "min": 2,
                                              "max": 3
                                          }, b64=True)

    for key, value in table.items():
        print(f"{key} -> {value}")

    shared_library.nmod_poly_clear(a)
    shared_library.flint_randclear(rand)
