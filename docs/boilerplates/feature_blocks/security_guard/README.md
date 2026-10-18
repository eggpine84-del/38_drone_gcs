# 10. Security Guard (보안 4대 물리 게이트 완제품)

> **전 도메인 범용 Zero-Trust 보안 게이트 블록**
> 외부 I/O 없는 순수 코어(`core.py`)와 FastAPI 단일 관문 미들웨어(`middleware.py`)로 구성되어, 신규 프로젝트에 30초 만에 완벽한 방어벽을 세웁니다.

---

## 1. 4대 게이트 구성
1. **Gate 1 (경계 붕괴 차단)**: SQL 인젝션, 메타문자 조작 감찰
2. **Gate 2 (신뢰 왜곡 차단)**: BOLA / IDOR 소유권 원자 대조
3. **Gate 3 (상태 교란 차단)**: 잔액 음수 차감, 잔액 부족, 동시성 조건부 검증
4. **Gate 4 (자원 고갈 차단)**: 1MB 페이로드 상한선, 최대 100건 조회 강제

---

## 2. 30초 복사-조립 가이드

### 단계 1: 프로젝트에 복사
새 프로젝트의 `src/shared/security/` 또는 `src/service/` 폴더로 이 블록을 복사합니다.

### 단계 2: FastAPI 앱에 미들웨어 등록
```python
# main.py 또는 service/shell/app.py
from fastapi import FastAPI
from src.shared.security.middleware import SecurityGateMiddleware

app = FastAPI()

# 단일 관문 미들웨어 부착
app.add_middleware(SecurityGateMiddleware)
```

### 단계 3: 핀테스트 복사 및 확인
`sample_pin_security.py`를 프로젝트의 `tests/test_pin_security_gates.py`로 복사하고 테스트를 실행합니다:
```bash
pytest tests/test_pin_security_gates.py
```
