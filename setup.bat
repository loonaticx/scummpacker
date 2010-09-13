@echo off
FOR /F "tokens=1-4 delims=/ " %%I IN ('DATE /t') DO SET thedate=%%L%%K%%J
set app_name=scummpacker

E:\Apps\Programming\Python2.5\python.exe src\setup.py py2exe %1 --bundle 2
rd build /S /Q
rename dist %app_name%
rem copy lgpl.txt %app_name%
mkdir %app_name%\docs
copy docs\%app_name%_manual.html %app_name%\docs

E:\Utils\Misc\7-Zip\7z.exe a -tzip -mx9 -r %app_name%_bin_%thedate%.zip %app_name%
rd %app_name% /s /q

mkdir %app_name%
copy src ..\%app_name%
copy *.bat ..\%app_name%
rem copy lgpl.txt ..\%app_name%
rem mkdir %app_name%\docs
rem copy docs\* %app_name%\docs
copy docs %app_name%\docs

E:\Utils\Misc\7-Zip\7z.exe a -tzip -mx9 -r %app_name%_src_%thedate%.zip %app_name%
rd %app_name% /s /q