from __future__ import annotations
import csv, re
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

# Minimal CSV helpers (avoid pandas for the POC)
def _read_csv(path: Path) -> Iterator[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            yield {k: (v or "").strip() for k, v in row.items()}

DEFAULT_PROCESSED_REGEX = re.compile(
    r"""(?xi)
    sandwich|burger|pizza|soup|stew|chili|casserole|lasagna|dumpling|
    cereal|granola|cookie|cracker|cake|brownie|muffin|doughnut|pastry|
    fries|chips|snack|candy|bar\b|sauce|dressing|ketchup|mayonnaise|
    marinade|seasoning|spice\s+mix|gravy|
    burrito|taco|quesadilla|enchilada|
    frozen\s+meal|microwave|instant\b|prepared|ready\s*to\s*eat|
    beverage|soda|cola|sports\s*drink|energy\s*drink|alcohol|beer|wine
    """
)

def looks_processed(name: str) -> bool:
    return bool(DEFAULT_PROCESSED_REGEX.search(name.lower()))

def load_foundation_foods_json(fdc_dir: Path,
                               categories_skip: Optional[List[str]] = None,
                               limit: int = 0) -> List[Dict[str, Any]]:
    """
    Load foundation foods from the pre-filtered foundation-foods.json file.
    Returns list of foods with fdc_id, description, and category.
    """
    foundation_json = fdc_dir / "foundation-foods.json"
    if not foundation_json.exists():
        raise FileNotFoundError(f"Missing {foundation_json}")
    
    import json
    with foundation_json.open("r", encoding="utf-8") as f:
        foods = json.load(f)
    
    # Apply category filtering
    if categories_skip:
        filtered_foods = []
        for food in foods:
            cat_name = food.get("category", "")
            skip_by_cat = any(c.lower() in cat_name.lower() for c in categories_skip)
            # Fallback name heuristic
            name = food.get("description", "")
            if skip_by_cat or looks_processed(name):
                continue
            filtered_foods.append(food)
            if limit and len(filtered_foods) >= limit:
                break
        return filtered_foods
    
    # No filtering, just apply limit
    if limit and limit > 0:
        return foods[:limit]
    return foods

def load_foundation_foods(fdc_dir: Path,
                          only_foundation: bool = True,
                          categories_skip: Optional[List[str]] = None,
                          limit: int = 0) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
    """
    Returns (foods, categories_by_id). Filters to FOUNDATION foods and skips items
    that look obviously processed based on category or name.
    """
    food_csv = fdc_dir / "food.csv"
    food_cat_csv = fdc_dir / "food_category.csv"
    if not food_csv.exists():
        raise FileNotFoundError(f"Missing {food_csv}")
    categories: Dict[str, str] = {}
    if food_cat_csv.exists():
        for row in _read_csv(food_cat_csv):
            categories[row.get("id", "")] = row.get("wweia_food_category_description") or row.get("description") or ""

    foods: List[Dict[str, str]] = []
    for row in _read_csv(food_csv):
        dt = (row.get("data_type") or "")
        if only_foundation and dt.lower() != "foundation":
            continue
        # Skip processed by category if we have it
        cat_id = row.get("food_category_id") or ""
        cat_name = categories.get(cat_id, "")
        skip_by_cat = False
        if categories_skip:
            skip_by_cat = any(c.lower() in cat_name.lower() for c in categories_skip)
        # Fallback name heuristic
        name = row.get("description") or ""
        if skip_by_cat or looks_processed(name):
            continue
        foods.append(row)
        if limit and len(foods) >= limit:
            break
    return foods, categories

def filter_nutrients_for_foods(fdc_dir: Path, keep_fdc_ids: Iterable[str]) -> List[Dict[str, str]]:
    """Return food_nutrient rows restricted to the given FDC IDs."""
    fn_csv = fdc_dir / "food_nutrient.csv"
    if not fn_csv.exists():
        raise FileNotFoundError(f"Missing {fn_csv}")
    keep = set(keep_fdc_ids)
    out: List[Dict[str, str]] = []
    for row in _read_csv(fn_csv):
        if (row.get("fdc_id") or "") in keep:
            out.append(row)
    return out

def load_nutrient_index(fdc_dir: Path) -> Dict[str, Dict[str, str]]:
    """Return {nutrient_id: row} from nutrient.csv."""
    n_csv = fdc_dir / "nutrient.csv"
    if not n_csv.exists():
        raise FileNotFoundError(f"Missing {n_csv}")
    out: Dict[str, Dict[str, str]] = {}
    for row in _read_csv(n_csv):
        nid = row.get("id") or ""
        if nid:
            out[nid] = row
    return out
