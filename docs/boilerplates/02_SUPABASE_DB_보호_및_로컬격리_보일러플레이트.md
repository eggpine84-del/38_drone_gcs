# [체크리스트] Supabase DB 보호 & 로컬 격리 보일러플레이트
# Supabase Dual-Shield Master Checklist (One-Touch)

> **원칙**: 서술식 설명 배제. 신규 프로젝트 시 아래 9개 항목만 위에서 아래로 순서대로 체크하면 완벽한 DB 보호 체계가 가동됩니다.

---

### [Phase 1. 환경변수 물리 격리 (로컬 vs 클라우드)]

- [ ] **1. 로컬 .env 주석 처리**
  - 파일: `config/.env`
  - 내용: `# DATABASE_URL="postgresql://..."` (앞에 `# ` 처리 필수)
  - 검증: 로컬 실행(`python main.py`) 시 원격 슈파베 접속 0건 차단 및 로컬 SQLite 강제.

- [ ] **2. Vercel 클라우드 영구 등록**
  - 위치: Vercel 대시보드 ➔ `Settings` ➔ `Environment Variables`
  - 내용: `DATABASE_URL`에 슈파베 6543 풀러 주소 등록
  - 검증: 오직 인터넷 상용 배포 서버만 슈파베에 접속.

---

### [Phase 2. 금고-지갑 물리 분리 (DDL vs CRUD)]

- [ ] **3. 금고(스키마 DDL) 전담 파일 생성**
  - 파일: `src/shared/shell/db_schema.py`
  - 내용: `init_db()` 함수 및 모든 `CREATE TABLE IF NOT EXISTS`, 초기 시드 생성 로직 배치.

- [ ] **4. 지갑(일상 CRUD) 파사드 연결**
  - 파일: `src/shared/shell/db_adapter.py`
  - 내용: 상단에 `from .db_schema import init_db` 선언.
  - 검증: 기존 호출부(`main.py`, 각종 테스트) 0줄 수정 및 100% 하위 호환.

---

### [Phase 3. 중앙 방탄 훅 안전핀 (.agents/guard_config.json)]

- [ ] **5. 파괴적 터미널 명령어 차단**
  - 항목: `"blocked_commands"`
  - 추가: `"supabase db reset"`, `"rm -rf data/db"`, `"del data\\db"`
  - 효과: 실수로 터미널에서 DB 전체를 밀어버리는 명령 즉시 0.001초 차단.

- [ ] **6. 스키마 파일 해시 철통 잠금**
  - 항목: `"refactor_immutable_dirs"` 및 `"fix_immutable_dirs"`
  - 추가: `"src/shared/shell/db_schema.py"`
  - 효과: `feat`/`change` 모드에선 스키마 추가 허용, `refactor`/`fix` 모드에선 스키마 변조 0초 차단.

- [ ] **7. UI 마크업 훅 오탐 차단**
  - 항목: `"diff_guard_policy"` ➔ `"protected_key_patterns"`
  - 제외: `"title"`, `"label"`, `"icon"` 제외 확인 (`id`, `key`, `name`, `code` 등 핵심만 유지).
  - 효과: HTML 화면 수정/삭제 시 억울한 훅 차단 원천 박멸.

---

### [Phase 4. 듀얼 어댑터 스위칭 엔진 (db_adapter.py)]

- [ ] **8. 테스트 샌드박스 강제 격리**
  - 조건: `os.getenv("SMTRADE_ENV") == "test" or "pytest" in sys.modules`
  - 동작: 테스트 시 무조건 임시 메모리(`:memory:`)로 강제 우회하여 운영 DB 보호.

- [ ] **9. 로컬 SQLite 3대 헌법 탑재**
  - `conn.execute("PRAGMA foreign_keys = ON;")`
  - `conn.execute("PRAGMA journal_mode = WAL;")`
  - `conn.execute("PRAGMA busy_timeout = 5000;")`
