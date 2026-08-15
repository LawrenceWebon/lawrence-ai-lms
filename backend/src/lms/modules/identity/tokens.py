from __future__ import annotations

import base64
import binascii
import json
import math
import re
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast
from urllib.parse import urlparse
from urllib.request import urlopen
from uuid import UUID

import jwt

from .entities import AssuranceLevel, VerifiedAccessToken

_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_TOKEN_BYTES = 16_384
_MAX_JWKS_BYTES = 65_536
_SUPPORTED_KEY_TYPES = {"ES256": "EC", "RS256": "RSA"}
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TokenInvalidError(Exception):
    """The presented token cannot establish an identity."""


class TokenVerificationUnavailableError(TokenInvalidError):
    """Trusted signing keys could not be obtained or validated."""


class JwksSourceUnavailableError(Exception):
    """The configured JWKS source did not return a usable document."""


class JwksSource(Protocol):
    def fetch(self) -> Mapping[str, object]: ...


@dataclass(frozen=True, slots=True)
class JwtVerificationConfig:
    issuer: str
    audience: str
    role: str
    clock_skew_seconds: int = 60
    allowed_algorithms: tuple[str, ...] = ("ES256", "RS256")

    def __post_init__(self) -> None:
        parsed = urlparse(self.issuer)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("JWT issuer must be a configured HTTPS origin/path")
        if not self.audience or not self.role:
            raise ValueError("JWT audience and role must be configured")
        if not 0 <= self.clock_skew_seconds <= 300:
            raise ValueError("JWT clock skew must be between zero and 300 seconds")
        if (
            not self.allowed_algorithms
            or len(set(self.allowed_algorithms)) != len(self.allowed_algorithms)
            or any(algorithm not in _SUPPORTED_KEY_TYPES for algorithm in self.allowed_algorithms)
        ):
            raise ValueError("JWT algorithms must be a unique subset of ES256 and RS256")


class HttpsJwksSource:
    """Bounded fetcher for one configured HTTPS JWKS endpoint."""

    def __init__(self, *, url: str, timeout_seconds: float = 2.0) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("JWKS URL must be a configured HTTPS endpoint")
        if not 0 < timeout_seconds <= 10:
            raise ValueError("JWKS timeout must be greater than zero and at most ten seconds")
        self._url = url
        self._timeout_seconds = timeout_seconds

    def fetch(self) -> Mapping[str, object]:
        try:
            with urlopen(self._url, timeout=self._timeout_seconds) as response:  # noqa: S310
                if response.geturl() != self._url:
                    raise JwksSourceUnavailableError(
                        "configured JWKS endpoint redirected unexpectedly"
                    )
                payload = response.read(_MAX_JWKS_BYTES + 1)
        except (OSError, TimeoutError, ValueError) as error:
            raise JwksSourceUnavailableError("configured JWKS endpoint is unavailable") from error
        if len(payload) > _MAX_JWKS_BYTES:
            raise JwksSourceUnavailableError("configured JWKS response exceeds the size limit")
        try:
            return _strict_json_object(payload)
        except (TokenInvalidError, UnicodeDecodeError) as error:
            raise JwksSourceUnavailableError("configured JWKS response is malformed") from error


@dataclass(frozen=True, slots=True)
class _VerificationKey:
    kid: str
    algorithm: str
    key: jwt.PyJWK


class CachedJwks:
    """Small in-process key cache with one refresh for an unknown key id."""

    def __init__(
        self,
        *,
        source: JwksSource,
        ttl_seconds: int = 300,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 1 <= ttl_seconds <= 600:
            raise ValueError("JWKS cache TTL must be between one and 600 seconds")
        self._source = source
        self._ttl_seconds = ttl_seconds
        self._monotonic = monotonic
        self._keys: dict[str, _VerificationKey] = {}
        self._expires_at = 0.0
        self._lock = threading.RLock()

    def get(self, *, kid: str, algorithm: str) -> _VerificationKey:
        with self._lock:
            now = self._monotonic()
            key = self._keys.get(kid)
            if key is not None and key.algorithm == algorithm and now < self._expires_at:
                return key
            self._refresh(now=now)
            key = self._keys.get(kid)
            if key is None or key.algorithm != algorithm:
                raise TokenInvalidError
            return key

    def _refresh(self, *, now: float) -> None:
        try:
            document = self._source.fetch()
            keys = _parse_jwks(document)
        except JwksSourceUnavailableError as error:
            raise TokenVerificationUnavailableError from error
        self._keys = keys
        self._expires_at = now + self._ttl_seconds


class JwtVerifier:
    def __init__(
        self,
        *,
        config: JwtVerificationConfig,
        keys: CachedJwks,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._config = config
        self._keys = keys
        self._clock = clock

    def verify(self, token: str) -> VerifiedAccessToken:
        header, unverified_claims = _decode_compact_token(token)
        algorithm = _required_string(header, "alg")
        if algorithm not in self._config.allowed_algorithms:
            raise TokenInvalidError
        token_type = header.get("typ")
        if token_type is not None and token_type != "JWT":  # noqa: S105 -- JOSE type
            raise TokenInvalidError
        if any(name in header for name in ("b64", "crit", "jku", "jwk", "x5u")):
            raise TokenInvalidError
        kid = _required_string(header, "kid")
        key = self._keys.get(kid=kid, algorithm=algorithm)

        try:
            decoded = cast(
                dict[str, object],
                jwt.decode(
                    token,
                    key=key.key.key,
                    algorithms=[algorithm],
                    audience=self._config.audience,
                    issuer=self._config.issuer,
                    options={
                        "require": [
                            "aal",
                            "aud",
                            "email",
                            "exp",
                            "iat",
                            "is_anonymous",
                            "iss",
                            "phone",
                            "role",
                            "session_id",
                            "sub",
                        ],
                        "verify_exp": False,
                        "verify_iat": False,
                        "verify_nbf": False,
                    },
                ),
            )
        except jwt.PyJWTError as error:
            raise TokenInvalidError from error
        if decoded != unverified_claims:
            raise TokenInvalidError

        now = self._clock()
        skew = self._config.clock_skew_seconds
        expires_at = _numeric_date(decoded, "exp")
        issued_at = _numeric_date(decoded, "iat")
        if expires_at <= now - skew or issued_at > now + skew:
            raise TokenInvalidError
        if "nbf" in decoded and _numeric_date(decoded, "nbf") > now + skew:
            raise TokenInvalidError
        if issued_at > expires_at:
            raise TokenInvalidError
        if _required_string(decoded, "role") != self._config.role:
            raise TokenInvalidError
        if decoded.get("is_anonymous") is not False:
            raise TokenInvalidError
        verified_email = _normalized_email(decoded)
        _required_text(decoded, "phone")

        subject = _required_uuid(decoded, "sub")
        session_id = _required_uuid(decoded, "session_id")
        assurance = _required_string(decoded, "aal")
        if assurance not in ("aal1", "aal2"):
            raise TokenInvalidError
        try:
            authentication_time = datetime.fromtimestamp(issued_at, tz=UTC)
        except (OverflowError, OSError, ValueError) as error:
            raise TokenInvalidError from error
        return VerifiedAccessToken(
            subject=subject,
            session_id=session_id,
            authentication_time=authentication_time,
            assurance_level=cast(AssuranceLevel, assurance),
            verified_email=verified_email,
        )


def _decode_compact_token(token: str) -> tuple[Mapping[str, object], Mapping[str, object]]:
    if not token or len(token.encode("utf-8")) > _MAX_TOKEN_BYTES:
        raise TokenInvalidError
    parts = token.split(".")
    if len(parts) != 3 or any(not part for part in parts):
        raise TokenInvalidError
    encoded_header, encoded_claims, encoded_signature = parts
    try:
        header = _strict_json_object(_decode_base64url(encoded_header))
        claims = _strict_json_object(_decode_base64url(encoded_claims))
        _decode_base64url(encoded_signature)
    except UnicodeDecodeError as error:
        raise TokenInvalidError from error
    return header, claims


def _decode_base64url(value: str) -> bytes:
    if not value or _BASE64URL.fullmatch(value) is None:
        raise TokenInvalidError
    padding = "=" * (-len(value) % 4)
    try:
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as error:
        raise TokenInvalidError from error


def _strict_json_object(payload: bytes) -> Mapping[str, object]:
    def unique_object(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise TokenInvalidError
            result[key] = value
        return result

    try:
        value = json.loads(payload, object_pairs_hook=unique_object)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise TokenInvalidError from error
    if not isinstance(value, dict):
        raise TokenInvalidError
    return cast(Mapping[str, object], value)


def _parse_jwks(document: Mapping[str, object]) -> dict[str, _VerificationKey]:
    raw_keys = document.get("keys")
    if not isinstance(raw_keys, list) or not 1 <= len(raw_keys) <= 32:
        raise TokenVerificationUnavailableError
    parsed: dict[str, _VerificationKey] = {}
    for raw_key in raw_keys:
        if not isinstance(raw_key, dict):
            raise TokenVerificationUnavailableError
        raw_mapping = cast(Mapping[str, object], raw_key)
        algorithm = raw_mapping.get("alg")
        if not isinstance(algorithm, str) or algorithm not in _SUPPORTED_KEY_TYPES:
            continue
        key = _parse_jwk(raw_mapping, algorithm=algorithm)
        if key.kid in parsed:
            raise TokenVerificationUnavailableError
        parsed[key.kid] = key
    if not parsed:
        raise TokenVerificationUnavailableError
    return parsed


def _parse_jwk(jwk: Mapping[str, object], *, algorithm: str) -> _VerificationKey:
    try:
        kid = _required_string(jwk, "kid")
        if _required_string(jwk, "kty") != _SUPPORTED_KEY_TYPES[algorithm]:
            raise TokenVerificationUnavailableError
        if jwk.get("use", "sig") != "sig":
            raise TokenVerificationUnavailableError
        key_ops = jwk.get("key_ops")
        if key_ops is not None and (
            not isinstance(key_ops, list)
            or "verify" not in key_ops
            or any(not isinstance(value, str) for value in key_ops)
        ):
            raise TokenVerificationUnavailableError
        if algorithm == "RS256":
            modulus = int.from_bytes(_decode_base64url(_required_string(jwk, "n")), "big")
            exponent = int.from_bytes(_decode_base64url(_required_string(jwk, "e")), "big")
            if not 2048 <= modulus.bit_length() <= 8192:
                raise TokenVerificationUnavailableError
            if not 3 <= exponent <= 2**31 - 1 or exponent % 2 == 0:
                raise TokenVerificationUnavailableError
        elif _required_string(jwk, "crv") != "P-256":
            raise TokenVerificationUnavailableError
        parsed_key = jwt.PyJWK.from_dict(dict(jwk), algorithm=algorithm)
    except (TokenInvalidError, jwt.PyJWTError, TypeError, ValueError) as error:
        raise TokenVerificationUnavailableError from error
    return _VerificationKey(kid=kid, algorithm=algorithm, key=parsed_key)


def _required_text(values: Mapping[str, object], name: str) -> str:
    value = values.get(name)
    if not isinstance(value, str):
        raise TokenInvalidError
    return value


def _normalized_email(values: Mapping[str, object]) -> str:
    value = _required_string(values, "email").strip().casefold()
    if len(value) > 254 or _EMAIL_PATTERN.fullmatch(value) is None:
        raise TokenInvalidError
    return value


def _required_string(values: Mapping[str, object], name: str) -> str:
    value = _required_text(values, name)
    if not value:
        raise TokenInvalidError
    return value


def _required_uuid(values: Mapping[str, object], name: str) -> UUID:
    try:
        return UUID(_required_string(values, name))
    except ValueError as error:
        raise TokenInvalidError from error


def _numeric_date(values: Mapping[str, object], name: str) -> float:
    value = values.get(name)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TokenInvalidError
    numeric = float(value)
    if not math.isfinite(numeric):
        raise TokenInvalidError
    return numeric
