# 레일즈급 웹 기능 AI 맞춤 적응형 플레이북 (Rails-Style Feature Playbook)

> **원칙 (Zero Technical Debt)**:
> 1. **정적 복붙 금지**: 고정된 하드코딩 샘플을 복사하지 않고, 각 프로젝트의 실제 환경(DB 종류, 변수명, 비즈니스 룰)에 맞추어 AI가 최적의 코드를 동적 생성합니다.
> 2. **FCIS 헌법 100% 준수**: 모든 기능은 `Core`(순수 연산/상태 판정)와 `Shell`(I/O, DB, 네트워크, 라우터)로 철저히 분리합니다.
> 3. **경량성 최우선**: Redis, Celery 등 무거운 외부 의존성을 남발하지 않고, 파이썬 표준 라이브러리와 FastAPI 기본 기능으로 해결합니다.

---

## 8대 핵심 기능 AI 맞춤 처방 매트릭스

| 번호 | 레일즈(Rails) 기능 | 핵심 목적 | 우리 스택 맞춤 해결책 (FastAPI + HTMX) |
| :--- | :--- | :--- | :--- |
| **01** | **Rails Scaffold** | 한 줄로 CRUD 전체 생성 | `feature_blocks/crud_sample` 패턴 (인라인 HTMX 수정 + Soft Delete) |
| **02** | **Active Record** | 샌드박스 트랜잭션 & 관계 | `db_adapter.py` 단일 컨텍스트 매니저 (`with db_transaction():`) |
| **03** | **Hotwire (Turbo)** | 새로고침 없는 부분 HTML 교체 | HTMX `hx-target` + OOB Swap (`hx-swap-oob="true"`) |
| **04** | **Active Job** | 응답 지연 없는 백그라운드 큐 | `FastAPI BackgroundTasks` (경량) 또는 SQLite 작업 큐 테이블 |
| **05** | **Action Mailer / Notifier**| 템플릿 기반 비동기 알림 발송 | Jinja2 HTML 템플릿 렌더링 + 비동기 웹훅/이메일 어댑터 |
| **06** | **Devise (Auth/RBAC)** | 세션 쿠키 및 역할별 접근 제어 | Stateless HMAC 서명 세션 쿠키 + FastAPI Dependency 권한 가드 |
| **07** | **Active Storage** | 파일/이미지 업로드 및 보안 검증 | 스트리밍 청크 저장 + 매직바이트 MIME 검증 + UUID 격리 |
| **08** | **Paper Trail (Audit)** | 누가/언제/무엇을 바꿨는지 추적 | `feature_blocks/audit_log` 패턴 (이전/이후 객체 JSON Diff 추적) |

---

## [세부 구현 가이드 및 AI 지시 공식]

### 1. Active Job (백그라운드 비동기 처리)
- **문제 의식**: 대용량 엑셀 처리, 알림 발송 시 사용자가 브라우저 모래시계를 보며 기다리지 않아야 함.
- **기술 부채 방지 처방**:
  - Redis/Celery 도입 금지 (서버 비용 및 인프라 복잡도 폭증 차단).
  - 1차: FastAPI 내장 `BackgroundTasks` 활용 (단순 메일, 로그, 가벼운 알림).
  - 2차(재시도/영속 필요 시): SQLite DB에 `job_queue` 테이블(id, payload, status, retry_count) 생성 후 스케줄러가 순차 처리.
- **AI 지시 공식**:
  > *"이 프로젝트의 [도메인명]에 백그라운드 작업을 적용해줘. 레일즈 플레이북 01번 규격에 따라 외부 큐 서버 없이 FastAPI BackgroundTasks(또는 경량 DB 큐)로 사용자 응답을 즉시 반환하고 백그라운드에서 처리해라."*

---

### 2. Action Mailer / Notifier (알림 템플릿 발송기)
- **문제 의식**: 코드 안에 이메일/슬랙 본문 문자열을 지저분하게 하드코딩하지 않아야 함.
- **기술 부채 방지 처방**:
  - `templates/emails/*.html` 또는 `templates/messages/*.txt`로 분리.
  - Jinja2 템플릿 엔진으로 변수를 주입하여 본문을 생성(Pure Core).
  - 실제 발송(SMTP, Slack Webhook, 카카오 알림톡)은 Shell의 단일 어댑터가 전담.
- **AI 지시 공식**:
  > *"레일즈 플레이북 02번에 맞춰 [알림 목적] 알림 발송기를 만들어줘. Jinja2 템플릿으로 본문을 굽고, 비동기 Shell 어댑터로 [슬랙/이메일]을 발송하는 FCIS 구조로 짜라."*

---

### 3. Devise (인증 및 역할 기반 권한 제어 - RBAC)
- **문제 의식**: 매 라우트마다 "if user.role != 'ADMIN'" 검사를 복사/붙여넣기 하다가 보안 구멍이 뚫림.
- **기술 부채 방지 처방**:
  - DB 세션 조회 없이 검증 가능한 Stateless HMAC 서명 쿠키 사용 (`itsdangerous` 또는 `PyJWT`).
  - FastAPI의 `Depends`를 활용하여 단 1줄로 권한 문지기 가드 적용:
    - `@router.get("/admin", dependencies=[Depends(require_role("ADMIN"))])`
- **AI 지시 공식**:
  > *"레일즈 플레이북 03번 규격에 맞춰 현재 [도메인명]에 RBAC 권한 가드를 적용해줘. FastAPI Depends와 단일 관문 데코레이터 패턴으로 권한 부족 시 403을 반환해라."*

---

### 4. Active Storage (파일 및 이미지 업로드 안전망)
- **문제 의식**: 사용자가 악성 웹쉘(.php, .py)이나 100MB 거대 파일을 올려 서버를 터뜨리는 것 방어.
- **기술 부채 방지 처방**:
  - 확장자 단순 검사 금지 ➔ 파일 헤더(매직 바이트)로 실제 MIME 타입 검증.
  - 원본 파일명 그대로 저장 금지 ➔ UUID 파일명으로 난수화하여 디스크 저장 (Path Traversal `../` 영구 차단).
  - 파일 저장은 스트리밍 청크(`shutil.copyfileobj`)로 처리하여 메모리 폭증 방지.
- **AI 지시 공식**:
  > *"레일즈 플레이북 04번에 맞춰 [파일 업로드 용도] 핸들러를 구현해줘. 확장자 및 파일 헤더 살균, UUID 파일명 저장, 파일 크기 제한(10MB)을 포함하는 Shell 어댑터로 작성해라."*

---

### 5. Paper Trail (감사 로그 및 변경 이력 추적)
- **문제 의식**: 중요한 데이터(직급, 가격, 권한, 주문 상태)가 수정되었을 때 "누가 이전 값을 뭐로 바꿨는지" 증적이 남아야 함.
- **기술 부채 방지 처방**:
  - 모든 테이블에 컬럼을 추가하지 않고, 독립된 `audit_logs` 단일 테이블 활용.
  - 수정 전(dict)과 수정 후(dict)를 비교하여 변경된 키만 추출하는 순수 함수(`extract_audit_diff`)를 거쳐 JSON으로 기록.
- **AI 지시 공식**:
  > *"레일즈 플레이북 05번에 맞춰 [테이블명] 데이터 변경 시 감사 로그(Audit Log)를 남겨줘. 변경 전/후의 Diff를 순수 Core로 추출하여 audit_logs 테이블에 적재해라."*

---

## [사용 방법 요약]
1. 새로운 프로젝트를 시작하거나 새 기능이 필요할 때, 이 문서를 열고 필요한 항목 번호를 확인합니다.
2. AI에게 **[AI 지시 공식]**을 복사해서 붙여넣습니다.
3. AI는 기존 레거시나 무거운 라이브러리 없이, **현재 프로젝트의 맥락에 100% 최적화된 맞춤형 코드**를 FCIS 원칙에 맞게 생성합니다.
