---
description: 작업 트리 즉시 Clean 커밋 및 스마트 싱크 베이스라인 확정
---

[즉시 로컬 커밋 명령 (/0_git_commit)]
0. [사전 점검]: .gitignore에 훅 런타임 임시 파일(.agents/.deploy_token, .agents/.baseline_hashes.json) 등록 확인 (최초 1회 필수).
1. [정리]: 이전 잔여 해시(.baseline_hashes.json) 존재 시 즉시 삭제.
2. [커밋]: 변경 파일 일괄 스테이징 후 표준 메시지로 즉시 로컬 커밋 (원격 푸시 금지).
3. [확정]: 작업 트리 Clean(스마트 싱크 가동) 확인 후 1줄 완료 보고.