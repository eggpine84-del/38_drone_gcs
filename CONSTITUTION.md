# [DRONE-GCS] 다중 드론 관제 시스템 헌법 (SYSTEM CONSTITUTION)

## 1. 목적 (Purpose)
다중 AI 드론의 실시간 비행 상태(Telemetry)를 수신·검증하고, 공중 충돌 및 추락 위험을 0.001초 만에 감지하여 안전 귀환 및 통제를 보장하는 무결점 관제탑 백엔드 구축.

## 2. 4대 공리 (Axioms)
1. **신호 불변성 (Telemetry Integrity)**:
   - 배터리는 0~100% 범위를 벗어날 수 없으며, 고도(Altitude)는 음수가 될 수 없다.
   - GPS 좌표(Lat/Lon)는 지구상 실존 좌표계여야 한다.
2. **단방향 비행 상태 전이 (Strict State Transition)**:
   - IDLE(대기) -> ARMED(시동) -> TAKEOFF(이륙) -> IN_FLIGHT(비행) -> LANDING(착륙) -> TERMINATED(종결)
   - 비행 중인 드론이 대기(IDLE)로 순간이동할 수 없다.
3. **위험 격리 및 강제 안전권한 (Fail-Safe Preemption)**:
   - 배터리 15% 이하, 3초 이상 통신 두절(Heartbeat Timeout), 허용 지오펜스 이탈 시 시스템은 즉시 EMERGENCY_RTH(비상 귀환) 상태로 강제 전환한다.
4. **다중 드론 격리 및 원장 보존 (Multi-Drone Isolation & Ledger)**:
   - 모든 판정은 drone_id별로 100% 독립 격리되며 상호 오염을 불허한다.
   - 모든 텔레메트리 로그와 경보 이력은 1건도 수정/삭제될 수 없으며 영구 보존(Append-Only)된다.

## 3. 최소 데이터 스키마 (SSOT)
```json
{
  "drone_id": "DRONE-01",
  "latitude": 37.5665,
  "longitude": 126.9780,
  "altitude": 50.0,
  "speed": 12.5,
  "battery": 85,
  "status": "IN_FLIGHT",
  "timestamp": "2026-10-18T14:00:00Z"
}
```

## 4. 2대 워크플로우 시나리오
1. **단발 텔레메트리 수신 (Single Telemetry Ingest)**:
   - 드론이 1회 비행 데이터를 쏘면 0.001초 내 검증 후 원장 저장 및 상태 반환 (B1 단일 봉투).
2. **복합 관제 및 비상 프로토콜 (Complex Failsafe Sequence)**:
   - 주기적 하트비트 수신 -> 3초 이상 미수신 감지 -> 실종 경보(LOST) 발령 -> 원장 기록 -> 관제 UI 실시간 경보 전파.

## 5. 3대 금기 (Taboos)
1. 선행 상태 검증 없는 임의 비행 명령 하달 금지 (예: 시동 안 켜진 드론 이륙 명령 차단).
2. 배터리 음수값 및 GPS 좌표 누락 데이터의 비즈니스 코어 유입 영구 금지.
3. 과거 비행 기록(블랙박스 원장) 수정/삭제(UPDATE/DELETE) 전면 금지.
