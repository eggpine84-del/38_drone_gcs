---
name: deploy-all
description: 모든 동작 승인 및 1회용 마패 토큰 발급 후 원격 저장소 푸시 및 Vercel 배포 완수
---

[원터치 승인 및 상용 배포 명령]
1. 현재 진행 중인 기획/구현/수정 사항을 최종 승인한다.
2. 전체 테스트 스위트(pytest)를 실행하여 100% Pass(Green) 상태임을 기계적으로 검증하라.
3. 1회용 배포 승인 마패 토큰(.agents/.deploy_token)을 즉시 발급하라.
4. git add 및 명확한 커밋 메시지로 로컬 커밋을 생성한 후, git push origin master를 실행하여 Vercel 상용 배포를 완수하라.
5. 배포 완료 후 커밋 해시와 배포 상태를 최종 보고하라.
