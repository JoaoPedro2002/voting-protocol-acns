from .compile import WIDTH, DIM, VECTOR, shared_library
from .primitives import primitives
from .classes import ctypes, PCRT_POLY_TYPE, NMOD_POLY_TYPE, FMPZ_MOD_POLY_T, PrivateKey, PublicKey, Ciphertext, \
    Veritext, Commitment, CommitmentKey, OPENING_TYPE
from .utils import nmod_poly_to_string, fmpz_mod_poly_to_string, nmod_poly_from_string, fmpz_mod_poly_from_string

CLASSES = {}
STRUCTS = [PublicKey, PrivateKey, Ciphertext, Veritext, CommitmentKey, Commitment]
FIELDS_STRUCTS = {}
for struct in STRUCTS:
    fields = frozenset(f[0] for f in struct._fields_)
    FIELDS_STRUCTS[fields] = struct


def recursive_deserialize(obj, obj_structure, depth=0):
    if isinstance(obj_structure[depth], int):
        ret_l = []
        for i in range(obj_structure[depth]):
            ret_l.append(recursive_deserialize(obj[i], obj_structure, depth + 1))
        return ret_l

    if isinstance(obj_structure[depth], str):
        deserializer = CLASSES[ctypes.Structure.__name__][1]
    else:
        deserializer = CLASSES[obj_structure[depth].__name__][1]
    return deserializer.deserialize(obj)


def recursive_assign(c_obj, items_list):
    for i, item in enumerate(items_list):
        if isinstance(item, list):
            recursive_assign(c_obj[i], item)
        else:
            c_obj[i] = item


def get_serializer(obj):
    for clazz in CLASSES.values():
        if isinstance(obj, clazz[0]):
            return clazz[1]
    return None


def serialize(obj):
    return get_serializer(obj).serialize(obj)


def get_deserializer_struct(obj):
    keys = frozenset(obj.keys())
    if keys in FIELDS_STRUCTS:
        return FIELDS_STRUCTS[keys]
    return None


class Serializer:
    def __init__(self, clazz):
        self.__clazz = clazz
        CLASSES[clazz.__name__] = (clazz, self)

    def serialize(self, obj):
        raise NotImplementedError

    def deserialize(self, obj):
        raise NotImplementedError


class ArraySerializer(Serializer):
    def __init__(self):
        super().__init__(ctypes.Array)

    def serialize(self, obj):
        list = []
        for item in obj:
            serializer = get_serializer(item)
            if not serializer:
                raise Exception(f"No implementation for {item.__class__.__name__}")
            list.append(serializer.serialize(item))

        return list


class NmodPolySerializer(Serializer):
    def __init__(self):
        super().__init__(NMOD_POLY_TYPE)

    def serialize(self, obj):
        return nmod_poly_to_string(shared_library, obj)

    def deserialize(self, obj):
        return nmod_poly_from_string(shared_library, obj)


class FmpzModPolySerializer(Serializer):
    def __init__(self):
        super().__init__(FMPZ_MOD_POLY_T)

    def serialize(self, obj):
        return fmpz_mod_poly_to_string(shared_library, obj, primitives.vericrypt.context)

    def deserialize(self, obj):
        return fmpz_mod_poly_from_string(shared_library, obj, primitives.vericrypt.context)


def deserialize_c_obj(field, obj):
    if isinstance(field, tuple):
        field_class = field[1]
    else:
        field_class = field
    aux = field_class.__name__.split("_")
    i = 0
    objects = []
    while i < len(aux) - 1:
        if aux[i] == "Array":
            objects.append(int(aux[i + 1]))
            i += 1
        else:
            objects.append(aux[i])
        i += 1
    if objects[0] == 'FmpzModPoly':
        objects.pop(0)
        objects.pop(0)
        objects.insert(0, FMPZ_MOD_POLY_T)
    elif objects[0] == 'NmodPoly':
        objects.pop(0)
        objects.pop(0)
        objects.insert(0, NMOD_POLY_TYPE)
    objects.reverse()
    ret = recursive_deserialize(obj, objects)
    if isinstance(ret, list):
        c_obj = field_class()
        recursive_assign(c_obj, ret)
    else:
        c_obj = ret
    return c_obj


class StructSerializer(Serializer):
    def __init__(self):
        super().__init__(ctypes.Structure)

    def serialize(self, obj):
        json_obj = {}
        for field in obj._fields_:
            serializer = get_serializer(getattr(obj, field[0]))
            if not serializer:
                raise Exception(f"No implementation for {field[0].__class__.__name__}")
            json_obj[field[0]] = serializer.serialize(getattr(obj, field[0]))
        return json_obj

    def deserialize(self, json_obj):
        struct = get_deserializer_struct(json_obj)
        if not struct:
            raise Exception(f"No implementation for {json_obj.keys()}")

        params = {}
        for field in struct._fields_:
            field_name = field[0]
            c_obj = deserialize_c_obj(field, json_obj[field_name])

            params[field_name] = c_obj

        return struct(**params)


struct_serializer = StructSerializer()
NmodPolySerializer()
FmpzModPolySerializer()
# needs to come last place in the assigment (nmod and fmpz are also arrays types, but we treat them differently)
ArraySerializer()


def deserialize_pk(data):
    pk_C = struct_serializer.deserialize(data['pk_C'])
    pk_V = struct_serializer.deserialize(data['pk_V'])
    pk_R = struct_serializer.deserialize(data['pk_R'])

    return pk_C, pk_V, pk_R


def serialize_pk(obj):
    pk_C, pk_V, pk_R = obj
    return {
        "pk_C": serialize(pk_C),
        "pk_V": serialize(pk_V),
        "pk_R": serialize(pk_R)
    }


def deserialize_dk(data):
    pk_C = struct_serializer.deserialize(data['pk_C'])
    dk_V = struct_serializer.deserialize(data['dk_V'])

    return pk_C, dk_V


def serialize_dk(obj):
    pk_C, dk_V = obj

    return {
        "pk_C": serialize(pk_C),
        "dk_V": serialize(dk_V)
    }


def deserialize_ck(data):
    pk_C = struct_serializer.deserialize(data['pk_C'])
    pk_V = struct_serializer.deserialize(data['pk_V'])
    dk_R = struct_serializer.deserialize(data['dk_R'])

    return pk_C, pk_V, dk_R


def serialize_ck(obj):
    pk_C, pk_V, dk_R = obj

    return {
        "pk_C": serialize(pk_C),
        "pk_V": serialize(pk_V),
        "dk_R": serialize(dk_R)
    }


def deserialize_vvk(data):
    c_a = struct_serializer.deserialize(data)
    return c_a


def serialize_vvk(data):
    c_a = struct_serializer.serialize(data)
    return c_a


def deserialize_vck(data):
    a = deserialize_c_obj(NMOD_POLY_TYPE, data['a'])
    c_a = deserialize_vvk(data['c_a'])
    d_a = deserialize_c_obj(PCRT_POLY_TYPE * WIDTH, data['d_a'])

    return a, c_a, d_a


def serialize_vck(data):
    a, c_a, d_a = data

    return {
        "a": serialize(a),
        "c_a": serialize(c_a),
        "d_a": serialize(d_a)
    }


def deserialize_encrypted_ballot(data):
    c = struct_serializer.deserialize(data['c'])
    cipher = deserialize_c_obj(Ciphertext * WIDTH, data['cipher'])
    e_c = deserialize_c_obj(FMPZ_MOD_POLY_T, data['e_c'])

    return c, cipher, e_c


def serialize_encrypted_ballot(data):
    c, cipher, e_c = data

    return {
        "c": serialize(c),
        "cipher": serialize(cipher),
        "e_c": serialize(e_c)
    }


def deserialize_sum_proof(data):
    y1 = deserialize_c_obj(NMOD_POLY_TYPE * 2 * WIDTH, data['y1'])
    y2 = deserialize_c_obj(NMOD_POLY_TYPE * 2 * WIDTH, data['y2'])
    y3 = deserialize_c_obj(NMOD_POLY_TYPE * 2 * WIDTH, data['y3'])
    t1 = deserialize_c_obj(NMOD_POLY_TYPE * 2, data['t1'])
    t2 = deserialize_c_obj(NMOD_POLY_TYPE * 2, data['t2'])
    t3 = deserialize_c_obj(NMOD_POLY_TYPE * 2, data['t3'])
    u = deserialize_c_obj(NMOD_POLY_TYPE * 2, data['u'])

    return y1, y2, y3, t1, t2, t3, u


def serialize_sum_proof(data):
    y1, y2, y3, t1, t2, t3, u = data

    return {
        "y1": serialize(y1),
        "y2": serialize(y2),
        "y3": serialize(y3),
        "t1": serialize(t1),
        "t2": serialize(t2),
        "t3": serialize(t3),
        "u": serialize(u)
    }

def deserialize_ballot_proof(data):
    r = deserialize_c_obj(FMPZ_MOD_POLY_T * 2 * DIM * VECTOR, data['z']['r'])
    e = deserialize_c_obj(FMPZ_MOD_POLY_T * 2 * DIM * VECTOR, data['z']['e'])
    e_ = deserialize_c_obj(FMPZ_MOD_POLY_T * 2 * VECTOR, data['z']['e_'])
    u = deserialize_c_obj(FMPZ_MOD_POLY_T * VECTOR, data['z']['u'])

    z = (r, e, e_, u)

    c_r = struct_serializer.deserialize(data['c_r'])

    e_r = struct_serializer.deserialize(data['e_r'])

    proof = deserialize_sum_proof(data['proof'])

    return z, c_r, e_r, proof


def serialize_z(z):
    r, e, e_, u = z

    return {
        "r": serialize(r),
        "e": serialize(e),
        "e_": serialize(e_),
        "u": serialize(u)
    }


def serialize_ballot_proof(data):
    z, c_r, e_r, proof = data

    return {
        "z": serialize_z(z),
        "c_r": serialize(c_r),
        "e_r": serialize(e_r),
        "proof": serialize_sum_proof(proof)
    }


def deserialize_shuffle_proof(data):
    length = len(data['y'])
    d = deserialize_c_obj(Commitment * length, data['d'])
    y = deserialize_c_obj(OPENING_TYPE * length, data['y'])
    _y = deserialize_c_obj(OPENING_TYPE * length, data['_y'])
    t = deserialize_c_obj(PCRT_POLY_TYPE * length, data['t'])
    _t = deserialize_c_obj(PCRT_POLY_TYPE * length, data['_t'])
    u = deserialize_c_obj(PCRT_POLY_TYPE * length, data['u'])
    s = deserialize_c_obj(NMOD_POLY_TYPE * length, data['s'])
    rho = deserialize_c_obj(NMOD_POLY_TYPE, data['rho'])

    return y, _y, t, _t, u, d, s, rho


def serialize_shuffle_proof(data):
    y, _y, t, _t, u, d, s, rho = data

    return {
        "y": serialize(y),
        "_y": serialize(_y),
        "t": serialize(t),
        "_t": serialize(_t),
        "u": serialize(u),
        "d": serialize(d),
        "s": serialize(s),
        "rho": serialize(rho)
    }
