@echo off
setlocal

echo [1/2] Installing dependencies...
python -m pip install -r requirements.txt

echo [2/2] Building VoteFree.exe ...
pyinstaller --noconfirm --clean --windowed ^
  --name VoteFree ^
  --add-data "votefree_app\templates;votefree_app\templates" ^
  --add-data "votefree_app\static;votefree_app\static" ^
  main.py

echo Build done. Output: dist\VoteFree\VoteFree.exe
pause
