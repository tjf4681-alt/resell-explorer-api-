# 리셀탐색기 실가격 API - Render용

이 폴더를 GitHub 저장소에 올리고 Render에 연결하면,
v3.3 탐색기의 "실가격 API 주소" 칸에 넣을 URL을 만들 수 있습니다.

## 가장 쉬운 순서

### 1. GitHub
1) github.com 로그인
2) 새 저장소(New repository) 만들기
3) 이름 예: `resell-explorer-api`
4) 이 ZIP을 풀어서 아래 파일 4개를 저장소에 업로드
   - app.py
   - requirements.txt
   - Dockerfile
   - render.yaml
5) Commit

### 2. Render
1) render.com 로그인
2) New + 선택
3) Blueprint 또는 Web Service 선택
4) 방금 만든 GitHub 저장소 연결
5) Docker 방식으로 배포
6) 배포 완료 후 주소 확인
   예: https://resell-explorer-api.onrender.com

### 3. 작동 확인
브라우저에서:
https://내주소.onrender.com/health

정상이면:
{"ok":true}

그 다음:
https://내주소.onrender.com/search?q=RTX%205090&sites=eBay,Amazon

JSON 결과가 나오면 서버가 작동하는 것입니다.

### 4. v3.3에 연결
1) v3.3 탐색기 열기
2) 상단 "실가격 API 주소"
3) Render 주소만 입력
   예: https://resell-explorer-api.onrender.com
4) "연결 저장"
5) 검색 시작

## 현재 연결 대상
- eBay
- Amazon
- 네이버쇼핑
- 번개장터
- 중고나라
- TCGplayer
- Mercari JP
- RockAuto
- Partsouq

사이트가 봇차단/로그인/지역제한을 걸면 결과가 0건 또는 실패 로그로 나올 수 있습니다.
그 경우 가격을 임의 생성하지 않습니다.

## 중요한 점
- eBay/Amazon/국내 사이트들은 HTML 구조나 접근정책이 바뀌면 파서 수정이 필요할 수 있습니다.
- 공식 API가 있는 서비스는 추후 공식 API로 교체하는 것이 가장 안정적입니다.
- Render 무료 플랜은 한동안 사용하지 않으면 잠들 수 있어 첫 요청이 느릴 수 있습니다.
