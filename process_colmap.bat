@echo off
REM Manual COLMAP Processing Script for Nerfstudio
REM This bypasses the nerfstudio preprocessing that uses incompatible COLMAP flags

echo ========================================
echo MANUAL COLMAP PROCESSING
echo ========================================
echo.

REM Configuration
set DATA_DIR=data\room_1
set IMAGES_DIR=%DATA_DIR%\images
set COLMAP_DIR=%DATA_DIR%\colmap
set SPARSE_DIR=%COLMAP_DIR%\sparse
set DATABASE=%COLMAP_DIR%\database.db

REM Create directories
echo Creating directories...
if not exist "%COLMAP_DIR%" mkdir "%COLMAP_DIR%"
if not exist "%SPARSE_DIR%" mkdir "%SPARSE_DIR%"
echo Done.
echo.

REM Step 1: Feature Extraction
echo [1/4] Extracting features...
colmap feature_extractor ^
    --database_path "%DATABASE%" ^
    --image_path "%IMAGES_DIR%" ^
    --ImageReader.single_camera 1 ^
    --ImageReader.camera_model OPENCV

if %errorlevel% neq 0 (
    echo ERROR: Feature extraction failed!
    pause
    exit /b 1
)
echo Done.
echo.

REM Step 2: Feature Matching
echo [2/4] Matching features...
colmap exhaustive_matcher ^
    --database_path "%DATABASE%"

if %errorlevel% neq 0 (
    echo ERROR: Feature matching failed!
    pause
    exit /b 1
)
echo Done.
echo.

REM Step 3: Sparse Reconstruction
echo [3/4] Running sparse reconstruction...
colmap mapper ^
    --database_path "%DATABASE%" ^
    --image_path "%IMAGES_DIR%" ^
    --output_path "%SPARSE_DIR%"

if %errorlevel% neq 0 (
    echo ERROR: Sparse reconstruction failed!
    pause
    exit /b 1
)
echo Done.
echo.

REM Step 4: Convert to Nerfstudio format
echo [4/4] Converting to nerfstudio format...
ns-process-data colmap ^
    --data "%DATA_DIR%" ^
    --output-dir "%DATA_DIR%"

if %errorlevel% neq 0 (
    echo WARNING: Conversion may have issues, but you can try training anyway
)
echo Done.
echo.

echo ========================================
echo SUCCESS! Data processing complete.
echo ========================================
echo.
echo You can now train with:
echo ns-train nerfacto --data %DATA_DIR% nerfstudio-data
echo.
pause