"""Settings daemon for SigmaOS-daemon-settings (cinnamon-settings-daemon).

Manages fonts, themes and hotkeys as pure plan/apply over an injected
settings dict (the daemon's backing store is hidden behind get/set).
Applying is idempotent; hotkey conflicts are detected fail-fast.
"""
import argparse, json, sys

ENGINE = {
    "name": "sigma-settingsd",
    "summary": "Plan font, theme and hotkey settings idempotently",
    "language": "python",
    "verbs": ["font", "theme", "hotkey", "dump"],
    "principles": ["Idempotence", "Fail-Fast", "Least Astonishment",
                   "Information Hiding", "KISS", "Deterministic Testing"],
}

cli_doc = """\
$ sigma-settingsd font --name "Inter 11" --mono "JetBrains Mono 10" --dpi 96
$ sigma-settingsd theme --gtk Adwaita-dark --icons Papirus --cursor Bibata
$ sigma-settingsd hotkey --binding "<Super>t" --action terminal.launch
$ sigma-settingsd hotkey --list
$ sigma-settingsd dump --format json
"""

FONT_SIZE_RE = r"^(?P<face>.+?)\s+(?P<size>\d{1,3})(?:\.(?P<scale>5|0))?$"
VALID_SCALING = ("1", "2")
BINDING_RE = r"^((<\w+>)\+?)*[\w-]+$"


class SettingsError(Exception):
    pass


def parse_font(spec):
    """Pure: 'Inter 11.5' -> {face, size, scale_percent}."""
    import re
    m = re.match(FONT_SIZE_RE, spec.strip())
    if not m:
        raise SettingsError(f"bad font spec {spec!r}; expected 'Face SIZE[.5]'")
    size = int(m.group("size"))
    if not (6 <= size <= 72):
        raise SettingsError(f"font size {size} out of range 6-72")
    scale = 100 if m.group("scale") is None else 150
    return {"face": m.group("face"), "size": size, "scale_percent": scale}


def _get(store, dotted):
    """Nested lookup for dotted keys; None when any level is missing."""
    node = store
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def plan_font(store, name=None, mono=None, dpi=None):
    """Pure: diff desired font settings against the store -> plan steps."""
    steps = []
    if name is not None:
        font = parse_font(name)
        if _get(store, "font.interface") != name:
            steps.append({"key": "font.interface",
                          "from": _get(store, "font.interface"),
                          "to": name, "font": font})
    if mono is not None:
        font = parse_font(mono)
        if _get(store, "font.mono") != mono:
            steps.append({"key": "font.mono", "from": _get(store, "font.mono"),
                          "to": mono, "font": font})
    if dpi is not None:
        if not (72 <= dpi <= 240):
            raise SettingsError(f"dpi {dpi} out of range 72-240")
        if _get(store, "font.dpi") != dpi:
            steps.append({"key": "font.dpi", "from": _get(store, "font.dpi"),
                          "to": dpi})
    return steps


THEME_KEYS = {"gtk": "theme.gtk", "icons": "theme.icons",
              "cursor": "theme.cursor", "name": "theme.name"}


def plan_theme(store, **desired):
    """Pure: diff theme selections; values must be sane identifiers."""
    steps = []
    for flag, key in THEME_KEYS.items():
        value = desired.get(flag)
        if value is None:
            continue
        if not value or not all(c.isalnum() or c in "-_." for c in value):
            raise SettingsError(f"bad theme name {value!r}")
        if _get(store, key) != value:
            steps.append({"key": key, "from": _get(store, key), "to": value})
    return steps


def normalize_binding(binding):
    """Pure: canonicalize '<Super>t' style bindings for comparison."""
    import re
    binding = "".join(binding.split())
    if not binding or not re.match(BINDING_RE, binding):
        raise SettingsError(f"bad key binding {binding!r}")
    key_part = re.sub(r"<[^>]+>\+?", "", binding)
    if not key_part:
        raise SettingsError(
            f"bad key binding {binding!r}: needs a non-modifier key")
    return binding.lower()


def plan_hotkey(store, binding, action):
    """Pure: bind action to key; fail-fast if the key chord is taken."""
    norm = normalize_binding(binding)
    existing = store.get("hotkeys", {})
    for act, bound in existing.items():
        if normalize_binding(bound) == norm and act != action:
            raise SettingsError(
                f"binding {binding} already used by {act}; pick another chord")
    if existing.get(action) == norm:
        return []  # idempotent: nothing to do
    return [{"key": f"hotkeys.{action}", "from": existing.get(action),
             "to": norm, "binding": binding}]


def apply_steps(store, steps):
    """Pure mutation: apply planned steps to the store (idempotent)."""
    for step in steps:
        key = step["key"]
        node = store
        if key.startswith("hotkeys."):
            # action ids may themselves contain dots: treat the rest as one key
            parts = ["hotkeys", key[len("hotkeys."):]]
        else:
            parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = step["to"]
    return store


def dump(store, fmt="text"):
    """Render the store deterministically."""
    if fmt == "json":
        return json.dumps(store, indent=2, sort_keys=True)
    lines = []
    for key in sorted(_flatten(store)):
        lines.append(f"{key} = {_flatten(store)[key]}")
    return "\n".join(lines)


def _flatten(node, prefix=""):
    out = {}
    for k in sorted(node):
        key = f"{prefix}.{k}" if prefix else k
        v = node[k]
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog=ENGINE["name"], description=ENGINE["summary"])
    p.add_argument("--store", default=None, help="JSON settings store file")
    sub = p.add_subparsers(dest="cmd", required=True)
    fo = sub.add_parser("font", help="plan font settings")
    fo.add_argument("--name", default=None, help="interface font, e.g. 'Inter 11'")
    fo.add_argument("--mono", default=None)
    fo.add_argument("--dpi", type=int, default=None)
    fo.add_argument("--apply", action="store_true")
    th = sub.add_parser("theme", help="plan theme settings")
    th.add_argument("--gtk", default=None)
    th.add_argument("--icons", default=None)
    th.add_argument("--cursor", default=None)
    th.add_argument("--name", default=None)
    th.add_argument("--apply", action="store_true")
    hk = sub.add_parser("hotkey", help="plan or list hotkey bindings")
    hk.add_argument("--binding", default=None, help="e.g. '<Super>t'")
    hk.add_argument("--action", default=None, help="action id, e.g. terminal.launch")
    hk.add_argument("--list", action="store_true", dest="list_only")
    hk.add_argument("--apply", action="store_true")
    du = sub.add_parser("dump", help="print all settings")
    du.add_argument("--format", default="text", choices=["text", "json"])
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    store = {}
    if args.store:
        try:
            with open(args.store) as fh:
                store = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            print(f"error: cannot load store: {e}", file=sys.stderr)
            return 1
    try:
        if args.cmd == "font":
            steps = plan_font(store, args.name, args.mono, args.dpi)
        elif args.cmd == "theme":
            steps = plan_theme(store, gtk=args.gtk, icons=args.icons,
                               cursor=args.cursor, name=args.name)
        elif args.cmd == "hotkey":
            if args.list_only or not (args.binding and args.action):
                for act, bound in sorted(store.get("hotkeys", {}).items()):
                    print(f"{bound} -> {act}")
                return 0
            steps = plan_hotkey(store, args.binding, args.action)
        elif args.cmd == "dump":
            print(dump(store, args.format))
            return 0
        for s in steps:
            print(f"{s['key']}: {s.get('from')!r} -> {s['to']!r}")
        print(f"{len(steps)} change(s)")
        if getattr(args, "apply", False) and steps:
            apply_steps(store, steps)
            if args.store:
                with open(args.store, "w") as fh:
                    json.dump(store, fh, indent=2, sort_keys=True)
            print("applied")
        return 0
    except SettingsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def self_test() -> None:
    # fonts
    f = parse_font("Inter 11")
    assert f == {"face": "Inter", "size": 11, "scale_percent": 100}
    f2 = parse_font("JetBrains Mono 10.5")
    assert f2 == {"face": "JetBrains Mono", "size": 10, "scale_percent": 150}
    for bad in ("Inter", "Inter 0", "Inter 999", ""):
        try:
            parse_font(bad)
        except SettingsError:
            pass
        else:
            raise AssertionError(f"font not rejected: {bad!r}")

    store = {"font": {"interface": "Cantarell 11", "dpi": 96},
             "theme": {"gtk": "Adwaita", "icons": "Adwaita"},
             "hotkeys": {"terminal.launch": "<super>t",
                         "launcher.launch": "<super>space"}}

    steps = plan_font(store, name="Inter 11", dpi=96)
    assert len(steps) == 1 and steps[0]["key"] == "font.interface"
    assert steps[0]["from"] == "Cantarell 11"
    assert plan_font(store, name="Cantarell 11", dpi=96) == []  # idempotent
    assert plan_font(store, dpi=120)[0]["to"] == 120
    try:
        plan_font(store, dpi=300)
    except SettingsError:
        pass
    else:
        raise AssertionError("bad dpi not caught")

    # themes
    steps = plan_theme(store, gtk="Adwaita-dark", icons="Papirus", cursor="Bibata")
    assert [s["key"] for s in steps] == ["theme.gtk", "theme.icons", "theme.cursor"]
    assert plan_theme(store, gtk="Adwaita") == []  # unchanged
    try:
        plan_theme(store, gtk="bad name!")
    except SettingsError:
        pass
    else:
        raise AssertionError("bad theme name not caught")

    # hotkeys
    try:
        normalize_binding("<Super>")
    except SettingsError:
        pass
    else:
        raise AssertionError("bare modifier not caught")
    try:
        normalize_binding("Ctrl+")
    except SettingsError:
        pass
    else:
        raise AssertionError("trailing plus not caught")
    assert normalize_binding("<Super>  T") == "<super>t"
    try:
        plan_hotkey(store, "<Super>t", "files.launch")
    except SettingsError as e:
        assert "terminal.launch" in str(e)
    else:
        raise AssertionError("hotkey conflict not caught")
    # rebinding the same action to the same chord is a no-op
    assert plan_hotkey(store, "<Super>t", "terminal.launch") == []
    new_steps = plan_hotkey(store, "<Super>Return", "terminal.launch")
    assert new_steps[0]["from"] == "<super>t"

    # apply is pure + idempotent
    mutated = json.loads(json.dumps(store))
    apply_steps(mutated, new_steps)
    assert mutated["hotkeys"]["terminal.launch"] == "<super>return"
    assert apply_steps(mutated, new_steps) == mutated

    # dump
    text = dump(store)
    assert "font.interface = Cantarell 11" in text
    assert text.index("font.dpi") < text.index("theme.gtk")  # sorted
    parsed = json.loads(dump(store, "json"))
    assert parsed == store


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
