% Written by Pablo Fernández Ríos and Yare Brea Espinosa.

% Note that we already reduce all valid stitches to those where X is smaller than Y
% A stitch is valid if X and Y are in the same row at distance 1...
validStitch(X, Y) :- cell(X), cell(Y), |X - Y| = 1, X / n = Y / n, X < Y.
% ...or in the same column at distance n
validStitch(X, Y) :- cell(X), cell(Y), |X - Y| = n, X < Y.

% Generate every combination of adjacent stitches with X < Y (a restriction that
% comes from validStitch) that join two different regions Z and Z'
{stitch(X, Y) : validStitch(X, Y), inRegion(Z, X), inRegion(Z', Y), Z != Z'}.

% Two stitches cannot share a hole
:- cell(C), #count{ X : stitch(C, X); Y : stitch(Y, C) } > 1.

% The predicate hole collects any cell C taking part in some stitch
hole(C) :- stitch(C, _).
hole(C) :- stitch(_, C).

% Check the number of holes in column K is exactly Y
:- columnHoles(K, Y), #count{ C : hole(C), C \ n = K } != Y.
% Check the number of holes in row K is exactly Y
:- rowHoles(K, Y), #count{ C : hole(C), C / n = K} != Y.

% Define the horizontally and vertically adjacent regions, leaning on the valid stitches
adjacentRegions(A, B) :- inRegion(A, X), inRegion(B, Y), A < B, validStitch(X, Y).
adjacentRegions(A, B) :- inRegion(A, X), inRegion(B, Y), A < B, validStitch(Y, X).  % Both directions are needed

% Any two adjacent regions must be joined by exactly m stitches
:- adjacentRegions(A, B),
    #count { X, Y: stitch(X, Y), inRegion(A, X), inRegion(B, Y);
             X, Y: stitch(X, Y), inRegion(A, Y), inRegion(B, X) } != m.

#show stitch/2.
