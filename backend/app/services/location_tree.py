"""
Location Tree Builder

Transforms flat inventory_location records into a nested JSON tree
following the hierarchy: Warehouse > Section > Zone > Aisle > Rack > Bin.

WHY this exists:
    The frontend needs a nested tree structure for warehouse location
    navigation (expandable sidebar / drill-down views).  The database
    stores locations flat (one row per bin).  This service bridges the
    two representations efficiently.

Orphan Management:
    Locations with a gap in their hierarchy (e.g. zone is set but section
    is NULL) are detected during tree construction.  At the section level,
    any location with section=NULL is grouped under a virtual "Unassigned"
    node appended to the end of the warehouse's children list.  This node
    has type="unassigned" and is_virtual=True so the frontend can render
    it distinctly.  Deeper-level gaps (zone=NULL, aisle=NULL, etc.) are
    flagged with is_orphan=True on the individual node.

Performance — optimised for up to 5,000+ locations:
    Phase 1: Single O(n) pass builds a nested dict tree via setdefault().
             Each location is visited exactly once; dict lookups are O(1).
    Phase 2: Single O(n) bottom-up walk to compute total_locations at
             every node (propagates leaf counts upward).
    Phase 3: Single O(n) walk converts the internal dict tree into the
             output JSON list structure with summaries.

    Total: O(n) time, O(n) space.  No repeated key scans.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract(obj: Any, key: str) -> Any:
    """Extract a value from a dict or an ORM object."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _norm(val: Any) -> str:
    """Normalise a hierarchy value to a non-None string."""
    if val is None:
        return ""
    s = str(val).strip()
    return s


def _display(val: str) -> str:
    """Human-readable label; 'Unassigned' for empty strings."""
    return val if val else "Unassigned"


def _plural(n: int) -> str:
    return "s" if n != 1 else ""


# ---------------------------------------------------------------------------
# Internal tree node type
# ---------------------------------------------------------------------------
# During Phase 1, the tree is built as nested dicts:
#
#   _tree[wh_id] = {
#       "__name": str,
#       "__children": {
#           section_key: {
#               "__children": {
#                   zone_key: { ... }
#               }
#           }
#       }
#   }
#
# Leaf level (bins) are stored as:
#   rack_node["__bins"] = [{"name": ..., "location_id": ..., ...}, ...]
#
# After Phase 2, every node also has "__total_locations" (int).


def build_location_tree(
    locations: list[Any],
    *,
    warehouse_names: dict[int | str, str] | None = None,
    include_location_id: bool = True,
) -> list[dict[str, Any]]:
    """
    Transform flat inventory_location objects into a nested JSON tree.

    Hierarchy: Warehouse > Section > Zone > Aisle > Rack > Bin.

    Args:
        locations: List of flat location records (dicts or ORM objects
            with warehouse_id, section, zone, aisle, rack, bin fields).
        warehouse_names: Optional mapping of warehouse_id -> display name.
            Falls back to "Warehouse {id}" when missing.
        include_location_id: If True, leaf (bin) nodes include the DB id.

    Returns:
        List of warehouse root nodes.  Each node has:
            name, type, summary, total_locations, children.
        Leaf (bin) nodes additionally carry location_id and display_code.

    Performance:
        O(n) time — one pass to build, one pass to count, one pass to
        format.  Handles 5,000+ locations without noticeable delay.
    """
    if not locations:
        return []

    warehouse_names = warehouse_names or {}

    # ------------------------------------------------------------------
    # Phase 1: Single-pass tree construction  [O(n)]
    # ------------------------------------------------------------------
    # _tree maps warehouse_id -> internal node dict.
    _tree: dict[str, dict[str, Any]] = {}

    for loc in locations:
        wh_raw = _extract(loc, "warehouse_id")
        wh_key = str(wh_raw) if wh_raw is not None else ""
        sec = _norm(_extract(loc, "section"))
        zon = _norm(_extract(loc, "zone"))
        ais = _norm(_extract(loc, "aisle"))
        rac = _norm(_extract(loc, "rack"))
        bn = _norm(_extract(loc, "bin"))

        # Drill into / create each level using setdefault — O(1) per level
        wh_node = _tree.setdefault(wh_key, {"__children": {}})
        sec_node = wh_node["__children"].setdefault(sec, {"__children": {}})
        zon_node = sec_node["__children"].setdefault(zon, {"__children": {}})
        ais_node = zon_node["__children"].setdefault(ais, {"__children": {}})
        rac_node = ais_node["__children"].setdefault(rac, {"__bins": []})

        # Build the leaf bin record
        bin_data: dict[str, Any] = {"name": _display(bn)}
        if include_location_id:
            lid = _extract(loc, "id")
            if lid is not None:
                bin_data["location_id"] = lid
        dc = _extract(loc, "display_code")
        if dc:
            bin_data["display_code"] = dc
        is_active = _extract(loc, "is_active")
        if is_active is not None:
            bin_data["is_active"] = is_active
        sort_order = _extract(loc, "sort_order")
        if sort_order is not None:
            bin_data["sort_order"] = sort_order

        rac_node["__bins"].append(bin_data)

    # ------------------------------------------------------------------
    # Phase 2: Bottom-up total_locations count  [O(n)]
    # ------------------------------------------------------------------
    # Walk the tree and propagate leaf counts upward.

    def _count_recursive(node: dict[str, Any]) -> int:
        """Set __total on this node and return total leaf count."""
        if "__bins" in node:
            # Rack level — bins are the leaves
            total = len(node["__bins"])
            node["__total"] = total
            return total

        children = node.get("__children", {})
        total = 0
        for child in children.values():
            total += _count_recursive(child)
        node["__total"] = total
        return total

    for wh_node in _tree.values():
        _count_recursive(wh_node)

    # ------------------------------------------------------------------
    # Phase 3: Format into output JSON  [O(n)]
    # ------------------------------------------------------------------
    _CHILD_LABEL = {
        "warehouse": "section",
        "section": "zone",
        "zone": "aisle",
        "aisle": "rack",
        "rack": "bin",
    }

    def _format_rack(key: str, node: dict[str, Any]) -> dict[str, Any]:
        """Format a rack node (its children are bin leaves)."""
        bins = node.get("__bins", [])
        total = node.get("__total", len(bins))
        out: dict[str, Any] = {
            "name": _display(key),
            "type": "rack",
            "total_locations": total,
            "summary": f"Rack {_display(key)} contains {total} bin{_plural(total)}",
            "children": [
                {
                    "name": b["name"],
                    "type": "bin",
                    **{k: v for k, v in b.items() if k != "name"},
                    "summary": f"Bin {_display(b.get('name', ''))}",
                }
                for b in bins
            ],
        }
        if key == "":
            out["is_orphan"] = True
        return out

    def _format_branch(
        key: str,
        node: dict[str, Any],
        level_type: str,
    ) -> dict[str, Any]:
        """Format a branch node (warehouse, section, zone, or aisle)."""
        children_dict = node.get("__children", {})
        total = node.get("__total", 0)
        child_type = _CHILD_LABEL.get(level_type, "child")
        direct_count = len(children_dict)

        # Summary uses total bin count for immediate clarity:
        # "Aisle A01 contains 20 bins" (not "3 racks")
        summary = (
            f"{level_type.capitalize()} {_display(key)} contains "
            f"{total} location{_plural(total)}"
        )

        # Determine if children are racks (leaf parents) or branches
        child_nodes: list[dict[str, Any]] = []
        next_type = _CHILD_LABEL.get(level_type, "")

        for child_key in sorted(children_dict.keys(), key=lambda x: (x == "", x)):
            child_node = children_dict[child_key]
            if next_type == "rack":
                # Children are rack nodes (which hold __bins, not __children)
                child_nodes.append(_format_rack(child_key, child_node))
            else:
                child_nodes.append(_format_branch(child_key, child_node, next_type))

        out: dict[str, Any] = {
            "name": _display(key),
            "type": level_type,
            "total_locations": total,
            "summary": summary,
            "children": child_nodes,
        }
        if key == "":
            out["is_orphan"] = True
        return out

    # Build root list (one entry per warehouse)
    roots: list[dict[str, Any]] = []

    for wh_key in sorted(_tree.keys()):
        wh_node = _tree[wh_key]

        # Resolve display name
        try:
            wh_id_int = int(wh_key)
        except (ValueError, TypeError):
            wh_id_int = wh_key  # type: ignore[assignment]
        display_name = warehouse_names.get(
            wh_id_int,
            warehouse_names.get(wh_key, f"Warehouse {wh_key}" if wh_key else "Warehouse (unspecified)"),
        )

        total = wh_node.get("__total", 0)
        sections = wh_node.get("__children", {})

        # Separate normal sections from orphans (section key == "")
        # WHY: Locations with section=NULL but deeper levels set are
        #      "orphans" — they have no parent section.  Grouping them
        #      under a virtual "Unassigned" node keeps the tree clean
        #      and lets the frontend render them distinctly.
        normal_section_nodes: list[dict[str, Any]] = []
        orphan_section_node: dict[str, Any] | None = None

        for sec_key in sorted(sections.keys(), key=lambda x: (x == "", x)):
            if sec_key == "":
                # Orphan: section is NULL — group under virtual "Unassigned"
                orphan_data = sections[sec_key]
                orphan_total = orphan_data.get("__total", 0)

                # Build children of the orphan node (zones within the NULL section)
                orphan_children: list[dict[str, Any]] = []
                orphan_child_dict = orphan_data.get("__children", {})
                for child_key in sorted(orphan_child_dict.keys(), key=lambda x: (x == "", x)):
                    child_node = orphan_child_dict[child_key]
                    orphan_children.append(_format_branch(child_key, child_node, "zone"))

                orphan_section_node = {
                    "name": "Unassigned",
                    "type": "unassigned",
                    "is_virtual": True,
                    "is_orphan": True,
                    "total_locations": orphan_total,
                    "summary": (
                        f"Unassigned contains {orphan_total} "
                        f"orphaned location{_plural(orphan_total)}"
                    ),
                    "children": orphan_children,
                }
            else:
                normal_section_nodes.append(
                    _format_branch(sec_key, sections[sec_key], "section")
                )

        # Count only normal sections for the summary (orphans are separate)
        section_count = len(normal_section_nodes)
        section_nodes = normal_section_nodes

        # Append the virtual "Unassigned" node at the end if orphans exist
        if orphan_section_node is not None:
            section_nodes.append(orphan_section_node)

        roots.append({
            "name": display_name,
            "type": "warehouse",
            "total_locations": total,
            "summary": (
                f"Warehouse {display_name} contains "
                f"{total} location{_plural(total)} across "
                f"{section_count} section{_plural(section_count)}"
            ),
            "children": section_nodes,
        })

    return roots
