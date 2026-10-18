# ⚡ Vercel + Supabase 풀스택 클라우드 구축 & 트러블슈팅 초압축 런북

> **목적**: Vercel Serverless + Supabase PostgreSQL 연동 시 발생하는 6대 핵심 이슈 및 0.2초 초고속화 솔루션을 0초 만에 재현/적용하기 위한 초압축 가이드.

---

## 1. 🌐 Vercel Serverless 배포 핵심 수칙
1. **URL 리라이트 경로 유실 방어**:
   - `vercel.json`: `"destination": "/api/index?__vercel_path=$1"`
   - `api/index.py`: `parse_qs(environ.get("QUERY_STRING"))`에서 `__vercel_path`를 추출하여 `PATH_INFO`로 복원.
2. **Read-Only FS ([Errno 30]) 방어**:
   - 서버리스 환경에서는 루트 쓰기 금지 ➔ 로그/임시 파일은 반드시 `/tmp` 경로로 폴백 및 `try-except` 격리.
3. **0.05초 초고속 서울 리전 지정**:
   - `vercel.json`: `"regions": ["icn1"]` 지정으로 태평양 횡단 네트워크 지연(250ms) 원천 차단.
4. **경량 순수 파이썬 드라이버 의존성**:
   - `requirements.txt`: `pg8000` (순수 파이썬) 채택으로 C-컴파일 에러 0% 및 빌드 0초 컷 보장.
5. **Vercel CLI 환경변수 등록 규칙**:
   - `Production`과 `Preview` 양쪽에 모두 등록 필수:
     ```bash
     "<VALUE>" | npx vercel env add <KEY> production
     "<VALUE>" | npx vercel env add <KEY> preview
     ```


---

## 2. 🐘 Supabase PostgreSQL 17 클라우드 연동 수칙
1. **특수문자 `#` URL 인코딩 및 `unquote` 디코딩 필수**:
   - 비밀번호에 `#` 등 특수문자 포함 시 `urlparse`가 해시(Fragment)로 오인하므로 `.env`에는 `%23`으로 저장.
   - 단, 파이썬 드라이버(`pg8000`)에 전달 시 `urlparse`는 자동 디코딩하지 않으므로 `unquote(parsed.password)` 필수 적용.
2. **IPv4 통신을 위한 Connection Pooler 필수 적용**:
   - Direct Host(`db.<ref>.supabase.co:5432`)는 IPv6 전용으로 국내 대다수 ISP 및 로컬 개발환경에서 타임아웃 발생.
   - 반드시 Supabase Pooler 호스트(`aws-1-<region>.pooler.supabase.com:5432` Session 모드 또는 `6543` Transaction 모드)를 사용.
3. **PostgreSQL 호환 DDL 및 메타데이터 자동 변환**:
   - `INTEGER PRIMARY KEY AUTOINCREMENT` ➔ `SERIAL PRIMARY KEY` 치환 (PK 자동 증가 보장).
   - `PRAGMA table_info(tbl)` ➔ `information_schema.columns` 쿼리 변환.
   - `PostgresProxyCursor`에 `rowcount`, `lastrowid` 프로퍼티 및 안전한 `fetchall()` 가드 구현.
4. **SQL 파라미터 바인딩 (`?` ➔ `%s`) 자동 호환**:
   - DB 어댑터에서 플레이스홀더를 `%s`로 자동 치환하여 SQLite/Postgres 쿼리 100% 공용화.
5. **날짜(datetime) 객체 JSON 직렬화 안전성 (`default=str`)**:
   - Supabase 날짜 객체 반환에 대비해 모든 `json.dumps(..., default=str)` 옵션 의무화.

---

## 3. 🚀 Zero-Lag 초고속화 (16초 ➔ 0.2초 80배 가속 솔루션)
1. **DB 커넥션 재사용 풀링 (Keep-Alive)**:
   - 매 쿼리마다 TCP Handshake/SSL 반복 금지. 글로벌 커넥션 캐시(`_GLOBAL_PG_CONN`) 및 `close()` no-op 처리.
2. **DDL 1회 멱등 캐싱 (`_INITIALIZED_DBS`)**:
   - `fetch_...` 조회마다 `CREATE TABLE`, `PRAGMA table_info` 반복 전송 금지.
   - `_INITIALIZED_DBS: set = set()` 가드로 최초 1회만 스키마 확인 후 이후 조회는 0ms 패스.
3. **외부 API 비동기/병렬화**:
   - 구글 트렌드/뉴스 RSS 수집 시 `concurrent.futures.ThreadPoolExecutor` 동시 실행 + 0.8초 타임아웃 강제.
4. **워크스페이스/테넌트 스위칭**:
   - 상단 드롭다운 변경 시 `window.location.href = targetValue;` 정규 이동으로 전체 컨텍스트 0.05초 즉시 교체.

---

## 4. 🛡️ 보안, 세션 & 아키텍처 규칙
1. **서버리스 무상태(Stateless) HMAC 세션 토큰**:
   - Vercel 서버리스 인스턴스가 3분마다 재생성되어도 세션이 풀리지 않도록 HMAC-SHA256 서명 쿠키 발급 및 검증.
   - 쿠키 `Max-Age`를 생략하여 브라우저 종료 시 즉시 파기되는 금융권 보안 유지.
2. **사이드이펙트 방지 (Table-Driven & Early Return)**:
   - 로그아웃(`/logout`) 및 헬스체크는 테넌트 가드레일보다 무조건 최상단 1순위 Early Return 처리.
   - 3개 이상 분기 발생 시 `if-elif` 금지, 무순서 Dict 매핑(`Table-Driven Dispatch`) 의무화.
3. **3선 가드레일 (BOLA 차단)**:
   - 일반 사용자의 `?tenant=`, `?ws=ws_personal_01` 변조 시 세션 소속 테넌트로 강제 튕김.
4. **환경변수 단일 진실 공급원 (`config/.env`)**:
   - `.env.local` 등 파편화 금지. `config/.env` 하나로 모든 Vercel/Supabase 토큰 통합 관리.
5. **모듈 분리 한도 및 회귀 테스트**:
   - 단일 파일 300줄 초과 감지 시 즉시 SRP 서브 모듈 분리.
   - 배포 전 `pytest` 131개 E2E 시나리오 전수 검증 통과 후 `git push` & `vercel --prod`.

---

## 5. 🛠️ 실전 트러블슈팅 케이스 아카이브

### [Case 1] Vercel 재배포 시 데이터 리셋 (기본 할일/원생 복구)
- **원인**: Direct Host(IPv6) 타임아웃으로 Vercel 임시 디스크(`/tmp`) 폴백 작동 ➔ 재배포 시 `/tmp` 초기화로 기본 시딩 재생성.
- **해결 (3대 조치)**:
  1. **IPv4 Pooler URL**: `aws-1-<region>.pooler.supabase.com:5432`로 갱신 (`SUPABASE_DB_URL`).
  2. **특수문자 디코딩**: URL의 `%23`(`#`)을 `unquote(parsed.password)`로 디코딩 전달.
  3. **DDL 호환**: `AUTOINCREMENT` ➔ `SERIAL PRIMARY KEY`, `PRAGMA table_info` ➔ `information_schema.columns` 자동 치환.

### [Case 2] 화면 전환 및 DB 조회 시 1~2초 지연 (해외 네트워크 지연)
- **원인**: Vercel 기본 리전(미국 `iad1`)에서 서울 Supabase DB로 쿼리 시 태평양 왕복(250ms x N회) 지연 발생.
- **해결**: `vercel.json`에 `"regions": ["icn1"]` (서울/인천) 지정 ➔ 동일 리전 로컬 통신(5ms 미만, 50배 가속)으로 0.1초 즉각 전환.

### [Case 3] 강사 프로필 변경 시 원장님 로그인 거부 및 메뉴 노출 장애
- **현상**: 강사가 프로필 수정 시 원장님 DB가 오염되어 원장 로그인 튕김 및 강사 메뉴 전체 노출.
- **원인**: 프로필 저장 및 세션 복원 시 강사/원장 분기 누락 + DB 트랜잭션 `commit()` 누락.
- **해결**: 강사(`teachers`)와 원장(`tenant_settings`) 저장 경로/세션 100% 분리 격리 및 `commit()` 적용 완료.

### [Case 4] 워크스페이스(마스터/개인/학원) 전환 시 프로필 이름 오염
- **현상**: 드롭다운 전환 시 이름이 학원 원장명으로 고정되거나 하드코딩 명칭 노출.
- **원인**: 클라우드 DB 동기화 코드가 `is_personal_mode` 플래그를 무시하고 세션 이름을 일괄 덮어씀.
- **해결**: `server_session_helper.py`에서 마스터(`system.ini`), 개인(`personal/config.ini`), 학원(`tenant_settings`)을 각각 1:1 동적 로드하도록 분기 격리.

### [Case 5] SPA 이동 및 헤더 DOM 동기화 레이스 컨디션 (Double Injection)
- **현상**: SPA 네비게이션 시 상단 프로필 알약과 드롭바(#wsSelector)가 서로 엇갈리거나 이전 상태로 고정되는 현상.
- **원인**: `header.header`를 통째로 교체한 후 이미 교체된 드롭바의 `innerHTML`을 가상 DOM에서 중복 덮어쓰며 DOM 참조 충돌 발생.
- **해결**: `ui_js_spa.py`에서 헤더를 단일 원자적(Atomic)으로 1회 갱신하고 내부 `option[selected]` 값만 안전 보정하도록 정리.

### [Case 6] 브라우저 뒤로가기(popstate/pageshow) 및 멀티테넌트 컨텍스트 동기화
- **현상**: 뒤로가기 시 URL은 돌아갔으나 드롭다운과 우측 프로필 이름(마스터/양준/원장)이 이전 상태로 굳는 현상.
- **원인**: 브라우저 폼 복원(BFCache)으로 `<select>` 값 강제 유지 + 백엔드에서 쿠키와 URL 파라미터 간 우선순위 충돌.
- **해결**:
  1. `<select id="wsSelector">`에 `autocomplete="off"` 부여하여 브라우저 자동 폼 캐시 무효화.
  2. `server_http_helper.py`에서 URL 쿼리 파라미터(`ws`, `tenant`)를 1순위 최우선으로 채택하는 '단일 진실 공급원(Single Source of Truth)' 확립.
  3. `popstate` 및 `pageshow` 이벤트에 `syncWsSelectorByUrl`을 연동하여 100% 멱등적 동기화.

### [Case 7] Supabase 날짜(datetime) 객체 JSON 직렬화 500 에러
- **현상**: 프라이빗 메모 등 Supabase 데이터 조회 화면 진입 시 `Object of type datetime is not JSON serializable` 500 에러 발생.
- **원인**: Supabase(PostgreSQL)는 날짜를 `datetime` 객체로 반환하는데 `json.dumps()`가 자동 변환하지 못함.
- **해결**: 모든 `json.dumps(..., default=str)` 옵션을 장착하여 날짜 객체를 자동으로 안전하게 문자열 직렬화.

### [Case 8] SPA 비동기 이동 시 메모 목록 빈 상자 노출
- **현상**: 사이드바 메뉴(SPA)로 메모장 진입 시 카운트는 뜨나 메모 목록 상자가 빈 채로 노출.
- **원인**: 초기 HTML을 빈 상자로 두고 JS 렌더링에만 의존하여 SPA DOM 교체 시 실행 타이밍 누락.
- **해결**: 파이썬 서버에서 메모 목록 버튼 HTML을 사전에 직접 생성하여 주입하는 서버 사전 렌더링(Server Pre-rendering) 장착.

### [Case 9] 홈 위젯 전체보기(Full Reload) 시 상단 드롭바 튕김 현상
- **원인**: 전체 새로고침 시 브라우저 파서가 `render_personal_layout` 1번 줄인 마스터 `<option>`을 기본값으로 덥석 무는 고질병.
- **해결**: 템플릿 1번 줄을 `[개인]`으로 재배치(`ui_templates.py`) + 위젯 링크 SPA 이동(`navigateTo`) 바인딩.

### [Case 10] 홈 위젯 프라이빗 최신 메모 이어쓰기 시 롤백 및 타이핑 유실
- **원인**: `note_id` 미바인딩으로 엉뚱한 레코드 덮어쓰기 + 단순 락(`isQuickMemoSaving`)의 타이핑 유실 비동기 결함.
- **해결**: `<input type="hidden" id="currentHomeMemoId">` In-place 바인딩 + 노션식 비동기 직렬화 대기열(`Trailing Queue`) 장착.

### [Case 11] 개인 작업실 커맨드 센터(Ctrl+K) 내 학원 원생 등록 노출 버그
- **원인**: `build_search_catalog` 퀵 액션 생성 시 `is_personal_mode` 분기 누락으로 `else(학원 기본값)` 타면서 원생 등록 노출.
- **해결**: 워크스페이스 타입별 `is_personal_mode` 플래그 주입 + 개인 전용 액션(`+ 새 메모`, `+ 새 일정`) 1:1 격리 장착.


