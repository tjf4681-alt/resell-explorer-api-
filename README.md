# Resell Explorer API v2

지원 사이트를 대폭 늘린 버전입니다.

## 지원 범위
- 국내 종합/가격비교
- 국내 중고/리셀
- 패션/신발
- PC/전자
- 자동차부품
- 카드/컬렉터
- 해외 종합
- 필리핀

## 업데이트 방법
기존 GitHub 저장소의 아래 4개 파일을 이 ZIP의 파일로 덮어쓰면 됩니다.
- app.py
- requirements.txt
- Dockerfile
- render.yaml

README.md도 덮어써도 됩니다.

Render가 GitHub 변경을 감지하면 자동 재배포됩니다.

## 확인
배포 후:
- /health
- /sites
- /search?q=RTX%205090&sites=eBay,Amazon,쿠팡,다나와

## 주의
직접 HTML 파싱 또는 Google site: 검색 보조 방식이라,
사이트의 봇 차단/로그인/JS 렌더링 정책에 따라 0건이 나올 수 있습니다.
0건이면 임의 가격을 만들지 않습니다.
