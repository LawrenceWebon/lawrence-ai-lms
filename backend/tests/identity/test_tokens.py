from __future__ import annotations

from collections.abc import Mapping

import pytest

from lms.modules.identity.tokens import (
    CachedJwks,
    JwksSourceUnavailableError,
    JwtVerificationConfig,
    JwtVerifier,
    TokenInvalidError,
    TokenVerificationUnavailableError,
)
from tests.identity.jwt_test_support import PRIMARY_KEY, ROTATED_KEY, access_token

NOW = 1_800_000_000


class MutableJwksSource:
    def __init__(self, *responses: Mapping[str, object] | Exception) -> None:
        self.responses = list(responses)
        self.calls = 0

    def fetch(self) -> Mapping[str, object]:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        if isinstance(response, Exception):
            raise JwksSourceUnavailableError from response
        return response


def jwks(*keys: object) -> dict[str, object]:
    return {"keys": [key.public_jwk() for key in keys]}  # type: ignore[attr-defined]


def verifier(source: MutableJwksSource, *, monotonic: list[float] | None = None) -> JwtVerifier:
    monotonic_value = monotonic or [0.0]
    return JwtVerifier(
        config=JwtVerificationConfig(
            issuer="https://synthetic.supabase.co/auth/v1",
            audience="authenticated",
            role="authenticated",
            clock_skew_seconds=60,
        ),
        keys=CachedJwks(
            source=source,
            ttl_seconds=300,
            monotonic=lambda: monotonic_value[0],
        ),
        clock=lambda: NOW,
    )


def test_valid_rs256_token_returns_only_identity_claims() -> None:
    verified = verifier(MutableJwksSource(jwks(PRIMARY_KEY))).verify(
        access_token(
            now=NOW,
            claim_overrides={"email": " Synthetic-Instructor@Example.Invalid "},
        )
    )

    assert str(verified.subject) == "00000000-0000-4000-8000-000000000102"
    assert str(verified.session_id) == "10000000-0000-4000-8000-000000000001"
    assert verified.assurance_level == "aal1"
    assert verified.verified_email == "synthetic-instructor@example.invalid"
    assert int(verified.authentication_time.timestamp()) == NOW - 30
    assert not hasattr(verified, "role")
    assert not hasattr(verified, "tenant_id")


@pytest.mark.parametrize(
    ("header", "claims"),
    [
        ({"alg": "none"}, {}),
        ({"alg": "HS256"}, {}),
        ({"kid": "unknown"}, {}),
        ({"jku": "https://attacker.invalid/jwks.json"}, {}),
        ({"crit": ["synthetic-extension"]}, {}),
        ({}, {"exp": NOW - 60}),
        ({}, {"exp": NOW - 61}),
        ({}, {"nbf": NOW + 61}),
        ({}, {"iat": NOW + 61}),
        ({}, {"iss": "https://other.supabase.co/auth/v1"}),
        ({}, {"aud": "other"}),
        ({}, {"role": "service_role"}),
        ({}, {"sub": "not-a-uuid"}),
        ({}, {"session_id": "not-a-uuid"}),
        ({}, {"aal": "aal3"}),
        ({}, {"email": ""}),
        ({}, {"email": "not-an-email"}),
        ({}, {"email": "bad address@example.invalid"}),
        ({}, {"email": f"{'a' * 244}@example.invalid"}),
    ],
)
def test_token_matrix_fails_closed(header: dict[str, object], claims: dict[str, object]) -> None:
    token = access_token(now=NOW, header_overrides=header, claim_overrides=claims)

    with pytest.raises(TokenInvalidError):
        verifier(MutableJwksSource(jwks(PRIMARY_KEY))).verify(token)


@pytest.mark.parametrize("token", ["", "one", "one.two", "one.two.three.four", "%%%.e30.sig"])
def test_malformed_compact_tokens_fail_closed(token: str) -> None:
    with pytest.raises(TokenInvalidError):
        verifier(MutableJwksSource(jwks(PRIMARY_KEY))).verify(token)


def test_signature_from_a_different_key_is_rejected() -> None:
    token = access_token(
        key=ROTATED_KEY,
        now=NOW,
        header_overrides={"kid": PRIMARY_KEY.kid},
    )

    with pytest.raises(TokenInvalidError):
        verifier(MutableJwksSource(jwks(PRIMARY_KEY))).verify(token)


def test_unknown_kid_refreshes_exactly_once() -> None:
    source = MutableJwksSource(jwks(PRIMARY_KEY), jwks(PRIMARY_KEY))
    token_verifier = verifier(source)
    token_verifier.verify(access_token(now=NOW))

    with pytest.raises(TokenInvalidError):
        token_verifier.verify(access_token(now=NOW, header_overrides={"kid": "unknown"}))

    assert source.calls == 2


def test_rotation_overlap_accepts_old_and_new_keys_after_refresh() -> None:
    source = MutableJwksSource(jwks(PRIMARY_KEY), jwks(PRIMARY_KEY, ROTATED_KEY))
    token_verifier = verifier(source)

    token_verifier.verify(access_token(key=PRIMARY_KEY, now=NOW))
    token_verifier.verify(access_token(key=ROTATED_KEY, now=NOW))
    token_verifier.verify(access_token(key=PRIMARY_KEY, now=NOW))

    assert source.calls == 2


def test_initial_jwks_outage_fails_closed() -> None:
    source = MutableJwksSource(OSError("synthetic outage"))

    with pytest.raises(TokenVerificationUnavailableError):
        verifier(source).verify(access_token(now=NOW))


def test_expired_key_cache_is_not_used_during_an_outage() -> None:
    monotonic = [0.0]
    source = MutableJwksSource(jwks(PRIMARY_KEY), OSError("synthetic outage"))
    token_verifier = verifier(source, monotonic=monotonic)
    token_verifier.verify(access_token(now=NOW))
    monotonic[0] = 301.0

    with pytest.raises(TokenVerificationUnavailableError):
        token_verifier.verify(access_token(now=NOW))
