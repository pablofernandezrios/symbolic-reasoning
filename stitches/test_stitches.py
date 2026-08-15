"""Tests for the Stitches solver.

These run Clingo, so they need the `clingo` package (see requirements.txt).
"""

import subprocess
import sys
from pathlib import Path

import pytest

clingo = pytest.importorskip("clingo")

REPO = Path(__file__).parent
PYTHON = sys.executable
RULES = (REPO / "stitches.lp").read_text(encoding="utf-8")

sys.path.insert(0, str(REPO))
import encode  # noqa: E402
import decode  # noqa: E402


def solve(domain_lp: str, limit: int = 0) -> list[list[tuple[int, int]]]:
    """Return every model of the rules plus the given domain facts."""
    ctl = clingo.Control()
    ctl.add("base", [], RULES + "\n" + domain_lp)
    ctl.ground([("base", [])])
    ctl.configuration.solve.models = str(limit)
    models = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            stitches = sorted(
                (a.arguments[0].number, a.arguments[1].number)
                for a in model.symbols(atoms=True)
                if a.name == "stitch" and len(a.arguments) == 2
            )
            models.append(stitches)
    return models


def encoded(name: str, tmp_path) -> str:
    """Run encode.py over a domain text file and return the generated facts."""
    out = tmp_path / "dom.lp"
    n, m, regions, cols, rows = encode.read_domain(str(REPO / name))
    encode.save_domain(str(out), n, m, regions, cols, rows)
    return out.read_text(encoding="utf-8")


# --- the encoder -------------------------------------------------------------

class TestEncode:
    def test_reads_the_domain(self):
        n, m, regions, cols, rows = encode.read_domain(str(REPO / "dom1.txt"))
        assert (n, m) == (4, 1)
        assert regions == "aabbacbbccddcddd"
        assert cols == ["2", "3", "3", "2"]
        assert rows == ["2", "4", "4", "0"]

    def test_regions_are_numbered_in_sorted_order(self, tmp_path):
        facts = encoded("dom1.txt", tmp_path)
        # 'a' is region 0 and holds cells 0, 1 and 4
        assert "inRegion(0, (0; 1; 4))." in facts
        # 'd' is region 3
        assert "inRegion(3, (10; 11; 13; 14; 15))." in facts

    def test_constants_and_cells(self, tmp_path):
        facts = encoded("dom1.txt", tmp_path)
        assert "#const n = 4." in facts
        assert "#const m = 1." in facts
        assert "cell(0..15)." in facts

    def test_row_and_column_limits(self, tmp_path):
        facts = encoded("dom1.txt", tmp_path)
        assert "columnHoles(1, 3)." in facts
        assert "rowHoles(3, 0)." in facts


# --- the encoding itself -----------------------------------------------------

class TestSolving:
    def test_dom1_has_exactly_one_solution(self, tmp_path):
        models = solve(encoded("dom1.txt", tmp_path))
        assert len(models) == 1

    def test_dom1_solution_is_the_expected_one(self, tmp_path):
        models = solve(encoded("dom1.txt", tmp_path))
        assert models[0] == [(1, 2), (4, 8), (5, 6), (7, 11), (9, 10)]

    def test_unsat_instance(self, tmp_path):
        """The authors' own regression case: regions a and c are adjacent but every
        way of connecting them clashes with the row and column counts."""
        assert solve(encoded("dom_unsat.txt", tmp_path)) == []

    def test_every_stitch_joins_two_different_regions(self, tmp_path):
        facts = encoded("dom1.txt", tmp_path)
        region_of = {}
        for cell, ch in enumerate("aabbacbbccddcddd"):
            region_of[cell] = ch
        for x, y in solve(facts)[0]:
            assert region_of[x] != region_of[y]

    def test_no_cell_is_used_by_two_stitches(self, tmp_path):
        stitches = solve(encoded("dom1.txt", tmp_path))[0]
        used = [c for pair in stitches for c in pair]
        assert len(used) == len(set(used))

    def test_stitches_only_join_adjacent_cells(self, tmp_path):
        for x, y in solve(encoded("dom1.txt", tmp_path))[0]:
            same_row = abs(x - y) == 1 and x // 4 == y // 4
            same_col = abs(x - y) == 4
            assert same_row or same_col

    def test_row_and_column_counts_are_met(self, tmp_path):
        stitches = solve(encoded("dom1.txt", tmp_path))[0]
        rows = [0] * 4
        cols = [0] * 4
        for pair in stitches:
            for c in pair:
                rows[c // 4] += 1
                cols[c % 4] += 1
        assert rows == [2, 4, 4, 0]
        assert cols == [2, 3, 3, 2]

    def test_adjacent_regions_joined_exactly_m_times(self, tmp_path):
        """m = 1 here, and there are five adjacent region pairs, so there must be
        exactly five stitches -- one per pair."""
        stitches = solve(encoded("dom1.txt", tmp_path))[0]
        assert len(stitches) == 5
        region_of = {c: ch for c, ch in enumerate("aabbacbbccddcddd")}
        pairs = [tuple(sorted((region_of[x], region_of[y]))) for x, y in stitches]
        assert sorted(pairs) == [("a", "b"), ("a", "c"), ("b", "c"), ("b", "d"), ("c", "d")]


# --- the decoder -------------------------------------------------------------

class TestDecode:
    def test_board_matches_the_committed_solution(self, tmp_path):
        stitches = solve(encoded("dom1.txt", tmp_path))[0]
        out = tmp_path / "sol.txt"
        decode.showsolution(str(out), stitches, 4)
        expected = (REPO / "sol1.txt").read_text(encoding="utf-8")
        assert out.read_text(encoding="utf-8").replace("\r\n", "\n") == expected

    def test_extract_n(self, tmp_path):
        dom = tmp_path / "d.lp"
        dom.write_text("#const n = 7.\t#const m = 2.\n", encoding="utf-8")
        assert decode.extract_n(str(dom)) == 7

    def test_extract_n_without_declaration_raises(self, tmp_path):
        dom = tmp_path / "bad.lp"
        dom.write_text("cell(0..3).\n", encoding="utf-8")
        with pytest.raises(ValueError, match="#const n"):
            decode.extract_n(str(dom))

    def test_unsat_writes_no_board(self, tmp_path):
        """An unsolvable puzzle must not leave a board full of dots behind."""
        dom_lp = tmp_path / "dom.lp"
        n, m, regions, cols, rows = encode.read_domain(str(REPO / "dom_unsat.txt"))
        encode.save_domain(str(dom_lp), n, m, regions, cols, rows)

        out = tmp_path / "sol.txt"
        result = subprocess.run(
            [PYTHON, str(REPO / "decode.py"), str(REPO / "stitches.lp"), str(dom_lp), str(out)],
            capture_output=True, text=True, cwd=REPO,
        )
        assert "UNSATISFIABLE" in result.stdout
        assert not out.exists()


# --- end to end --------------------------------------------------------------

def test_command_line_round_trip(tmp_path):
    dom_lp = tmp_path / "dom1.lp"
    sol = tmp_path / "sol1.txt"
    subprocess.run([PYTHON, str(REPO / "encode.py"), str(REPO / "dom1.txt"), str(dom_lp)],
                   check=True, cwd=REPO)
    subprocess.run([PYTHON, str(REPO / "decode.py"), str(REPO / "stitches.lp"), str(dom_lp), str(sol)],
                   check=True, cwd=REPO)
    expected = (REPO / "sol1.txt").read_text(encoding="utf-8")
    assert sol.read_text(encoding="utf-8").replace("\r\n", "\n") == expected
