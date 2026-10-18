# B2B 어드민 9대 레고 블록 완제품 가이드

> **FastAPI + Jinja2 + htmx + Pure Core/Shell 아키텍처**
> B2B 사내 시스템/어드민/SaaS 개발 시 필요한 9대 표준 부품을 5분 만에 복사하여 조립할 수 있는 영구 자산입니다.

## 9대 블록 목록
1. `crud_sample/`: 표준 데이터 관리 (목록/등록/노션스타일 인라인 수정/소프트 딜리트)
2. `kpi_dashboard/`: 대시보드 메인 통계 & 4대 지표 카드 (htmx 비동기 갱신)
3. `excel_io/`: CSV/엑셀 대량 업로드 & 다운로드
4. `status_workflow/`: 상태 머신 (접수->승인->완료 상태 전이 유효성 검증)
5. `audit_log/`: 감사 로그 (변경 전/후 차이점 Diff 추적 타임라인)
6. `file_storage/`: 첨부파일 보안 검증 및 UUID 디스크 격리 저장 (웹쉘 차단)
7. `webhook_receiver/`: 외부 Webhook HMAC-SHA256 서명 검증 및 멱등성 보장
8. `rate_limiter/`: 슬라이딩 윈도우 기반 API 속도 제한기 (429 차단)
9. `cron_scheduler/`: 경량 크론 스케줄러 & 중복 실행 락(Lock) 보호
10. `security_guard/`: 4대 물리 게이트(인젝션/IDOR/동시성/자원고갈) 단일 관문 미들웨어 & 순수 코어
