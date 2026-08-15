# Written by Pablo Fernández Ríos and Yare Brea Espinosa. 

import argparse


# Reads a text domain file and returns all puzzle parameters
def read_domain(input_file: str) -> tuple[int, int, str, list[str], list[str]]:

    with open(file=input_file, mode='r') as f:
        # Read all lines, stripping trailing newlines and ignoring blank lines
        domain = [line.rstrip('\n') for line in f if line.strip()]

        # First line: board size (n) and stitches per region pair (m)
        n, m = domain[0].split()
        n, m = int(n), int(m)

        # Flatten all region rows into a single string
        regions = "".join(domain[1:-2])

        # Column and row hole limits (lines right after the grid)
        columns_limit = domain[-2].split()
        rows_limit    = domain[-1].split()

    return (n, m, regions, columns_limit, rows_limit)


# Writes Clingo facts (.lp) from the parsed puzzle parameters
def save_domain(output_file: str, n: int, m: int, regions: str, columns_limit: list[str], rows_limit: list[str]) -> None:

    with open(file=output_file, mode='w', encoding="utf-8") as f:
        # Define constants used throughout the Clingo program
        f.write(f"#const n = {n}.\t")  # Board dimension
        f.write(f"#const m = {m}.\n")  # Stitches per region pair

        f.write(f"cell(0..{n*n-1}).  % cell(0..(n*n-1))\n\n")  # Board dimension

        # Group cell indices by their region character in a single pass
        region_map = {}
        for pos, char in enumerate(regions):
            if char not in region_map:
                region_map[char] = []
            region_map[char].append(str(pos))

        # Write the compact facts (for instance: inRegion(0, (1;2;5;9))) line by line
        for i, char in enumerate(sorted(region_map.keys())):
            f.write(f"inRegion({i}, ({'; '.join(region_map[char])})).\n")

        f.write("\n")
        # Write the columnHoles(NColumn, Limit) facts that limit the number of holes in a column
        for i in range(n):
            f.write(f"columnHoles({i}, {columns_limit[i]}). ")
            if i % 5 == 4:  # Avoid stacking every fact on the same line, for a prettier format
                f.write("\n")

        f.write("\n\n")
        # Write the rowHoles(NRow, Limit) facts that limit the number of holes in a row
        for i in range(n):
            f.write(f"rowHoles({i}, {rows_limit[i]}). ")
            if i % 5 == 4:
                f.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Encode")
    parser.add_argument("input_file", help="File to read the puzzle domain from")
    parser.add_argument("output_file", help="File to write the Clingo domain to")

    args = parser.parse_args()

    # Parse the text file and write the corresponding Clingo facts
    n, m, regions, columns_limit, rows_limit = read_domain(args.input_file)
    save_domain(args.output_file, n, m, regions, columns_limit, rows_limit)
