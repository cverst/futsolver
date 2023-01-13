from main.solver import SBCSolver


class TestSBCSolver:
    def test_get_formation_info(self):
        sbc_solver = SBCSolver(None, formation="442", max_cost=100000, minimize=False)
        sbc_solver._get_formation_info()
        assert sbc_solver.formation_list == [
            "GK",
            "RB",
            "CB_1",
            "CB_2",
            "LB",
            "RM",
            "CM_1",
            "CM_2",
            "LM",
            "ST_1",
            "ST_2",
        ]
        assert sbc_solver.team_size == 11
