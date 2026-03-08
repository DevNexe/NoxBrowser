from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
# load font like application does
import os
font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'MaterialSymbolsRounded.ttf')
if os.path.exists(font_path):
    QFontDatabase.addApplicationFont(font_path)

fonts = QFontDatabase().families()
materials = [f for f in fonts if 'Material' in f]
print('Material fonts:', materials)
print('Has Material Symbols Rounded?', 'Material Symbols Rounded' in fonts)
