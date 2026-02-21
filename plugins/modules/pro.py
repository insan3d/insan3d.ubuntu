"""Manage Ubuntu Pro services with the `pro` CLI."""

import json
from typing import Any

from ansible.module_utils.basic import AnsibleModule  # pyright: ignore[reportMissingTypeStubs]

DOCUMENTATION = r"""
---
module: insan3d.ubuntu.pro
short_description: Manage Ubuntu Pro services with the C(pro) CLI
description:
  - Returns C(pro status --wait --format=json) when invoked without arguments.

  - When called with C(state=attached), runs C(pro attach --format=json) and
    optionally enables/disables services.

  - When called with C(state=detached), runs C(pro detach --assume-yes --format=json).

options:
  state:
    type: str
    choices:
      - attached
      - detached

    description:
      - Desired Ubuntu Pro attachment state.

  token:
    type: str
    description:
      - Ubuntu Pro token used for attaching when required.

  enabled:
    type: list
    elements: str
    description:
      - List of services to enable (requires the system to be attached).

  disabled:
    type: list
    elements: str
    description:
      - List of services to disable (requires the system to be attached).
"""

EXAMPLES = r"""
- name: Return Ubuntu Pro status only
  insan3d.ubuntu.pro:

- name: Attach and enable selected services
  insan3d.ubuntu.pro:
    state: attached
    token: "{{ pro_token }}"
    enabled:
      - esm-apps
      - esm-infra
      - livepatch

- name: Disable services
  insan3d.ubuntu.pro:
    disabled:
      - livepatch

- name: Detach Ubuntu Pro
  insan3d.ubuntu.pro:
    state: detached
"""

RETURN = r"""
changed:
  description: Whether the module made changes.
  type: bool
  returned: always

status:
  description: Parsed JSON from C(pro status --wait --format=json).
  type: dict
  returned: always

enabled:
  description: Services that were enabled.
  type: list
  elements: str
  returned: when changed

disabled:
  description: Services that were disabled.
  type: list
  elements: str
  returned: when changed

attach_result:
  description: Parsed JSON output from C(pro attach) if executed.
  type: dict
  returned: when changed

detach_result:
  description: Parsed JSON output from C(pro detach) if executed.
  type: dict
  returned: when changed

enable_result:
  description: Parsed JSON output from C(pro enable) if executed.
  type: dict
  returned: when changed

disable_result:
  description: Parsed JSON output from C(pro disable) if executed.
  type: dict
  returned: when changed
"""


_ENABLED = ("enabled", "active", "on")


def _execute(
    module: AnsibleModule,
    args: list[str],
) -> tuple[dict[str, Any] | None, str, str]:
    """
    Run a command and parse JSON output when available.

    Args:
        module: Ansible module instance used to execute the command.
        args: Command arguments to execute.

    Returns:
        Parsed JSON (or raw output), stdout, and stderr.
    """

    rc, out, err = module.run_command(args)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    if rc != 0:
        module.fail_json(msg="command failed", rc=rc, stdout=out, stderr=err, cmd=args)  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]

    if not out:
        return None, out, err  # pyright: ignore[reportUnknownVariableType]

    try:
        return json.loads(out), out, err  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]

    except ValueError:
        return {"raw": out}, out, err  # pyright: ignore[reportUnknownVariableType]


def _service_enabled(service: dict[str, Any]) -> bool:
    """
    Extract enabled flag from JSON.

    Args:
        service: Service entry from the status payload.

    Returns:
        True if enabled, otherwise False.
    """

    if "enabled" in service:
        return bool(service["enabled"])

    status = service.get("status")
    if isinstance(status, str):
        return status.lower() in _ENABLED

    state = service.get("state")
    if isinstance(state, str):
        return state.lower() in _ENABLED

    return False


def _collect_enabled_services(status: dict[str, Any] | None) -> set[str]:
    """
    Extract currently enabled service names from the status payload.

    Args:
        status: Parsed JSON output of pro status.

    Returns:
        Set of enabled service names.
    """

    service_entries: list[dict[str, Any]] = status.get("services", []) if isinstance(status, dict) else []
    current_enabled: set[str] = set()

    for svc in service_entries:
        name = svc.get("name")
        if not name:
            continue

        if _service_enabled(svc):
            current_enabled.add(name)

    return current_enabled


def _status_attached(status: dict[str, Any] | None) -> bool:
    """
    Return True when the system is attached.

    Args:
        status: Parsed JSON output of pro status.

    Returns:
        True if attached.
    """

    if isinstance(status, dict) and "attached" in status:
        return bool(status.get("attached"))

    return False


def _get_status(module: AnsibleModule, pro: str) -> dict[str, Any] | None:
    """
    Get current Ubuntu Pro status.

    Returns:
        Parsed C(pro status --wait --format=json) output.
    """

    status, _, _ = _execute(module, [pro, "status", "--wait", "--format=json"])
    return status


def _maybe_attach(
    module: AnsibleModule,
    pro: str,
    token: str,
    result: dict[str, Any],
) -> bool:
    """
    Attach the system to Ubuntu Pro subscription.

    Returns:
        The attach result.
    """

    attach_result, _, _ = _execute(module, [pro, "attach", "--format=json", token])
    result["attach_result"] = attach_result
    return True


def _maybe_detach(
    module: AnsibleModule,
    pro: str,
    result: dict[str, Any],
) -> bool:
    """
    Detach the system from Ubuntu Pro subscription.

    Returns:
        The detach result.
    """

    detach_result, _, _ = _execute(module, [pro, "detach", "--assume-yes", "--format=json"])
    result["detach_result"] = detach_result
    return True


def _maybe_enable_services(
    module: AnsibleModule,
    pro: str,
    to_enable: list[str],
    result: dict[str, Any],
) -> bool:
    """
    Enable requested services.

    Returns:
        The enable result.
    """

    enable_result, _, _ = _execute(
        module,
        [pro, "enable", "--assume-yes", "--format=json", *to_enable],
    )

    result["enable_result"] = enable_result
    result["enabled"] = to_enable
    return True


def _maybe_disable_services(
    module: AnsibleModule,
    pro: str,
    to_disable: list[str],
    result: dict[str, Any],
) -> bool:
    """
    Disable services.

    Returns:
        The disable result.
    """

    disable_result, _, _ = _execute(
        module,
        [pro, "disable", "--assume-yes", "--format=json", *to_disable],
    )

    result["disable_result"] = disable_result
    result["disabled"] = to_disable
    return True


def main() -> None:  # noqa: C901, PLR0914
    """Ansible module to manage Ubuntu Pro services with the `pro` CLI."""

    module_args: dict[str, Any] = {
        "state": {"type": "str", "choices": ["attached", "detached"], "required": False},
        "token": {"type": "str", "required": False, "no_log": True},
        "enabled": {"type": "list", "elements": "str", "required": False},
        "disabled": {"type": "list", "elements": "str", "required": False},
    }

    result: dict[str, Any] = {"changed": False}

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ["state", "attached", ["token"]],
        ],
    )

    pro: str = module.get_bin_path("pro", required=True)  # pyright: ignore[reportUnknownVariableType, reportAssignmentType, reportUnknownMemberType]

    state: str | None = module.params.get("state")
    token: str | None = module.params.get("token")
    enabled: list[str] = module.params.get("enabled") or []
    disabled: list[str] = module.params.get("disabled") or []

    if state == "detached" and (enabled or disabled):
        module.fail_json(msg="enabled/disabled cannot be used with state=detached")  # pyright: ignore[reportUnknownMemberType]

    status = _get_status(module, pro)
    result["status"] = status

    attached = _status_attached(status)

    attach_needed = (state == "attached" or enabled or disabled) and not attached
    if attach_needed and not token:
        module.fail_json(msg="token is required to attach the system")  # pyright: ignore[reportUnknownMemberType]

    detach_needed = state == "detached" and attached
    current_enabled = _collect_enabled_services(status)
    to_enable = [svc for svc in enabled if svc not in current_enabled]
    to_disable = [svc for svc in disabled if svc in current_enabled]

    if module.check_mode:
        changed = bool(attach_needed or detach_needed or to_enable or to_disable)
        result["changed"] = changed

        if to_enable:
            result["enabled"] = to_enable

        if to_disable:
            result["disabled"] = to_disable

        module.exit_json(**result)  # pyright: ignore[reportUnknownMemberType]

    changed = False

    if detach_needed:
        changed |= _maybe_detach(module, pro, result)

    elif attach_needed and token:
        changed |= _maybe_attach(module, pro, token, result)
        status = _get_status(module, pro)
        result["status"] = status
        current_enabled = _collect_enabled_services(status)
        to_enable = [svc for svc in enabled if svc not in current_enabled]
        to_disable = [svc for svc in disabled if svc in current_enabled]

    if to_enable:
        changed |= _maybe_enable_services(module, pro, to_enable, result)

    if to_disable:
        changed |= _maybe_disable_services(module, pro, to_disable, result)

    if changed:
        result["status"] = _get_status(module, pro)

    result["changed"] = changed
    module.exit_json(**result)  # pyright: ignore[reportUnknownMemberType]


if __name__ == "__main__":
    main()
