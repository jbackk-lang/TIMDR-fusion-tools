import os

from parsers.csv_parser import load_csv

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_CSV = os.path.join(REPO_ROOT, "data", "w7x_mirnov_example.csv")


def test_load_example_csv():
    """
    Also serves as a regression test for the README's own documented
    import path: it used to say `from parsers.csv_parser import load_csv`,
    but the file actually lived at tools/parsers/csv_parser.py (confirmed
    broken via a live ModuleNotFoundError). It has been moved to
    parsers/csv_parser.py so the documented import path is now correct.
    """
    time, signal = load_csv(EXAMPLE_CSV)
    assert len(time) == len(signal)
    assert len(time) == 2000
