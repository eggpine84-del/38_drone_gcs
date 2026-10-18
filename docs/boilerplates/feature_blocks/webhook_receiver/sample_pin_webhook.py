"""
[Pin-Test First] 7_webhook_receiver 핀테스트 선작성
"""
import hmac
import hashlib
import pytest
from docs.boilerplates.feature_blocks.webhook_receiver.core import verify_webhook_signature, process_idempotent_event


def test_verify_webhook_signature_success():
    """정상 HMAC 서명 검증은 성공해야 한다."""
    secret = "test_webhook_secret_key_12345"
    payload = b'{"event":"payment_success","amount":50000}'
    valid_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    res = verify_webhook_signature(payload_bytes=payload, signature_header=valid_sig, secret_key=secret)
    assert res["success"] is True
    assert res["data"]["verified"] is True


def test_verify_webhook_signature_tampered_payload():
    """페이로드가 1바이트라도 위조되면 서명 검증이 즉시 실패해야 한다."""
    secret = "test_webhook_secret_key_12345"
    payload = b'{"event":"payment_success","amount":50000}'
    tampered = b'{"event":"payment_success","amount":10000}'
    valid_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    res = verify_webhook_signature(payload_bytes=tampered, signature_header=valid_sig, secret_key=secret)
    assert res["success"] is False
    assert res["error"] == "ERR_INVALID_SIGNATURE"


def test_process_idempotent_event_duplicate_blocked():
    """동일한 멱등키(이벤트 ID)가 재수신되면 중복 거부되어야 한다."""
    processed_keys = {"evt_1001", "evt_1002"}
    res = process_idempotent_event(event_id="evt_1001", processed_ids=processed_keys)
    assert res["success"] is False
    assert res["error"] == "ERR_DUPLICATE_EVENT"
