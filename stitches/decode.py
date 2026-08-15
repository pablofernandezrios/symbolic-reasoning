# Written by Pablo Fernández Ríos and Yare Brea Espinosa. 

import clingo
import sys
import re


################################## SOLVING ###################################

def solving(ctl: clingo.Control) -> list[tuple[int, int]] | None:
    nummodels = 0
    solution: list[tuple[int, int]] = []

    with ctl.solve(yield_=True) as handle:
        for model in handle:
            # A unique solution is expected, warn and stop on a second model
            if nummodels > 0:
                print("Warning: more than 1 model")
                break

            # Collect every stitch(X, Y) atom from the model
            for atom in model.symbols(atoms=True):
                if atom.name == "stitch" and len(atom.arguments) == 2:
                    x = atom.arguments[0].number
                    y = atom.arguments[1].number
                    solution.append((x, y))

            nummodels = 1

    if nummodels == 0:  # No model found
        print("UNSATISFIABLE")
        return None     # Return None rather than an empty solution, so the caller
                        # does not write out a board full of dots for an unsolvable puzzle

    return solution


# Writes the solution as an n x n text board using directional symbols
def showsolution(output_file: str, solution: list[tuple[int, int]], n: int) -> None:

    # Build an empty board
    board = [['.' for _ in range(n)] for _ in range(n)]

    for a, b in solution:
        row_a, col_a = a // n, a % n  # Convert linear index to row, col
        row_b, col_b = b // n, b % n

        if row_a == row_b:  # Horizontal stitch: > then <
            board[row_a][col_a] = '>'
            board[row_b][col_b] = '<'
        else:               # Vertical stitch: v then ^
            board[row_a][col_a] = 'v'
            board[row_b][col_b] = '^'

    with open(file=output_file, mode='w', encoding="utf-8") as f:
        for row in board:
            f.write(''.join(row) + '\n')


# Extracts the board size n from a '#const n=...' line in a Clingo domain file
def extract_n(filepath: str) -> int:

    with open(filepath, mode='r') as f:
        line = f.readline()
        match = re.search(r'#const\s+n\s*=\s*(\d+)', line)
        if match:
            return int(match.group(1))

    # Without n we cannot lay the board out, so fail loudly instead of returning None
    raise ValueError(f"Error: could not find a '#const n = ...' declaration on the first line of {filepath}")


################################ MAIN PROGRAM #################################
if __name__ == "__main__":
    if len(sys.argv) < 4:  # Need: rules file, domain file, output file
        print("Usage: decode.py <rules.lp> <domain.lp> <output.txt>")
        sys.exit()

    # Set up Clingo: load rules + domain, ground, allow up to 2 models
    ctl = clingo.Control()
    ctl.add("base", [], "")
    for arg in sys.argv[1:3]:     # Load rules file and domain file
        ctl.load(arg)
    ctl.ground([("base", [])])
    ctl.configuration.solve.models = "2"  # Retrieve at most 2 models to detect non-uniqueness

    n = extract_n(sys.argv[2])    # Read board size from the domain file

    # Solve and write the output board if a solution exists
    solution = solving(ctl)
    if solution is not None:
        showsolution(output_file=sys.argv[3], solution=solution, n=n)
