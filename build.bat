REM Clear current session log 
cls
REM Source environment (Uncomment lines starting with "set" if you current env does not have these defined.)
set DCC=MAYA
REM set HFS=C:\Program Files\Side Effects Software\Houdini 19.5.605
set MAYA_DEVKIT=C:\qvisten_pipeline\assetResolver\devkit_2024
set MAYA_ROOT=C:\Program Files\Autodesk\Maya2022
REM Define Resolver > Has to be one of 'fileResolver'/'pythonResolver'/'cachedResolver'/'httpResolver'
set RESOLVER_NAME=cachedResolver
REM Clear existing build data and invoke cmake
rmdir /S /Q build
rmdir /S /Q dist
cmake . -B build -G "Visual Studio 16 2019" -A x64 -T v142
cmake --build build  --clean-first --config Release
cmake --install build