# [02 Frontend & UI-UX Standard Policy: Modern Component-Kit]

## 0. 절대 헌법 (Hardening & Zero-Crash)
- [No-Emoji & Clean-UI]: 소스/UI/로그 내 이모지 절대 금지 | Tailwind 공식 CDN 기본 장착 (외부 무단 폰트/스크립트 금지) | 1em 단색 인라인 SVG(액션당 최대 1개) | 시스템 폰트 고정
- [Zero-Clipping & Zero-Jank]: 픽셀 땜질 금지 | 8px 그리드(4, 8, 12, 16, 24px) | 4대 상태(Normal ➔ Hover 명도변화 ➔ Active scale(0.98) ➔ Disabled)
- [Zero-Pixel-Tug]: 임의 인라인 픽셀 조작 엄금, 오직 [A원단 토큰 + B완제품 블록] 조합만 허용

## 1. A계열 4대 기초 원소 (Atoms & Theme Tokens)
- [A-1 Color]: 매트 블랙(#090d16), 슬레이트(#0f172a), Green(#2ea043), Amber(#d29922), Red(#f85149) (대비비 4.5:1 이상)
- [A-2 Typography]: 전광판(1.08rem Bold), 지침(0.92rem), 본문(0.86rem), 라벨(0.76rem) (찌그러짐 방지 절대 비례)
- [A-3 Radius/Space]: 컨테이너(12~14px), 카드/인풋(8px), 뱃지(9999px) | 8-Point Grid 시스템
- [A-4 Icon]: 무CDN 순수 1em SVG (`stroke:currentColor; stroke-width:2; fill:none;`)

## 2. B계열 8대 완제품 블록 규격 (Blocks)
- [B-1 Container]: 모바일/PC 높이 자동감지 무짤림 쉘 (`min-h-[100dvh] pb-24 pb-[calc(6rem+env(safe-area-inset-bottom))] w-full max-w-full overflow-x-hidden`)
- [B-2 Header]: 모바일 1줄 고정 상단바 (`h-14 px-4 flex items-center justify-between whitespace-nowrap`, 모바일 텍스트버튼 금지➔1em SVG 아이콘버튼 축소, 프로필/직책 압축 표기)
- [B-3 Form/Input]: T1 유효성 검증 인풋 (`text-base md:text-sm` 모바일 자동줌 차단) | [B-4 Button]: 햅틱/로딩 스피너 내장 액션 버튼
- [B-5 Result Card]: 1px 보더 다크 서피스 대시보드 | [B-6 Status Badge]: 상태 자동 매핑 뱃지
- [B-7 Metric Tile]: 1.08rem Bold 전광판 가격 박스 | [B-8 Accordion]: 무라이브러리 원클릭 서랍
- [B-9 Data Table]: 래퍼(`w-full overflow-x-auto`) | 폭 고정(table-layout:fixed; width:100%) | 긴글자(truncate-1 + title툴팁 세트) | 뱃지/버튼(nowrap 줄바꿈 금지) | 가격/수치(우측정렬 tabular-nums)

## 3. 상황별 디자인 프리셋 & Vibe Engine (무한 동적 확장)
- [대표 베이스라인]:
  * [P-1 퀀트 터미널]: 칠흑 매트 블랙(#090d16) + 네온 에메랄드 + 세미 직각 6px (데이터 밀도 1위, 전문 금융/차트)
  * [P-2 토스 미니멀]: 딥 슬레이트(#0f172a) + 일렉트릭 블루 + 소프트 라운딩 14px (대중적 핀테크, 극상 가독성)
  * [P-3 크립토/AI 하이테크]: 옵시디언(#0b0e14) + 골드/바이올렛 네온 글로우 8px (챗GPT, 웹3, 최첨단)
  * [P-4 블루칩 PB]: 클래식 딥 네이비(#0a192f) + 로얄 골드 + 모던 라운딩 8px (기관 투자자, 엔터프라이즈 신뢰형)
  * [P-5 비주얼 임팩트]: 메인 키 비주얼 선행 생성 ➔ 순수 Tailwind만으로 무드/컬러 일체화 (랜딩/쇼케이스 전용, AI Slop 원천 차단)
- [P-Custom 무한 동적 디스패처]:
  * 사장님이 [도메인 / 서비스 성격 / 참고 앱 URL 또는 캡처]만 던지면 AI가 최적 원소(A-1~A-3) 자동 조색/적용
  * 예: "P-Custom: 당근마켓 감성" ➔ 웜 화이트 + 오렌지 액센트 + 16px 소프트 라운딩
  * 예: "P-Custom: 노션 미니멀" ➔ 클린 모노톤 + 1px 극세 보더 + 흑백 볼드 타이포
  * 예: "P-Custom: 로빈후드" ➔ 딥 차콜 + 네온 라임그린 + 대형 전광판 차트

## 4. 사장님 1초 지시 공식 (Prompt Formula)
- [공식]: "[P-번호 또는 P-Custom 레퍼런스] + [B-번호 블록 조합] + [기능명] = 100% 종결 배포"
- [실전 예시 1]: "P-2 토스 스타일에 B-3 입력창, B-4 버튼, B-7 전광판으로 [RSI 판독기] 배포해라."
- [실전 예시 2]: "P-Custom: 로빈후드 라임그린 감성에 B-1 임베드 쉘, B-7 전광판으로 [급등주 발굴기] 배포해라."

## 5. 프론트엔드 5대 고속 조립 스택 (Fast-Track Stack)
- [S-1 UI 디자인]: Tailwind + shadcn/ui (A원단 토큰 + B블록 조합으로 픽셀 땜질 0초)
- [S-2 데이터/통신]: TanStack Query / SWR (단 1줄 `useQuery`로 캐싱/자동갱신/로딩 100% 종결)
- [S-3 퀀트/차트]: Tremor / Recharts (수치 배열 주입 시 마우스 툴팁 인터랙티브 차트 5줄 컷)
- [S-4 회원/인증]: Clerk / Supabase Auth (구글/카카오 소셜 로그인 완제품 10분 연동)
- [S-5 폼 유효성]: Zod (T1 Input Distrust 규칙 2줄로 에러 안내 및 타입 추론 자동화)






