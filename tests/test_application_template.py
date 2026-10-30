"""`APIApplication.template.locked_deploy_settings`: optional key of the typed dict, with the two setting names."""

from __future__ import annotations

from typing import get_args, get_type_hints

from vertracloud.types import APIApplicationTemplate


def test_locked_deploy_settings_is_an_optional_list_of_the_two_settings() -> None:
    hints = get_type_hints(APIApplicationTemplate)
    assert "locked_deploy_settings" in hints
    assert "locked_deploy_settings" in APIApplicationTemplate.__optional_keys__
    (item,) = get_args(hints["locked_deploy_settings"])
    assert set(get_args(item)) == {"zero_downtime", "auto_rollback"}
