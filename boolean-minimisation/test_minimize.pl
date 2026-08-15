% Tests for minimize.pl
%
% Run with:  swipl -g run_tests -t halt minimize.pl test_minimize.pl
%
% Comparing the output term for term would be brittle, so instead each test checks the
% two things that actually matter: the minimised formula has exactly the same models as
% the original (soundness), and it uses the expected number of terms (minimality).

:- begin_tests(minimize).

% --- a small evaluator, so we can compare truth tables directly ---------------

eval(true, _) :- !.
eval(false, _) :- !, fail.
eval(not F, Env) :- !, \+ eval(F, Env).
eval(F and G, Env) :- !, eval(F, Env), eval(G, Env).
eval(F v G, Env) :- !, ( eval(F, Env) ; eval(G, Env) ).
eval(F -> G, Env) :- !, ( eval(F, Env) -> eval(G, Env) ; true ).
eval(F <-> G, Env) :- !,
    (   eval(F, Env), eval(G, Env)
    ;   \+ eval(F, Env), \+ eval(G, Env)
    ).
eval(A, Env) :- memberchk(A-1, Env).

% assignments(+Vars, -Env) enumerates every truth assignment over Vars
assignments([], []).
assignments([V|Vs], [V-B|Env]) :- member(B, [0,1]), assignments(Vs, Env).

% equivalent(+F, +G, +Vars) is true when F and G agree on every assignment
equivalent(F, G, Vars) :-
    forall(assignments(Vars, Env),
           ( eval(F, Env) -> eval(G, Env) ; \+ eval(G, Env) )).

% count_terms(+DNF, -N) counts the disjuncts
count_terms(F v G, N) :- !, count_terms(F, N1), count_terms(G, N2), N is N1 + N2.
count_terms(_, 1).

% check(+Formula, +Vars, -Min, -Terms)
check(F, Vars, Min, Terms) :-
    minimize(F, Min),
    equivalent(F, Min, Vars),
    count_terms(Min, Terms).


% --- soundness plus minimality ------------------------------------------------

test(absorption) :-
    check(a v (a and b), [a,b], Min, N),
    N =:= 1, Min == a.

test(complementary_pair) :-
    check((a and b) v (a and not b), [a,b], Min, N),
    N =:= 1, Min == a.

test(xor_is_already_minimal) :-
    check((a and not b) v (not a and b), [a,b], _, N),
    N =:= 2.

test(consensus_term_is_dropped) :-
    % b and c is implied by the other two, so a minimal cover has 2 terms
    check((not a and b) v (a and c) v (b and c), [a,b,c], _, N),
    N =:= 2.

test(majority_needs_three_terms) :-
    check((a and b) v (b and c) v (a and c), [a,b,c], _, N),
    N =:= 3.

test(implication) :-
    check(a -> b, [a,b], _, N),
    N =:= 2.

test(biconditional) :-
    check(a <-> b, [a,b], _, N),
    N =:= 2.

test(single_variable) :-
    check(a, [a], Min, N),
    N =:= 1, Min == a.


% --- the cyclic cover, which the first version of the covering phase got wrong ---

test(cyclic_cover_is_minimal) :-
    % Models 000, 001, 010, 101, 110, 111. Every prime implicant covers two minterms
    % and every minterm is covered twice, so no prime implicant is essential. A greedy
    % essential-only reduction returns 4 terms here; the minimum is 3.
    F = ( (not a and not b and not c) v (not a and not b and c) v (not a and b and not c)
        v (a and not b and c)         v (a and b and not c)     v (a and b and c) ),
    check(F, [a,b,c], _, N),
    N =:= 3.

test(second_cyclic_cover_is_minimal) :-
    F = ( (not a and not b and c) v (not a and b and not c) v (not a and b and c)
        v (a and not b and not c) v (a and not b and c)     v (a and b and not c) ),
    check(F, [a,b,c], _, N),
    N =:= 3.


% --- prime implicant generation ------------------------------------------------

test(merges_all_the_way_up) :-
    % Models 010, 100, 101, 110, 111. The minimum cover is a + (b and not c), which
    % only exists if 10- and 11- are merged into 1--. An implicant therefore has to
    % stay available as a merge partner after it has already been absorbed once.
    F = ( (not a and b and not c) v (a and not b and not c) v (a and not b and c)
        v (a and b and not c)     v (a and b and c) ),
    check(F, [a,b,c], _, N),
    N =:= 2.


% --- constants -----------------------------------------------------------------

test(tautology) :-
    minimize(a v not a, Min),
    Min == true.

test(contradiction) :-
    minimize(a and not a, Min),
    Min == false.

test(tautology_over_two_variables) :-
    minimize((a and b) v (not a) v (a and not b), Min),
    Min == true.


% --- repeated calls must not contaminate each other ----------------------------

test(consecutive_calls_are_independent) :-
    minimize((a and b) v (a and not b), M1),
    minimize((not a and b) v (a and c) v (b and c), M2),
    minimize((a and b) v (a and not b), M3),
    M1 == a,
    M1 == M3,
    count_terms(M2, 2).

:- end_tests(minimize).
