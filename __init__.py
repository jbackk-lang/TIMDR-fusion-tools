# fusion-tools
#
# Ten plik NIE re-eksportuje jeszcze podmodulow (timdr, latro, model_j,
# parsers) - wczesniej ten komentarz obiecywal to, czego kod nie robil.
# Import wyglada tak:
#
#   from timdr.timdr_filter import timdr
#   from latro.latro_core import latro
#   from model_j.model_j_detector import model_j
#   from parsers.csv_parser import load_csv
#
# (uruchamiane z katalogu glownego repo - timdr/, latro/, model_j/ i
# parsers/ sa "namespace packages" Pythona 3, wiec nie potrzebuja
# wlasnego __init__.py).
