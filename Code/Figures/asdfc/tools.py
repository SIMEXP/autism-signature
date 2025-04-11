import sys
import time
import itertools as it


def find_all_combinations(n_elements, n_group=2):
    # Define the session IDs
    elements = list(range(n_elements))
    # Find all combinations of 2 sessions to compute ICC on
    icc_sessions = list(it.combinations(elements, n_group))
    # Find the remaining sessions for each of the ICC sessions
    remaining_sessions = [list(set(elements) - set(icc_s)) for icc_s in icc_sessions]
    # Find all combinations of subtype sessions for 1 - 8 subtype sessions
    session_pairs = [(icc, sbt) for rem, icc in zip(remaining_sessions, icc_sessions)
                     for n_sbt in range(1, len(rem) + 1)
                     for sbt in list(it.combinations(rem, n_sbt))]

    return session_pairs
