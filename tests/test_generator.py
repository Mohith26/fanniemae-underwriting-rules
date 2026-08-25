"""Generator determinism and validity."""
from underwritekit.generator import AppGenerator


def test_same_seed_is_deterministic():
    a = [app.to_dict() for app in AppGenerator(123).stream(300)]
    b = [app.to_dict() for app in AppGenerator(123).stream(300)]
    assert a == b


def test_different_seeds_differ():
    a = [app.to_dict() for app in AppGenerator(1).stream(100)]
    b = [app.to_dict() for app in AppGenerator(2).stream(100)]
    assert a != b


def test_generated_apps_are_valid():
    for app in AppGenerator(7).stream(2000):
        app.validate()


def test_stream_yields_exact_count():
    assert sum(1 for _ in AppGenerator(5).stream(1234)) == 1234


def test_population_hits_all_occupancies_and_units():
    apps = list(AppGenerator(11).stream(5000))
    assert {a.occupancy for a in apps} == {"primary", "second_home", "investment"}
    assert {a.units for a in apps} == {1, 2, 3, 4}
    assert {a.property_type for a in apps} == {
        "single_family", "condo", "manufactured",
    }
