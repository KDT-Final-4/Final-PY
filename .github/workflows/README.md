# GitHub Actions Workflows

## build-and-push.yml

파이썬 코드가 upstream의 main 브랜치에 merge될 때 자동으로 실행되는 워크플로우입니다.

### 역할
- 파이썬 코드를 Docker 이미지로 빌드
- ECR에 이미지 푸시 (final-py:latest)

### 트리거 조건
- upstream의 main 브랜치에 push
- 다음 파일 변경은 무시: `.md`, `.gitignore`, `.editorconfig`, `.gitattributes`, `README.md`

### 필요한 GitHub Secrets
upstream repository의 Settings → Secrets and variables → Actions에 다음을 추가해야 합니다:

1. `AWS_ACCESS_KEY_ID`: AWS 액세스 키 ID
2. `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 액세스 키

### AWS IAM 권한
GitHub Actions에서 사용할 IAM 역할에 다음 정책을 연결하세요:

**PowerUserAccess** (AWS 관리형 정책)
- AWS Console → IAM → Roles → `github-actions-role` 선택
- "권한 추가" → "PowerUserAccess" 정책 연결
- 백엔드와 동일한 방식으로 설정 가능
- ECR 이미지 빌드 및 푸시에 필요한 모든 권한이 포함되어 있습니다

### 결과
- ECR에 `final-py:latest` 이미지가 최신 코드로 업데이트됩니다.
- ECS 서비스는 자동으로 업데이트되지 않습니다 (CDK에서 관리).

