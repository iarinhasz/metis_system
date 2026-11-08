"""Todo acesso ao banco do Metis.

Uma pasta por app Django (`queries/attempts/`, `queries/questions/`, …) e, dentro dela, um
Management por model. O model herda o Management, e o resto do código chama o método na
própria classe do model: `Run.get_with_events(run_id)`, nunca `Run.objects…`.
"""
