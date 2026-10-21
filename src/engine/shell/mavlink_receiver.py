"""MAVLink 통신 수신 셸 어댑터 호환 브릿지 (하위 호환성 100% 보장).

단일 책임 원칙(SRP)에 따라 실제 구현부는 src.engine.shell.mavlink 서브패키지로 분리되었습니다.
기존 모든 외부 import 경로는 본 브릿지를 통해 100% 안전하게 동작합니다.
"""

from src.engine.shell.mavlink.multi_receiver import MAVLinkMultiReceiver
from src.engine.shell.mavlink.receiver import MAVLinkReceiver

__all__ = ["MAVLinkMultiReceiver", "MAVLinkReceiver"]
