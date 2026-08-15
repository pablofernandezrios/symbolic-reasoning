"""Exhaustive check of minimize.pl against a brute-force exact minimiser.

For every one of the 254 non-constant Boolean functions of 3 variables (and, optionally,
a random sample of 4-variable ones) this runs minimize/2 and checks two things:

  1. the result is logically equivalent to the input   -- soundness
  2. it uses as few terms as the true minimum          -- minimality

The true minimum is computed independently here, by generating all prime implicants and
then searching for the smallest subset of them that covers every minterm.

Usage:
    python verify_exhaustive.py            # all 3-variable functions
    python verify_exhaustive.py 4 40       # plus 40 random 4-variable functions
"""

import itertools
import os
import random
import re
import subprocess
import sys
import tempfile

SWIPL = "swipl"
MINIMIZE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "minimize.pl")


# --- formulas ---------------------------------------------------------------

def to_prolog(term):
    kind = term[0]
    if kind == "var":
        return term[1]
    if kind == "not":
        return "not (%s)" % to_prolog(term[1])
    if kind == "and":
        return "(%s and %s)" % (to_prolog(term[1]), to_prolog(term[2]))
    if kind == "or":
        return "(%s v %s)" % (to_prolog(term[1]), to_prolog(term[2]))
    raise ValueError(kind)


def evaluate(term, env):
    kind = term[0]
    if kind == "var":
        if term[1] == "true":
            return True
        if term[1] == "false":
            return False
        return env[term[1]]
    if kind == "not":
        return not evaluate(term[1], env)
    if kind == "and":
        return evaluate(term[1], env) and evaluate(term[2], env)
    if kind == "or":
        return evaluate(term[1], env) or evaluate(term[2], env)
    raise ValueError(kind)


def dnf_from_minterms(minterms, variables):
    """Build the canonical DNF of an explicit set of minterms."""
    terms = []
    for bits in minterms:
        literals = [("var", v) if b else ("not", ("var", v))
                    for v, b in zip(variables, bits)]
        term = literals[0]
        for lit in literals[1:]:
            term = ("and", term, lit)
        terms.append(term)
    formula = terms[0]
    for term in terms[1:]:
        formula = ("or", formula, term)
    return formula


# --- the independent exact minimiser ----------------------------------------

def prime_implicants(minterms, nvars):
    current = set(tuple(m) for m in minterms)
    primes = set()
    while current:
        used, nxt = set(), set()
        items = list(current)
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                diff = [k for k in range(nvars) if a[k] != b[k]]
                if len(diff) == 1 and a[diff[0]] != "-" and b[diff[0]] != "-":
                    merged = list(a)
                    merged[diff[0]] = "-"
                    nxt.add(tuple(merged))
                    used.add(a)
                    used.add(b)
        primes |= {c for c in current if c not in used}
        current = nxt
    return sorted(primes, key=lambda t: tuple(str(x) for x in t))


def covers(implicant, minterm):
    return all(implicant[k] == "-" or implicant[k] == minterm[k]
               for k in range(len(minterm)))


def minimum_cover_size(minterms, primes):
    if not minterms:
        return 0
    for size in range(1, len(primes) + 1):
        for combo in itertools.combinations(primes, size):
            if all(any(covers(p, m) for p in combo) for m in minterms):
                return size
    return None


# --- driving minimize.pl ----------------------------------------------------

def run_minimize(formula, timeout=120):
    goal = ("( catch(minimize(%s, Min), E, (print_message(error, E), fail)) -> "
            "write('RESULT='), write_canonical(Min), nl "
            "; write('RESULT=FAIL'), nl )." % to_prolog(formula))
    fd, path = tempfile.mkstemp(suffix=".pl", text=True)
    with os.fdopen(fd, "w") as fh:
        fh.write(":- initialization(main, main).\nmain :- %s\n" % goal)
    try:
        proc = subprocess.run([SWIPL, "-g", "true", "-t", "halt", MINIMIZE, path],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None
    finally:
        os.unlink(path)
    match = re.search(r"RESULT=(.*)", proc.stdout)
    return match.group(1).strip() if match else None


def parse(text):
    """Parse write_canonical output: v(A,B), and(A,B), not(A)."""
    pos = [0]

    def parse_term():
        while pos[0] < len(text) and text[pos[0]] in " \t":
            pos[0] += 1
        match = re.match(r"[a-z][A-Za-z0-9_]*", text[pos[0]:])
        if not match:
            raise ValueError("bad token in %r" % text)
        name = match.group(0)
        pos[0] += len(name)
        if pos[0] < len(text) and text[pos[0]] == "(":
            pos[0] += 1
            args = [parse_term()]
            while pos[0] < len(text) and text[pos[0]] == ",":
                pos[0] += 1
                args.append(parse_term())
            pos[0] += 1  # closing paren
            return {"v": ("or",), "and": ("and",), "not": ("not",)}[name] + tuple(args)
        return ("var", name)

    return parse_term()


def count_terms(term):
    if term[0] == "or":
        return count_terms(term[1]) + count_terms(term[2])
    return 1


# --- the check ---------------------------------------------------------------

def check(minterms, variables):
    nvars = len(variables)
    formula = dnf_from_minterms(minterms, variables)
    optimal = minimum_cover_size(minterms, prime_implicants(minterms, nvars))

    raw = run_minimize(formula)
    if raw is None or raw == "FAIL":
        return "no output"

    result = parse(raw)
    for bits in itertools.product([0, 1], repeat=nvars):
        env = dict(zip(variables, [bool(b) for b in bits]))
        if evaluate(formula, env) != evaluate(result, env):
            return "NOT EQUIVALENT: %s" % raw
    if result in (("var", "true"), ("var", "false")):
        return None
    terms = count_terms(result)
    if terms > optimal:
        return "not minimal (%d > %d): %s" % (terms, optimal, raw)
    return None


def main():
    variables = ["a", "b", "c"]
    all_bits = list(itertools.product([0, 1], repeat=3))
    failures = 0
    total = 0
    for mask in range(1, 255):  # skip the constant-false and constant-true functions
        minterms = [all_bits[i] for i in range(8) if (mask >> i) & 1]
        problem = check(minterms, variables)
        total += 1
        if problem:
            failures += 1
            print("  mask %3d %s -> %s" % (mask, minterms, problem))
    print("3 variables: %d/%d functions equivalent and minimal" % (total - failures, total))

    if len(sys.argv) > 2 and sys.argv[1] == "4":
        n = int(sys.argv[2])
        variables = ["a", "b", "c", "d"]
        all_bits = list(itertools.product([0, 1], repeat=4))
        random.seed(0)
        failures = 0
        for _ in range(n):
            minterms = sorted(random.sample(all_bits, random.randint(2, 14)))
            problem = check(minterms, variables)
            if problem:
                failures += 1
                print("  %s -> %s" % (minterms, problem))
        print("4 variables: %d/%d sampled functions equivalent and minimal"
              % (n - failures, n))


if __name__ == "__main__":
    main()
