# B2B 어드민 만능 CRUD 표준 보일러플레이트 가이드

> **FastAPI + Jinja2 + htmx + Pure Core/Shell 아키텍처 기반**
> 새 회사 납품이나 새 메뉴 추가 시 이 폴더의 코드를 복사해서 5분 만에 CRUD를 완성할 수 있는 영구 표준 자산입니다.

---

## 1. 파일 구성도
- `crud_core.py`: I/O가 전혀 없는 순수 검증 및 비즈니스 연산 (Pure Core)
- `crud_routes.py`: FastAPI APIRouter 엔드포인트 및 htmx 부분 렌더링 응답 (Shell)
- `crud_view.html`: htmx 인라인 수정, 신규 등록 폼, 토스트 알림이 일체화된 UI 템플릿
- `test_pin_crud_sample.py`: 0.01초 만에 Core와 라우트 전체를 100% 검증하는 핀테스트

---

## 2. 핵심 동작 원리 (현대 하이엔드 htmx 패턴)
1. **목록 조회**: 
   - `<tbody>`가 최초 로드 시 `hx-get="/sample-items"`로 행(`<tr>`) 조각들을 요청하여 끼워 넣습니다.
2. **신규 등록**: 
   - 폼에서 `hx-post="/sample-items"` 호출 시 새 `<tr>`을 테이블 맨 아래(`beforeend`)에 붙이고 폼을 자동 초기화(`reset()`)합니다.
3. **인라인 편집 (No Modal)**: 
   - 행의 [수정] 버튼 클릭 시 `hx-get="/sample-items/{id}/edit"`이 호출되어 해당 행(`<tr>`) 자체가 즉시 `<input>` 수정 폼으로 바뀝니다.
   - [저장] 누르면 `hx-put`으로 갱신된 읽기 전용 행으로 복귀, [취소] 누르면 원래 상태로 복구됩니다.
4. **원장 보호 (Soft Delete)**: 
   - [삭제] 버튼 클릭 시 확인창(`hx-confirm`) 후 `hx-delete`를 호출하여 DB에서 물리 삭제하지 않고 `is_deleted=True`로 보존하며 화면에서만 즉시 사라집니다.
5. **글로벌 토스트 (OOB Swap)**: 
   - 등록/수정/삭제 시 응답 HTML 안에 `<div id="toast" hx-swap-oob="true">`가 포함되어 있어, 화면 어디서 요청하든 우측 상단 토스트 메시지가 자동으로 갱신됩니다.

---

## 3. 새 프로젝트/메뉴에 복붙해서 쓰는 3단계
1. `crud_core.py`의 필드명(예: `name`, `category` ➔ `user_name`, `email` 등)을 원하는 도메인에 맞게 변경합니다.
2. `crud_routes.py`의 `SAMPLE_DB`를 실제 프로젝트의 DB Repository 호출로 교체합니다.
3. 메인 앱 `main.py`에 라우터를 등록합니다:
   ```python
   from docs.boilerplates.feature_blocks.crud_sample.crud_routes import router as sample_router
   app.include_router(sample_router)
   ```
