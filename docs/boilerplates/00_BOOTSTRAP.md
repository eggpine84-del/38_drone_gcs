# [BOOTSTRAP.md] 신규 프로젝트 원터치 자동 부팅 매뉴얼
> **철칙**: 비즈니스 구현 코드 작성 금지 | 체크리스트 완수 후 즉시 정지(STOP).

---

### [Phase 0. 엔트리포인트 & 대칭 폴더 뼈대 점검]
- [ ] 1. 루트 `main.py` 부재 시 `docs/boilerplates/main.py` 배치 (존재 시 스킵)
- [ ] 2. Three-Tier 폴더 구조 점검 및 생성 (부재 시 생성):
  - 척추 엔진(Engine): `src/engine/{core,shell}`, `tests/{test_core,test_shell}`
  - 수직 피처(Features): `src/features/{name}/{core,shell,templates}`, `tests/test_features/{name}`
  - 정적 자산(Static): `static/{images,audio}` (루트 직속 정적 자산)
  - 순수 공유함(Shared): `src/shared/` (기본 생성 금지 | 3개 피처 중복 시만 생성)

---

### [Phase 1. 아키텍처 핀-테스트 & 전역 샌드박스 배치]
- [ ] 3. `docs/boilerplates/test_architecture.py`를 `tests/test_shell/test_architecture.py`로 배치 (존재 시 스킵)
  - **헌법**: 시스템 척추(`src/engine`)와 테스트(`tests/test_core`, `tests/test_shell`) 1:1 대칭 분리 및 Zero File Assert 7대 가드 준수
- [ ] 3-1. **[필수 방탄 세트: DB 격리 샌드박스 & 스키마 금고]**
  - `docs/boilerplates/conftest.py` ➔ `tests/conftest.py` 배치 (가상 디스크 샌드박스 자동 주입)
  - `docs/boilerplates/db_adapter.py` ➔ `src/engine/shell/db_adapter.py` 배치 (SQLite 3대 헌법 & 순수 커넥션 배관)
  - `docs/boilerplates/db_schema.py` ➔ `src/engine/shell/db_schema.py` 배치 (테이블 DDL & 초기 시드 금고)
- [ ] 3-2. **[Vercel 클라우드 배포 헌법: 서울 리전 고정]**
  - Vercel 배포 시 `docs/boilerplates/vercel.json` ➔ 루트 `vercel.json` 배치 (미국 워싱턴 태평양 왕복 렉 100% 방어용 `"regions": ["icn1"]` 필수 탑재)
- [ ] 3-3. **[웹 UI 4대 스택 헌법 가드]**
  - `docs/boilerplates/test_ui_markup_guard.py` ➔ `tests/test_shell/test_ui_markup_guard.py` 배치 (JS 0줄 & Tailwind/HTMX 엔진)
  - `docs/boilerplates/test_ui_contract_guard.py` ➔ `tests/test_shell/test_ui_contract_guard.py` 배치 (HTML 하드코딩 금지 & 200 조각 계약)
- [ ] 3-4. **[피처 격리 헌법 가드]**
  - `docs/boilerplates/test_feature_guard.py` ➔ `tests/test_shell/test_feature_guard.py` 배치 (피처 수평 import 금지 기계적 검증)
- [ ] 3-5. **[대문 입력 규격(DTO) 및 3대 핀테스트 가드]**
  - `docs/boilerplates/test_input_contract_guard.py` ➔ `tests/test_shell/test_input_contract_guard.py` 배치 (날것의 dict 금지, extra='forbid' 및 3대 핀테스트 기계적 강제)

---

### [Phase 2. 시스템 무결성 점검 & 러너 실행]
- [ ] 4. 4대 에셋 자가 점검: `.agents/`, `templates/`, `docs/`, `AGENTS.md`
- [ ] 5. `pytest -q` 실행 ➔ 정예 7대 아키텍처 가드 100% Pass(Green) 확인

---

### [Phase 3. 부팅 완료 보고 및 대기 (STOP)]
- [ ] 6. "프로젝트 부팅 및 정예 7대 아키텍처 가드 안전망 가동 완료" 1줄 보고 후 **즉시 대기(STOP)**

