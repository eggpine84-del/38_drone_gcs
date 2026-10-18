---
description: 3대 입구 30대 검문소를 단 1초 만에 전수 실전 격발하여 1장 대시보드로 완수 보고
---

[30대 훅 전수 실전 감사 파이프라인 (/4_hook_step_by_step)]
1. [3대 철칙]: 위반 즉시 차단(Exit 1/deny) | 정상 즉시 허용(Exit 0/allow) | 클린 원복(Zero-Pollution)
2. [단 1줄 기계적 실행]:
   - `python tests/run_all_30_guards_check.py` 실행 (PreTool 10개 + PostTool 1개 + StopGate 19개 전수 순회).
   - 단 1개라도 실패 시 즉시 중단(Fail-Fast).
3. [결과 보고]:
   - 터미널 실제 출력 로그 기반 30대 전수 [PASS] 1장 요약표 사장님께 제출.