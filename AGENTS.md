# ANTIGRAVITY AUTOMATIC EXECUTION RULES

  

사용자의 '승인' 전까지는 아래 철칙을 단 한 항목도 생략 없이 100% 강제 적용한다:

0. **[Arch-Guard (직언 의무)]**: 
   - 예스맨 코딩 절대 금지 (임시 땜질·상태충돌·권한혼선 선제 비판).
   - 1목적 1도구, 5대 검증(신원불변/영향격리/멱등성/자원정리) 및 단일관문(Fail-Fast·기본값폴백금지) 준수.
   - [기획의도 vs 기술대가] 및 A/B 대안 선제안 후 승인 시만 구현.

1. **[0.CONTROL (수정/출력 통제)]**:
   - [No-Emoji & Clean-SVG]: 소스/DB/로그/CLI 이모지 절대 금지 | 순수 인라인 SVG(단색 1em, 액션/네비당 최대 1개) 절제 적용.
   - [Pre-Report & Pinpoint]: 수정 전 [위치, 전/후, 사유] 보고 필수 | `write_to_file` 영구 금지, 오직 `replace_file_content`로 지정 라인만 핀포인트 수정.
   - [Zero Deletion]: 기존 조건문/예외/로그 임의 삭제·변형 절대 금지.
   - [Template Immutability]: templates/ 폴더 내 파일(01~09)은 범용 영구 양식이므로 파일 자체 수정/작성 절대 금지 (모든 기획서·보고서는 서식 100% 채워 오직 '채팅창'에 직접 출력).
   - [스택 철칙]: 5대 공인스택(FastAPI/Jinja2/HTMX/Tailwind/Go) 외 타 스택·JS파일 영구 금지 (예외 도입 시 기획서 사전 승인 필수).


2. **[BASE RULES (코딩 표준)]**:
   - [T0]: Guard Clause | Table-Driven Dispatch (3개 이상 분기 시 if-elif 금지, 무순서 Dict 매핑 필수) | Const Only | SRP (300줄 초과 시 억지압축 금지, 서브모듈 분리).
   - [T1~T2]: 입력 불신 | 타입·로깅 필수 | 3대분리(로직/문지기가드/핀테스트) & Core-Shell 격리 | 상태변경 100% DB 전담.

3. **[Pipeline & Approval Gate]**:
   `templates/README.md` 열람(`view_file`) 필수 및 답변 첫 줄 체크인 영수증 의무 출력:
   `[체크인]: [유형: feat|change|fix|refactor] | [도메인: DB|API|UI|Engine] ➔ 템플릿[XX] 열람완료 | 가드: [핵심 1줄]`
   - 현재 파이프라인 단계(S1~S8) 준수 및 단계별 필수 요건(S1 4대요소, S2 하드코딩금지, S3 Core/Shell격리, S4 브라우저/T1검증)  완수 후 사장님 승인 시만 다음 단계 진입.
   - [Rails-Playbook 바인딩]: API/웹 기능 구현(09 백본) 시 `docs/boilerplates/RAILS_FEATURE_PLAYBOOK.md`를 자동 대조하여 비동기/인증/알림/파일/감사 5대 실무 패턴을 기본 적용.

4. **[Pin-Test First]**:
   - 기능 구현 전 핀테스트 선작성(Red 필수) ➔ 구현 통과(Green).
   - 기존 테스트 임의 변형/삭제/약화 절대 금지 | 리팩토링 시 1:1 Zero-Mutation 증빙.
   - [Full-Assertion]: 텍스트(in file)·부분(res.x==1) 단언 금지 | 실제 런타임 호출 반환값 전체 객체 통째 대조(res==expected) 필수.

5. **[.agents/ 격리 (안전핀)]**:
   - `.agents/` 폴더 내 파일(워크플로우/훅/룰)은 일반 개발 작업 시 임의 수정 절대 금지 (훅 런타임 CWD=.agents).


