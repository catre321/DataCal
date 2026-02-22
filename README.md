# DataCal
Load data and input formular to make calculation

pip install "Nuitka[onefile]"
nuitka --onefile --windows-console-mode=attach --enable-plugin=tk-inter main.py

pyinstaller --onefile main.py