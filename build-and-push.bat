@echo off
REM AWS ECS 이미지 빌드 및 푸시 스크립트 (Windows)
REM 사용법: .env 파일에 AWS_ACCOUNT_ID와 AWS_REGION을 설정하고 build-and-push.bat 실행

setlocal enabledelayedexpansion
set "AWS_ACCOUNT_ID="
set "AWS_REGION="
set "ECR_REPOSITORY_NAME="
set "IMAGE_TAG="
set "ECR_REPOSITORY_URI="

REM .env 파일 확인
if not exist .env (
    echo Error: .env file not found
    echo.
    echo Please create .env file with the following content:
    echo   AWS_ACCOUNT_ID=123456789012
    echo   AWS_REGION=ap-northeast-2
    echo   ECR_REPOSITORY_NAME=final-py ^(optional^)
    echo   IMAGE_TAG=latest ^(optional^)
    exit /b 1
)

REM .env 파일에서 변수 로드
for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
    set "line=%%a"
    if not "!line:~0,1!"=="#" (
        set "key=%%a"
        set "value=%%b"
        for /f "tokens=*" %%c in ("!value!") do set "value=%%c"
        set "!key!=!value!"
    )
)

for /f "tokens=*" %%i in ("%AWS_ACCOUNT_ID%") do set "AWS_ACCOUNT_ID=%%i"
for /f "tokens=*" %%i in ("%AWS_REGION%") do set "AWS_REGION=%%i"
for /f "tokens=*" %%i in ("%ECR_REPOSITORY_NAME%") do set "ECR_REPOSITORY_NAME=%%i"
for /f "tokens=*" %%i in ("%IMAGE_TAG%") do set "IMAGE_TAG=%%i"
for %%v in (AWS_ACCOUNT_ID AWS_REGION ECR_REPOSITORY_NAME IMAGE_TAG) do (
    set "!%%v!=!%%v: =!!"
)

REM 필수 파라미터 확인
if "%AWS_ACCOUNT_ID%"=="" (
    echo Error: AWS_ACCOUNT_ID is required in .env file
    echo.
    echo Please add AWS_ACCOUNT_ID to your .env file:
    echo   AWS_ACCOUNT_ID=123456789012
    exit /b 1
)

REM 기본값 설정
if "%AWS_REGION%"=="" (
    set AWS_REGION=ap-northeast-2
)

if "%ECR_REPOSITORY_NAME%"=="" (
    set ECR_REPOSITORY_NAME=final-py
)

if "%IMAGE_TAG%"=="" (
    set IMAGE_TAG=latest
)

REM ECR 리포지토리 URI
set "ECR_REPOSITORY_URI=%AWS_ACCOUNT_ID%.dkr.ecr.%AWS_REGION%.amazonaws.com"
set "ECR_REPOSITORY_URI=!ECR_REPOSITORY_URI: =!"
set "ECR_REPOSITORY_URI=%ECR_REPOSITORY_URI%/%ECR_REPOSITORY_NAME%"

echo ==========================================
echo Building Docker image...
echo Repository: %ECR_REPOSITORY_URI%
echo Tag: %IMAGE_TAG%
echo ==========================================

REM Docker 이미지 빌드
docker build -t %ECR_REPOSITORY_NAME%:%IMAGE_TAG% .

if errorlevel 1 (
    echo Error: Docker build failed
    exit /b 1
)

REM ECR 로그인
echo Logging in to Amazon ECR...
aws ecr get-login-password --region %AWS_REGION% | docker login --username AWS --password-stdin %ECR_REPOSITORY_URI%

if errorlevel 1 (
    echo Error: ECR login failed
    exit /b 1
)

REM 리포지토리가 없으면 생성
echo Checking if ECR repository exists...
aws ecr describe-repositories --repository-names %ECR_REPOSITORY_NAME% --region %AWS_REGION% >nul 2>&1
if errorlevel 1 (
    echo Creating ECR repository: %ECR_REPOSITORY_NAME%
    aws ecr create-repository --repository-name %ECR_REPOSITORY_NAME% --region %AWS_REGION%
)

REM 이미지 태깅
echo Tagging image...
docker tag %ECR_REPOSITORY_NAME%:%IMAGE_TAG% %ECR_REPOSITORY_URI%:%IMAGE_TAG%

REM 이미지 푸시
echo Pushing image to ECR...
docker push %ECR_REPOSITORY_URI%:%IMAGE_TAG%

if errorlevel 1 (
    echo Error: Docker push failed
    exit /b 1
)

echo ==========================================
echo Successfully pushed image to ECR!
echo Image URI: %ECR_REPOSITORY_URI%:%IMAGE_TAG%
echo ==========================================

endlocal

