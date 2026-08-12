from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _integer_base64url(value: int) -> str:
    return _base64url(value.to_bytes((value.bit_length() + 7) // 8, "big"))


@dataclass(frozen=True, slots=True)
class RsaTestKey:
    kid: str
    modulus: int
    private_exponent: int
    public_exponent: int = 65537

    def public_jwk(self) -> dict[str, object]:
        return {
            "alg": "RS256",
            "e": _integer_base64url(self.public_exponent),
            "kid": self.kid,
            "kty": "RSA",
            "n": _integer_base64url(self.modulus),
            "use": "sig",
        }

    def sign(self, signing_input: bytes) -> bytes:
        digest_info = bytes.fromhex("3031300d060960864801650304020105000420")
        digest_info += hashlib.sha256(signing_input).digest()
        width = (self.modulus.bit_length() + 7) // 8
        encoded = b"\x00\x01" + (b"\xff" * (width - len(digest_info) - 3))
        encoded += b"\x00" + digest_info
        signature = pow(int.from_bytes(encoded, "big"), self.private_exponent, self.modulus)
        return signature.to_bytes(width, "big")


PRIMARY_KEY = RsaTestKey(
    kid="synthetic-primary",
    modulus=int(
        "b25d5f9c776e818607452636090fb58c39cbedc3cb33c1e50863b2a95b9cd57e"
        "f7a03fdaa18fd1f2a696e95b9c83c5104472588c73e6646701db3c97bcaf56bb"
        "2b1dfbe6a2bd550b33602fac7c49e67cb916a8a1b55954d274f1d4b4ae0e8223"
        "d008e506caa77acb2bf9d020536a870a37cb04cf8216d270014e80fc4be8ee38f"
        "4303052987b1372e90bd31b385ad9f6543ed12b849ca25b5f6ac091ba7cad6b2d"
        "0822c3e542d6ca9a1390e9408a3bf33ec065f55a2afa49eb6eefcc01cee283d07"
        "81ac296fbc934652ba9d5f491741d59a543ceebc0b957d0c09095660a6ab36a38"
        "70bf5beaf2c17ac21eba4f089c96621655143a7887077803eb58ebd8e455",
        16,
    ),
    private_exponent=int(
        "0a3fc1a28b88543555389cd1510efa8724111048b110a322712b7814dc389f04a"
        "1dfaef0f604a8c8912dadc61505cb593bc84d9c9b27a625a1c92d14fe58c8453"
        "95d35357e5773ca10cf2f9e1bdc36917c79e2ac66c5207c76ba28aca32dc93e4"
        "6922445922287df4c826e7a550b68d6bba2ffa9442d3735616b2c8fe820152ece"
        "fb9b78170ecc28cd6b63722165f45a1605185df8415ad275f1d403253b189a46c"
        "5bed234542e6730b901d572b423527eac9bdb5322e36ca5a9159d710a07f31d6c"
        "eca3bd82e105e515d5fabd373f1c10151357f56f3d9e75a3ede0540854e87f269"
        "7a1569ccaa81122c962dbc7db6f034645ad560f9acf33a7735762b2f391",
        16,
    ),
)

ROTATED_KEY = RsaTestKey(
    kid="synthetic-rotated",
    modulus=int(
        "dd5a3a9c49ba0a24e0dea471c5c3dc0de55765db40e7a66bb3762f52552265d7"
        "2c31fbe17477989f490b33ee89c2a0311483d9ad3a863ad889ac9d27d7617908"
        "b38af2aa2ee193f95744b9e5d9337e168afad3f3ad7a5e6da8adac5be6373325"
        "92dfa4895d40bd086b1228d13edca83208fad8b8f75a1dce384a2133a48088f60"
        "5ab61e5fc6a90995fadef7c3a3871b30679dafff8a7023d47c5f890d0081914f8"
        "d7af1b520a9c76776b8e5973ae3d522173d19caf1fa1d83d814c28ada44245b8a"
        "db602b1574a89e2bdc28df96f668d589bc18a4cd7f5b3b3254f46238e205905f"
        "259f76867831c36c2d7ebfe85df65285ab1887c4fea855344715e126016d7",
        16,
    ),
    private_exponent=int(
        "5c0992693db69f552a3329092d83fcd1c2548ec395bf3c5177f36245c7a45fd8"
        "12464e4736582c1bbf116b6c79d77528333187a721b8826b5b036ced0dff3786"
        "48b133a95388f4302efb2298d1b1397242237d51cb062091541bb2991ba6441c1"
        "16ff04835801f998a7ba88128b433336acc72a4a624d053d8cfe9f2412a38c7d"
        "cb83d751d1b685cef4ac2636ed3d4d22add3c33800c74ff1ad0492be22fd543b"
        "8b72a13d59267fc34b9556202cf2b339559c30cd94d1deb40cbd9c9f4139c527"
        "01a33243cc2af5f6fb65ad2f56a7307caa42a2c5757e9a3449c36e5842f80822"
        "10a1a4f0d5f7a098785af5c5a53d08eaa9c7acefc4e4d39eaf28d1161207e31",
        16,
    ),
)


def access_token(
    *,
    key: RsaTestKey = PRIMARY_KEY,
    now: int = 1_800_000_000,
    header_overrides: dict[str, object] | None = None,
    claim_overrides: dict[str, object] | None = None,
) -> str:
    header: dict[str, object] = {"alg": "RS256", "kid": key.kid, "typ": "JWT"}
    claims: dict[str, object] = {
        "aal": "aal1",
        "aud": "authenticated",
        "email": "synthetic-instructor@example.invalid",
        "exp": now + 300,
        "iat": now - 30,
        "is_anonymous": False,
        "iss": "https://synthetic.supabase.co/auth/v1",
        "phone": "",
        "role": "authenticated",
        "session_id": "10000000-0000-4000-8000-000000000001",
        "sub": "00000000-0000-4000-8000-000000000102",
    }
    if header_overrides:
        header.update(header_overrides)
    if claim_overrides:
        claims.update(claim_overrides)
    encoded_header = _base64url(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    encoded_claims = _base64url(
        json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_claims}".encode("ascii")
    return f"{signing_input.decode('ascii')}.{_base64url(key.sign(signing_input))}"
