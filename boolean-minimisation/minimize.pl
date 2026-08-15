% Written by Yare Brea Espinosa and Pablo Fernández Ríos 

% 1) Operators
:- op(599, yfx, v).
:- op(400, yfx, and).   % Binds tighter than or
:- op(200, fy, not).    % Highest priority
:- op(1050, yfx, ->).   % Binds tighter than the biconditional
:- op(1200, yfx, <->).

% Template: minterm(Identifier, Implicant, Number of models the implicant covers,
%                   "x" if it has been merged | "o" if it has not)
:- dynamic minterm/4.

member(E, L):-  % member/2: true when E is an element of the list L
    append(_, [E|_], L).

powers_of_two(Vars, Power):-  % Powers of 2 up to 2^(length of Vars)
    append(Prefix, _, Vars),
    length(Prefix, Exponent),
    Power is 2^Exponent.

% 2) Unfold, to remove conditionals and biconditionals

% Base case
unfold(A, [A], A) :- atom(A), !.  % An atom is stored in Vars and returned unchanged

% Recursive cases
unfold(A -> B, Vars, Unfold) :-
    unfold(A,VarsA, FA), unfold(B, VarsB, FB), findall(C, (member(C, VarsA); member(C, VarsB), \+ member(C, VarsA)), Vars), Unfold = not FA v FB.

unfold(A <-> B, Vars, Unfold) :-
    unfold(A, VarsA, FA), unfold(B, VarsB, FB), findall(C, (member(C, VarsA); member(C, VarsB), \+ member(C, VarsA)), Vars), Unfold = (FA and FB) v (not FA and not FB).

unfold(not A, Vars, Unfold) :-
    unfold(A, Vars, FA), Unfold = not FA.

unfold(A v B, Vars, Unfold) :-
    unfold(A, VarsA, FA), unfold(B, VarsB, FB), findall(C, (member(C, VarsA); member(C, VarsB), \+ member(C, VarsA)), Vars), Unfold = FA v FB.

unfold(A and B, Vars, Unfold) :-
    unfold(A, VarsA, FA), unfold(B, VarsB, FB), findall(C, (member(C, VarsA); member(C, VarsB), \+ member(C, VarsA)), Vars), Unfold = FA and FB.



% 3) Tab
% NOTE: this section is the propositional tableau engine supplied with the
% course template; it is not our own work. Everything else in this file is.
literal_(L) :- atom(L).
literal_(not L) :- atom(L).
compl_(not A,A) :- !.
compl_(A, not A).

% Treats the list where the element is inserted as a set
% where an atom and its negation cannot be in the set together.
addlit_(F,[],[F]) :- !.
addlit_(F,[F|L],[F|L]) :- !.
addlit_(F,[G|L],[G|L2]) :- \+ compl_(F,G), addlit_(F,L,L2).

%% tab_(+FormulaList, +AuxList, -ModelList)
% Applies the tabulation method to a list of formulas
% Obtains the list of models of the conjuction of all formulas in FormulaList
% AuxList should be an empty list
% The models are expressed as a list of literals
tab_([],B,B) :- !.
tab_([F|L],B,Bn) :- literal_(F),!,addlit_(F,B,B1),tab_(L,B1,Bn).

% Does not insert complementary literals in the B (B1) list.
tab_([not not F|L],B,Bn) :- tab_([F|L],B,Bn).  % not not
tab_([F v G|L],B,Bn) :- tab_([F|L],B,Bn); tab_([G|L],B,Bn).
tab_([not (F and G)|L],B,Bn) :- tab_([not F|L],B,Bn); tab_([not G|L],B,Bn).  % negated and is or of the negations
tab_([F and G|L],B,Bn) :- tab_([F,G|L],B,Bn).
tab_([not (F v G) |L],B,Bn) :- tab_([not F,not G|L],B,Bn).  % negated or is and of the negations


%%%% Obtains the dfn of a formula from a list of clauses
% An empty clause carries no literals, so it stands for the constant true
% (it is what a tautology minimises to).
toclause([],true):-!.
toclause([A],A):-!.
toclause([A|As],A and G):- toclause(As,G).

% No clauses at all means the formula has no models: the constant false.
todnf([],false):-!.
todnf([A],F) :- !, toclause(A,F).
todnf([A|As],F v G) :- toclause(A,F), todnf(As,G).



% 4) to_model/3 extracts the models of a branch produced by tab_/3, with the help
% of bit_of/3. Template: to_model(Tableau branch, Variable list, Model)
bit_of(Branch, Var, 1) :- member(Var, Branch), !.        % The literal occurs, so the bit is 1
bit_of(Branch, Var, 0) :- member(not Var, Branch), !.    % Its complement occurs, so the bit is 0
% If neither occurs the variable is free, so we produce both bits
bit_of(_, _, 1).
bit_of(_, _, 0).

% Base case
to_model(_, [], []):-!.
% Recursive case
to_model(Branch, [H|T], [Val|Tail]) :-
    bit_of(Branch, H, Val),
    to_model(Branch, T, Tail).


% 5) implicant_length/2 gives the number of models an implicant covers.
% Template: implicant_length(Implicant, Number of models it covers)

% Base cases
implicant_length([], 0):- !.

implicant_length([H], Length) :-
    H = -, !, Length is 2;   % Every dash doubles the number of models covered
    Length is 1, !.

% Recursive case
implicant_length([H|T], Length) :-
    implicant_length([H], L1), implicant_length(T, L2),
    Length is L1*L2.

% 6) implicant_id/3 gives the identifier (the minterm number) of an implicant.
% Template: implicant_id(Implicant, Identifier, Running power of two)
implicant_id([], [0], 0) :- !.
implicant_id([Bit|Rest], [ID_number], Power):-
    implicant_id(Rest, [NewID], NewPower),
    Power is NewPower + 1,
    ID_number is (Bit * (2 ^ NewPower) + NewID).  % Binary to decimal by powers of two

% 7) compare_implicants/4 compares two implicants position by position and builds the
% merged one. A Distance of 1 means they differ in exactly one bit, so they can be merged.
% Template: compare_implicants(Implicant1, Implicant2, Number of differing positions, Merged implicant)
% Note: only implicants covering the same number of models should be passed in

% Base case
compare_implicants([H1], [H2], Distance, NewImp):-
    H1 \= H2, !,
    Distance is 1,      % They differ here, so raise the counter and write a dash
    NewImp = [-];
    NewImp = [H1], Distance is 0, !.

% Recursive case
compare_implicants([H1|T1], [H2|T2], Distance, NewImp) :-
    compare_implicants([H1], [H2], Distance1, NewImp1),
    compare_implicants(T1, T2, Distance2, NewImp2),
    Distance is (Distance1 + Distance2), append(NewImp1, NewImp2, NewImp).

% 8) store_terms/1 stores the implicants it receives in minterm/4, marking them unmerged ("o")
store_terms([]) :- !.
store_terms([Implicant|Tail]) :-
    implicant_length(Implicant, NumModels),
    implicant_id(Implicant, Id, _),
    assertz(minterm(Id, Implicant, NumModels, o)),
    store_terms(Tail).

% 9) minterms/1 receives a power of two (the number of models covered by the implicants
% to compare) and performs the merging pass for that column.
%
% The parents are picked regardless of their flag. An implicant has to stay available
% as a merge partner even once it has been absorbed, because in Quine-McCluskey a term
% must be combined with EVERY neighbour it has, not just the first one found. Marking
% it "x" only records that it is no longer a prime implicant.
minterms(Size) :-
    minterm(Id1, Implicant1, Size, _),  % Any implicant of this column
    minterm(Id2, Implicant2, Size, _),
    Id1 \= Id2,                         % We do not want to compare one with itself
    append(Id1, Id2, Ids),
    sort(Ids, NewID),                   % Sorting makes the identifier canonical, so that
                                        % merging (4,5) and (5,4) does not store it twice
    \+ minterm(NewID, _, _, _),         % Continue only if this merge does not already exist
    compare_implicants(Implicant1, Implicant2, 1, NewImplicant),  % The real test: can they be merged?
    implicant_length(NewImplicant, NewLength),
    mark_used(Id1, Implicant1, Size),   % Neither parent is prime any more
    mark_used(Id2, Implicant2, Size),
    assertz(minterm(NewID, NewImplicant, NewLength, o)).  % Store the resulting implicant

% mark_used/3 flags an implicant as absorbed while keeping exactly one copy of it
mark_used(Id, Implicant, Size) :-
    retractall(minterm(Id, Implicant, Size, o)),
    (   minterm(Id, Implicant, Size, x)
    ->  true                                        % Already marked by an earlier merge
    ;   assertz(minterm(Id, Implicant, Size, x))
    ).


% 10) Covering phase
%
% Whatever is still marked "o" after the merging passes is a prime implicant. We now
% need the smallest subset of those that still covers every minterm.
%
% An earlier version of this dropped, one at a time, any prime implicant that covered
% no minterm uniquely. That is sound (it never drops a minterm) but it is greedy and
% order dependent, so on a cyclic chart -- one where no prime implicant is essential --
% it stopped early and returned a redundant cover. We now search for covers of
% increasing size and stop at the first one that works, which is therefore minimum.

% 10.1) set_to_cover/1 returns the smallest set of prime implicants that covers every minterm
set_to_cover(PrimeImplicants) :-
    findall(ID-Implicant, minterm(ID, Implicant, _, o), Primes),  % The ones left with "o" are the prime implicants
    findall(M, (member(ID-_, Primes), member(M, ID)), AllMinterms),
    sort(AllMinterms, Minterms),   % Every minterm that has to be covered, without repetitions
    length(Primes, Total),
    between(0, Total, Size),       % Try a cover of 0 implicants, then 1, then 2...
    subset_of(Primes, Size, Chosen),
    covers(Minterms, Chosen), !,   % Cut on the first success: sizes grow, so this one is minimum
    findall(Implicant, member(_-Implicant, Chosen), PrimeImplicants).

% 10.2) subset_of/3 picks Size elements out of the list, keeping their order
subset_of(_, 0, []) :- !.
subset_of([H|T], Size, [H|Rest]) :- Size > 0, Size1 is Size - 1, subset_of(T, Size1, Rest).
subset_of([_|T], Size, Rest) :- Size > 0, subset_of(T, Size, Rest).

% 10.3) covers/2 checks that every minterm appears in the ID of some chosen implicant
covers([], _) :- !.
covers([M|T], Chosen) :-
    member(ID-_, Chosen), member(M, ID), !,
    covers(T, Chosen).

% 11) toterms/3 turns a list of implicants into a list of terms
% Template: toterms(List of prime implicants, Variable list, List of terms)

% Base case
proposition([], [], []) :- !.
% Recursive cases
proposition([1|T], [Var|VarTail], [Var|RestVars]) :- proposition(T, VarTail, RestVars), !.       % Bit 1: add the variable
proposition([0|T], [Var|VarTail], [not Var|RestVars]) :- proposition(T, VarTail, RestVars), !.   % Bit 0: add its negation
proposition([_|T], [_|VarTail], RestVars) :- proposition(T, VarTail, RestVars), !.               % A dash: the variable drops out

% Base case
toterms([], _, []).
% Recursive case
toterms([H|T], Vars, [HeadTerm|TailTerm]) :-
    proposition(H, Vars, HeadTerm),
    toterms(T, Vars, TailTerm).

% 12) MAIN PREDICATE minimize/2. Takes a formula and returns a minimal DNF
% Template: minimize(Formula, Minimised formula)
minimize(F, Min) :-
    retractall(minterm(_, _, _, _)),  % Clear the table left behind by any previous call
    unfold(F, Vars, Unfold),          % Remove conditionals and biconditionals
    findall(Model, (tab_([Unfold], [], Branch), to_model(Branch, Vars, Model)), Implicants),  % Collect the models
    store_terms(Implicants),          % Store them as the starting implicants
    findall(_, (powers_of_two(Vars, Power), minterms(Power)), _),  % Merge implicants column by column
    set_to_cover(PrimeTerms),         % Choose the smallest covering set of prime implicants
    toterms(PrimeTerms, Vars, Terms), % Turn the prime implicants back into terms
    todnf(Terms, Min).                % Assemble the minimised formula
