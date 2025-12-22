#!/bin/bash
# AWS ECS 이미지 빌드 및 푸시 스크립트 (Linux/Mac)
# 사용법: .env 파일에 AWS_ACCOUNT_ID와 AWS_REGION을 설정하고 build-and-push.sh 실행

set -e

# 변수 초기화
AWS_ACCOUNT_ID=""
AWS_REGION=""
ECR_REPOSITORY_NAME=""
IMAGE_TAG=""
ECR_REPOSITORY_URI=""

# .env 파일 확인
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo ""
    echo "Please create .env file with the following content:"
    echo "  AWS_ACCOUNT_ID=123456789012"
    echo "  AWS_REGION=ap-northeast-2"
    echo "  ECR_REPOSITORY_NAME=final-py (optional)"
    echo "  IMAGE_TAG=latest (optional)"
    exit 1
fi

# .env 파일에서 변수 로드
while IFS='=' read -r key value || [ -n "$key" ]; do
    # 주석 라인 무시
    if [[ $key =~ ^#.*$ ]] || [[ -z "$key" ]]; then
        continue
    fi
    
    # 앞뒤 공백 제거
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    
    case "$key" in
        AWS_ACCOUNT_ID)
            AWS_ACCOUNT_ID="$value"
            ;;
        AWS_REGION)
            AWS_REGION="$value"
            ;;
        ECR_REPOSITORY_NAME)
            ECR_REPOSITORY_NAME="$value"
            ;;
        IMAGE_TAG)
            IMAGE_TAG="$value"
            ;;
    esac
done < .env

# 필수 파라미터 확인
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "Error: AWS_ACCOUNT_ID is required in .env file"
    echo ""
    echo "Please add AWS_ACCOUNT_ID to your .env file:"
    echo "  AWS_ACCOUNT_ID=123456789012"
    exit 1
fi

# 기본값 설정
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="ap-northeast-2"
fi

if [ -z "$ECR_REPOSITORY_NAME" ]; then
    ECR_REPOSITORY_NAME="final-py"
fi

if [ -z "$IMAGE_TAG" ]; then
    IMAGE_TAG="latest"
fi

# ECR 리포지토리 URI
ECR_REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}"

echo "=========================================="
echo "Building Docker image..."
echo "Repository: ${ECR_REPOSITORY_URI}"
echo "Tag: ${IMAGE_TAG}"
echo "=========================================="

# Docker 이미지 빌드
docker build -t "${ECR_REPOSITORY_NAME}:${IMAGE_TAG}" .

if [ $? -ne 0 ]; then
    echo "Error: Docker build failed"
    exit 1
fi

# ECR 로그인
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_REPOSITORY_URI}"

if [ $? -ne 0 ]; then
    echo "Error: ECR login failed"
    exit 1
fi

# 리포지토리가 없으면 생성
echo "Checking if ECR repository exists..."
aws ecr describe-repositories --repository-names "${ECR_REPOSITORY_NAME}" --region "${AWS_REGION}" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Creating ECR repository: ${ECR_REPOSITORY_NAME}"
    aws ecr create-repository --repository-name "${ECR_REPOSITORY_NAME}" --region "${AWS_REGION}"
fi

# 이미지 태깅
echo "Tagging image..."
docker tag "${ECR_REPOSITORY_NAME}:${IMAGE_TAG}" "${ECR_REPOSITORY_URI}:${IMAGE_TAG}"

# 이미지 푸시
echo "Pushing image to ECR..."
docker push "${ECR_REPOSITORY_URI}:${IMAGE_TAG}"

if [ $? -ne 0 ]; then
    echo "Error: Docker push failed"
    exit 1
fi

echo "=========================================="
echo "Successfully pushed image to ECR!"
echo "Image URI: ${ECR_REPOSITORY_URI}:${IMAGE_TAG}"
echo "=========================================="
