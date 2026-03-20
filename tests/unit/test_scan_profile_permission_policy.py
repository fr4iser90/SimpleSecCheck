from domain.policies.scan_profile_policy import (
    is_scan_profile_allowed,
    resolve_max_allowed_scan_profile_for_actor,
    scan_profile_settings,
)


def test_profile_hierarchy_allows_downgrade():
    order = ["quick", "standard", "deep"]
    assert is_scan_profile_allowed(selected_profile="quick", max_allowed_profile="deep", profile_order=order)
    assert is_scan_profile_allowed(selected_profile="standard", max_allowed_profile="deep", profile_order=order)
    assert is_scan_profile_allowed(selected_profile="quick", max_allowed_profile="standard", profile_order=order)


def test_profile_hierarchy_blocks_upgrade():
    order = ["quick", "standard", "deep"]
    assert not is_scan_profile_allowed(selected_profile="deep", max_allowed_profile="standard", profile_order=order)
    assert not is_scan_profile_allowed(selected_profile="standard", max_allowed_profile="quick", profile_order=order)


def test_resolve_max_allowed_profile_for_roles():
    settings = scan_profile_settings()
    assert resolve_max_allowed_scan_profile_for_actor(settings, actor_role="admin", is_authenticated=True) == "deep"
    assert resolve_max_allowed_scan_profile_for_actor(settings, actor_role="user", is_authenticated=True) == "standard"
    assert resolve_max_allowed_scan_profile_for_actor(settings, actor_role="", is_authenticated=False) == "quick"
