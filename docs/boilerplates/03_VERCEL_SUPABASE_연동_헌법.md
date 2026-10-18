# [보일러플레이트] Vercel + Supabase 클라우드 실전 연동 헌법
# Cloud Integration Master Constitution (Zero-Crash & Zero-Lag)

> **목적**: 로컬(SQLite)에서는 잘 되다가 클라우드(Vercel + Supabase)에 올리는 순간 발생하는 7대 지뢰(네트워크 렉, 커넥션 고갈, 세션 유실, 브라우저 오염, 배포 누락)를 원천 차단하고, 신규 프로젝트에 1분 만에 복붙하여 100% 한 번에 성공시키는 실전 마스터 규격서.

---

## [7대 실전 지뢰 매트릭스 & 영구 해결책 요약]

| 번호 | 영역 | 실전 지뢰 (발생 원인) | 치명적 증상 | 헌법 강제 해결책 |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **리전 위치** | Vercel 기본 리전이 미국 워싱턴(`iad1`)으로 설정됨 | 서울 Supabase DB까지 태평양 횡단으로 **10초 렉/타임아웃** | 루트 `vercel.json`에 `"regions": ["icn1"]` (서울) 필수 탑재 |
| **2** | **풀러 포트** | Supabase 대시보드 기본 복사값인 `5432` 세션 풀러 사용 | 동시 연결이 **15개로 하드캡**되어 금방 500 에러 크래시 | IPv4 트랜잭션 풀러 **`6543` 포트** 고정 및 어댑터 코드 자동 승격 |
| **3** | **커넥션 풀링** | `pg8000.Connection` 객체에 `.execute()` 직접 호출 버그 | 매 쿼리마다 AttributeError ➔ 풀러 캐시 소멸 ➔ **단일 요청당 커넥션 5개 폭주** | `cur = conn.cursor(); cur.execute("SELECT 1;"); cur.close()` 헬스체크 |
| **4** | **서버리스 콜드스타트** | 기본 타임아웃 5초 설정 및 예외 핸들러 부재 | 람다 기동 지연 시 **`Internal Server Error` 검은 화면** 직출력 | `timeout=10` 완화 + 라우트 레벨 `try-except` Safe Fallback 가드 |
| **5** | **배포 파이프라인** | 태그만 단독 푸시 (`git push origin $new`) | `master` 브랜치가 안 올라가 **Vercel이 옛날 코드를 그대로 돌림** | `git push origin master $new` (브랜치 + 태그 동시 푸시) 필수 |
| **6** | **서버리스 세션** | 메모리 딕셔너리에만 세션 보관 (`ACTIVE_SESSIONS`) | 람다 인스턴스 전환 시 세션 유실 ➔ 갑자기 로그인 풀림 | 세션 쿠키-DB SSOT 동기화 + 비인증 요청 시 303 로그인 리다이렉트 |
| **7** | **브라우저 자동채우기** | `<input type="password">`에 크롬이 비번 강제 주입 | 대표자/관리자 비번이 다른 폼이나 사용자 관리 화면에 덮어씌워짐 | 초기 `type="text"` + `-webkit-text-security: disc;` + HTMX 라이프사이클 세척 |

---
