# symbolic-reasoning

> **Note:** this repository is a fork of work developed as a pair with Yare Brea Espinosa
> (ASP for Stitches, Prolog for Boolean minimisation). Development was done locally and
> jointly. Original repo: https://github.com/YareBE/symbolic-reasoning

Two declarative solvers: a Stitches puzzle solver written in Answer Set Programming, and a
Boolean formula minimiser written in Prolog that goes from a propositional formula to a
minimal disjunctive normal form via semantic tableaux and Quine–McCluskey.

Both share a premise. You describe *what* a correct answer looks like and let a solver find
one, instead of writing a procedure that constructs it.

| directory | language | what it does |
|---|---|---|
| [`stitches/`](stitches) | ASP (clingo) + Python | Solves Stitches puzzles; 34 lines of ASP with a Python encoder/decoder |
| [`boolean-minimisation/`](boolean-minimisation) | Prolog (SWI) | Minimal DNF of a propositional formula, via tableaux + Quine–McCluskey |

---

# stitches

## The puzzle

A Stitches board is an `n × n` grid partitioned into irregular regions. You have to draw
*stitches*: short segments joining two orthogonally adjacent cells that lie in **different**
regions. The rules are:

- Every pair of regions that touch must be joined by exactly `m` stitches — *every* pair, so
  two regions that share a border and get no stitch make the board invalid.
- A cell can be the endpoint of at most one stitch. An endpoint is called a *hole*.
- The number of holes in each row and each column is given, and must be matched exactly.

The difficulty is that the three constraints pull against each other. Row and column counts
decide *how many* holes go where, region adjacency decides *which pairs* must be joined, and
the one-stitch-per-cell rule couples every local choice to its neighbours. It is a
constraint satisfaction problem with no useful greedy strategy, which makes it a natural fit
for ASP: state the rules, let the grounder and solver do the search.

## How each rule maps to the encoding

The whole solver is 34 lines. Reading it constraint by constraint:

**Geometry.** Two cells are stitchable if they are horizontally adjacent (differ by 1 and
share a row) or vertically adjacent (differ by `n`). Cells are numbered `0..n²-1`, so row is
`C / n` and column is `C \ n`.

```prolog
validStitch(X, Y) :- cell(X), cell(Y), |X - Y| = 1, X / n = Y / n, X < Y.
validStitch(X, Y) :- cell(X), cell(Y), |X - Y| = n, X < Y.
```

The `X < Y` is not cosmetic: it makes each unordered pair appear exactly once, so a stitch
has a single canonical representation and the solver never has to consider `stitch(5,4)`
alongside `stitch(4,5)`. The row check on the first rule stops cell 3 and cell 4 — adjacent
by number, but on opposite edges of a 4-wide board — from counting as neighbours.

**Generate.** A single choice rule proposes any set of stitches:

```prolog
{stitch(X, Y) : validStitch(X, Y), inRegion(Z, X), inRegion(Z', Y), Z != Z'}.
```

**No shared holes.** A cell may appear in at most one stitch, in either position:

```prolog
:- cell(C), #count{ X : stitch(C, X); Y : stitch(Y, C) } > 1.
```

**Row and column counts.** `hole/1` is derived from both endpoints, then counted:

```prolog
hole(C) :- stitch(C, _).
hole(C) :- stitch(_, C).
:- columnHoles(K, Y), #count{ C : hole(C), C \ n = K } != Y.
:- rowHoles(K, Y),    #count{ C : hole(C), C / n = K } != Y.
```

**Exactly `m` stitches per adjacent region pair.** Adjacency between regions is derived from
the cells, taken in both directions because `validStitch` is one-directional:

```prolog
adjacentRegions(A, B) :- inRegion(A, X), inRegion(B, Y), A < B, validStitch(X, Y).
adjacentRegions(A, B) :- inRegion(A, X), inRegion(B, Y), A < B, validStitch(Y, X).
:- adjacentRegions(A, B),
    #count { X, Y: stitch(X, Y), inRegion(A, X), inRegion(B, Y);
             X, Y: stitch(X, Y), inRegion(A, Y), inRegion(B, X) } != m.
```

## Design notes

**One number per cell instead of a row and a column.** A board position could have been
modelled as a pair `(row, column)`, which is how the puzzle is drawn. Instead every cell is
a single integer in `0..n²-1`, and the row and column are recovered arithmetically as
`C / n` and `C \ n`. That choice propagates through the whole encoding: `stitch/2` takes two
integers rather than four, adjacency is `|X - Y| = 1` or `|X - Y| = n` instead of a
comparison on pairs, and the row and column counts are single `#count` aggregates over a
division and a modulo. Most of the reason the program fits in 34 lines is this decision
taken on the first one.

**Restricting the generator instead of filtering afterwards.** The first working version
proposed a `stitch(X, Y)` for any pair of cells with `X < Y` and then threw away the invalid
ones with constraints. That is the textbook generate-and-test shape and it is correct, but
it hands the grounder every pair on the board. Folding `validStitch` and the `Z != Z'`
region test into the choice rule itself means only genuinely stitchable cross-region pairs
are ever created. On a 10×10 board cut into 25 regions, that is the difference between
grounding 4950 candidate `stitch/2` atoms and grounding 80 — the search space the solver
then has to explore is smaller by the same factor.

**Deriving region adjacency from the board, not from the model.** This one was an actual
bug, and it is the most interesting thing in the encoding. An earlier version derived
"regions A and B are connected" from the stitches present in the candidate model, and then
required that count to be `m`. The flaw is that if two adjacent regions had *no* stitch
between them, the predicate was never derived for that pair, so the constraint had nothing
to fire on and the board was accepted. The solver happily returned SATISFIABLE for boards
that were not solvable. Deriving `adjacentRegions` from `inRegion` and `validStitch`
instead — from the board's fixed geometry rather than from the guess — makes the constraint
fire on every pair that ought to be joined. `dom_unsat.txt` is the minimal case that exposed
it, kept as a regression test.

**A single `hole/1` predicate instead of four counts.** Row and column limits originally
needed four separate aggregates, because a hole can be the first or second element of a
stitch. Deriving `hole/1` from both positions collapses that to two counts and reads far
closer to the way the puzzle is stated.

**Asking for two models on purpose.** `decode.py` sets `ctl.configuration.solve.models = "2"`
even though exactly one solution is expected. Asking for two is how the program *detects*
that a puzzle is under-constrained: if a second model comes back it prints a warning rather
than silently presenting one arbitrary answer as though it were the answer. Asking for one
could never tell the difference.

## Running it

```
$ pip install -r stitches/requirements.txt
$ cd stitches
$ python encode.py dom1.txt dom1.lp        # puzzle text -> clingo facts
$ python decode.py stitches.lp dom1.lp sol1.txt   # solve and render the board
```

### Worked example

`dom1.txt` describes a 4×4 board with `m = 1`:

```
4 1
aabb
acbb
ccdd
cddd
2 3 3 2
2 4 4 0
```

The first line is `n` and `m`. The next four lines give each cell's region. The last two
lines are the per-column and per-row hole counts.

Five pairs of regions touch — `a-b`, `a-c`, `b-c`, `b-d` and `c-d` — so with `m = 1` the
board needs exactly five stitches and therefore ten holes, which is what the row counts
`2 + 4 + 4 + 0` add up to. Note the last row must contain no holes at all.

`encode.py` turns this into facts, numbering regions in sorted order (`a` → 0 … `d` → 3):

```prolog
#const n = 4.   #const m = 1.
cell(0..15).

inRegion(0, (0; 1; 4)).
inRegion(1, (2; 3; 6; 7)).
inRegion(2, (5; 8; 9; 12)).
inRegion(3, (10; 11; 13; 14; 15)).

columnHoles(0, 2). columnHoles(1, 3). columnHoles(2, 3). columnHoles(3, 2).
rowHoles(0, 2). rowHoles(1, 4). rowHoles(2, 4). rowHoles(3, 0).
```

and the solver produces `stitch(1,2)`, `stitch(4,8)`, `stitch(5,6)`, `stitch(7,11)`,
`stitch(9,10)` — one per adjacent region pair — which `decode.py` renders as `sol1.txt`:

```
.><.
v><v
^><^
....
```

`>` and `<` are the two ends of a horizontal stitch, `v` and `^` the ends of a vertical one.
The solution is unique; `decode.py` would warn if it were not.

`dom_unsat.txt` is the 2×2 counterexample described above, and correctly prints
`UNSATISFIABLE` without writing a board.

### Tests

```
$ python -m pytest stitches/test_stitches.py -q
17 passed
```

The tests check the encoder's output facts, then assert the solved board satisfies each
puzzle rule independently of the encoding — no shared holes, only adjacent cells joined,
row and column counts met, exactly one stitch per adjacent region pair — and that the
unsatisfiable instance stays unsatisfiable.

## Known limitations

- **Region labels are single characters**, so a board cannot have more than the number of
  distinct printable characters you are willing to type, and regions are assumed contiguous
  without ever checking it. A disconnected "region" would be accepted and treated as one.
- **The encoder validates almost nothing.** A domain file whose row of counts is the wrong
  length, or whose grid is not `n` lines of `n` characters, will produce malformed facts
  or an `IndexError` rather than a clear message.
- **Only exact counts are supported.** Real Stitches puzzles are always stated this way, but
  the encoding has no way to express "at most" or "at least".
- **Only the first solution is reported.** With two models requested, a non-unique puzzle is
  detected and warned about, but the alternatives are not shown.

---

# boolean-minimisation

## The problem

Given a propositional formula — with `and`, `v`, `not`, `->` and `<->` — produce a
*minimal* disjunctive normal form: a sum of products with as few terms as possible that is
true on exactly the same assignments. This is the classical logic-design problem, and it
splits into three stages that are each interesting on their own:

1. **Find the models.** Rewrite away the conditionals, then run a semantic tableau to
   enumerate every satisfying assignment.
2. **Grow the prime implicants.** Repeatedly merge pairs of implicants that differ in one
   position, replacing that position with a dash. This is Quine–McCluskey's merging phase.
3. **Cover.** Choose the fewest prime implicants that together still cover every model.

Stage 3 is the one with teeth: it is a set-cover problem, and it is NP-hard.

## Design notes

**Models come from a tableau, not a truth table.** Instead of enumerating all `2ⁿ`
assignments, `tab_/3` decomposes the formula into branches, each of which is a partial
assignment. `bit_of/3` then expands any variable a branch never constrained into both `0`
and `1`, which is what turns a partial branch into concrete models.

**An implicant's identity is the set of minterms it covers.** Each implicant is stored as
`minterm(ID, Implicant, Size, Flag)`, where `ID` is the list of decimal minterm numbers it
covers. Merging two implicants is then just concatenating their IDs, and the covering stage
can ask "is this minterm covered?" by looking in the ID rather than re-deriving anything.
IDs are sorted so that merging `(4,5)` and `(5,4)` yields the same canonical identifier and
the result gets stored once.

**An absorbed implicant must stay available as a merge partner.** This is the subtlety that
makes or breaks the merging phase. When two implicants merge, both are flagged as no longer
prime — but they must still be *reachable* for further merges in the same column, because
Quine–McCluskey requires every term to be combined with every neighbour it has, not just the
first one found. Dropping them outright means `10-` and `11-` never combine into `1--`, the
prime implicant `a` is never generated, and the minimiser then returns three terms where two
would do. `mark_used/3` exists precisely to flag without removing.

**Covering searches by increasing size rather than reducing greedily.** An earlier version
repeatedly discarded any prime implicant that covered no minterm uniquely. That is sound —
it never drops a minterm — but it is greedy and order dependent, and on a *cyclic* cover
chart, where no prime implicant is essential, it stops early with a redundant answer.
`set_to_cover/1` now enumerates candidate covers of size 0, 1, 2 … and cuts at the first one
that covers everything, which is therefore minimum by construction. Cyclic charts are the
motivating case and there are tests for two of them.

## Running it

```
$ swipl minimize.pl
?- minimize((not a and b) v (a and c) v (b and c), M).
M = not a and b v a and c.

?- minimize(a <-> b, M).
M = a and b v not a and not b.

?- minimize(a v not a, M).
M = true.
```

Operators are `and`, `v`, `not`, `->` and `<->`, with `not` binding tightest and `<->`
loosest, so `a and b v c` parses as `(a and b) v c`.

### Tests

```
$ swipl -g run_tests -t halt minimize.pl test_minimize.pl
% All 15 tests passed
```

Rather than pin exact output terms, each test checks that the minimised formula has the
same truth table as the input and uses the expected number of terms.

There is also an exhaustive differential check against an independent brute-force minimiser
written in Python:

```
$ python verify_exhaustive.py 4 40
3 variables: 254/254 functions equivalent and minimal
4 variables: 40/40 sampled functions equivalent and minimal
```

That covers every non-constant Boolean function of three variables.

## Known limitations

- **It enumerates models, so it is exponential in the number of variables** in both time and
  memory, before the NP-hard covering stage even starts. This is a teaching implementation
  and is comfortable with a handful of variables, not with thirty.
- **The covering search is brute force.** Candidate covers are enumerated by increasing size
  with no bounding or dominance rules, so a function with many prime implicants and a large
  minimum cover will be slow. Correct, but not an industrial minimiser.
- **Only one formula at a time, and only propositional logic** — no predicates, no
  quantifiers, no multi-output minimisation and no don't-care conditions.
- **Variables are Prolog atoms**, so they must be lowercase or quoted.
- **The propositional tableau in section 3 of `minimize.pl` came with the course template**
  and is not our own work; it is marked as such in the source. Everything else is.

---

## Attribution

Coursework for the second year of the AI degree at the Universidade da Coruña, both written
in a pair by **Yare Brea Espinosa** and **Pablo Fernández Ríos**. Comments and identifiers
have been translated from Spanish to English.

Licensed under the MIT License — see [LICENSE](LICENSE).
