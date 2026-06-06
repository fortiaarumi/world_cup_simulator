"""
Tests for the Round-of-32 third-place allocation (official FIFA Annex C table).

Guards against the regression where a group winner could be drawn against a
third-placed team from its OWN group (e.g. Belgium (1G) vs Egypt/Iran (3G)).
"""
import os
import sys
from itertools import combinations

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.core import STAGE
from engine.sim import Competition
from engine.schedule import (
    get_third_place_groups,
    THIRD_PLACE_POOLS,
    ROUND_OF_32_BRACKET,
)
from engine.third_place_table import THIRD_PLACE_ASSIGNMENTS

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "wc_2026_teams.json",
)

# Group winner that hosts the third-placed team in each "1v3" match.
WINNER_GROUP = {74: "E", 77: "I", 79: "A", 80: "L",
                81: "D", 82: "G", 85: "B", 87: "K"}


class TestAnnexCTable:
    """The shipped 495-row allocation table is complete and self-consistent."""

    def test_covers_all_495_combinations(self):
        expected = {"".join(c) for c in combinations("ABCDEFGHIJKL", 8)}
        assert set(THIRD_PLACE_ASSIGNMENTS) == expected
        assert len(THIRD_PLACE_ASSIGNMENTS) == 495

    def test_every_combo_is_valid(self):
        """For all 495 combos: a bijection, in-pool, with no same-group rematch."""
        for combo in combinations("ABCDEFGHIJKL", 8):
            assignment = get_third_place_groups(set(combo))
            # exactly the 8 matches that host a 3rd-placed team
            assert set(assignment) == set(THIRD_PLACE_POOLS)
            # bijection onto the advancing groups
            assert sorted(assignment.values()) == sorted(combo)
            for match_num, group in assignment.items():
                # opponent is drawn only from the official pool for that match
                assert group in THIRD_PLACE_POOLS[match_num]
                # and never from the winner's own group
                assert group != WINNER_GROUP[match_num]

    def test_invalid_combo_raises(self):
        with pytest.raises(ValueError):
            get_third_place_groups(set("ABCDEFG"))   # only 7 groups
        with pytest.raises(ValueError):
            get_third_place_groups(set("ABCDEFGHI"))  # 9 groups


class TestBelgiumRegression:
    """The exact scenario from the bug report."""

    def test_group_g_winner_never_faces_group_g_third(self):
        # Whenever G's third-placed team advances, match 82 (1G) must not host it.
        for combo in combinations("ABCDEFGHIJKL", 8):
            if "G" in combo:
                assignment = get_third_place_groups(set(combo))
                assert assignment[82] != "G", (
                    f"combo {''.join(combo)} sends 3G into match 82 (1G)"
                )

    def test_known_official_assignment(self):
        # Official Annex C row for advancing groups A,B,C,D,G,J,K,L:
        # match 82 (1G) is allocated the 3rd-placed team from group A.
        assignment = get_third_place_groups(set("ABCDGJKL"))
        assert assignment[82] == "A"


class TestIntegration:
    """The allocation is wired correctly into build_round_of_32."""

    def _full_competition(self):
        return Competition.from_json_file(DATA_FILE, random_seed=7)

    def test_assignment_maps_to_correct_teams(self):
        """_assign_third_place_teams returns, for each match, a team whose group
        matches the Annex C table and is never the winner's group."""
        comp = self._full_competition()
        # Pick a deterministic advancing set without relying on match results:
        # use each group's seeded 3rd team as a stand-in third-placed side.
        combo = list("ABCDGJKL")
        comp.advancing_third_place = [comp.groups[g].teams[2] for g in combo]
        comp.advancing_third_groups = set(combo)

        by_match = comp._assign_third_place_teams()
        expected = get_third_place_groups(set(combo))
        for match_num, team in by_match.items():
            assert team.group.name == expected[match_num]
            assert team.group.name != WINNER_GROUP[match_num]

    def test_full_simulation_has_no_same_group_r32_pairing(self):
        comp = self._full_competition()
        comp.simulate()
        group_of = {t.name: t.group.name for t in comp.teams}
        r32 = comp.knockout_matches[STAGE.ROUND_OF_32]
        assert len(r32) == 16
        for m in r32:
            assert group_of[m.home_team.name] != group_of[m.away_team.name], (
                f"match {m.number}: {m.home_team.name} vs {m.away_team.name} "
                f"are both from group {group_of[m.home_team.name]}"
            )

    def test_onev3_matches_host_the_group_winner(self):
        """Each 1v3 match must contain the designated group winner plus a
        third-placed team from a different group."""
        comp = self._full_competition()
        comp.simulate()
        group_of = {t.name: t.group.name for t in comp.teams}
        by_num = {m.number: m for m in comp.knockout_matches[STAGE.ROUND_OF_32]}
        for match_num, (_, ptype, src1, _s2) in ROUND_OF_32_BRACKET.items():
            if ptype == "1v3":
                m = by_num[match_num]
                groups = {group_of[m.home_team.name], group_of[m.away_team.name]}
                assert src1[1] in groups          # the group winner is present
                assert len(groups) == 2           # opponent from another group


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
