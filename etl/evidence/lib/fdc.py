from __future__ import annotations
import csv, re
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Any

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

_COOKED_RE = re.compile(r"(?i)\b(cooked|braised|fried|grilled|baked|roasted|toasted|boiled|steamed|prepared|heated)\b")
_CANNED_RE = re.compile(r"(?i)\b(canned|jarred|retort|brine|pickl)\w*")
_MIXTURE_RE = re.compile(r"(?i)\b(hummus|salsa|sauce|gravy|soup|stew|marinara|ketchup|mustard|spread|dip|salad|pasta\s+sauce)\b")
_ADDED_RE = re.compile(r"(?i)(with\s+salt|salt\s+added|sweeten\w*|sugar\s+added|with\s+oil|vitamin\s+|fortifi\w+|iodized)")
_DERIVATIVE_TOKENS = ("flour","meal","semolina","oil","salt","sugar","butter","tahini","masa")
_RAW_HINT = re.compile(r"(?i)\b(raw|fresh)\b")

_EXCLUDE_CATEGORIES = {
    "baked products",
    "restaurant foods",
    "soups, sauces, and gravies",
    "sausages and luncheon meats",
    "sweets",
    "beverages",
}

def _is_allowed_seed_butter(desc: str) -> bool:
    """
    Allow seed/nut butter only if no additive hints.
    Accepts tahini/"sesame butter, creamy" when no salt/sugar/oil/fortification tokens found.
    """
    d = desc.lower()
    if "butter" not in d and "tahini" not in d:
        return False
    if _ADDED_RE.search(d):
        return False
    # Prefer clear seed context
    return ("tahini" in d) or ("sesame" in d) or ("peanut" in d) or ("almond" in d) or ("cashew" in d)

def is_base_food_record(rec: Dict[str, Any], include_derived: bool = False) -> bool:
    name = (rec.get("description") or "").lower()
    cat  = (rec.get("category") or "").lower()

    # hard category excludes
    if any(c in cat for c in _EXCLUDE_CATEGORIES):
        return False

    # mixtures and obvious processed states
    if _MIXTURE_RE.search(name):
        return False

    # dairy derived products (cheese, yogurt, cottage, cream) are excluded in base pass
    if "dairy and egg products" in cat:
        # eggs may be raw whole/white/yolk only
        if "egg" in name and _RAW_HINT.search(name) and not _CANNED_RE.search(name):
            return True
        return False

    # vegetables/fruits: prefer raw fresh whole parts; exclude canned/pickled/juiced/sauced/dried by default
    if "vegetables and vegetable products" in cat or "fruits and fruit juices" in cat:
        if _CANNED_RE.search(name) or "juice" in name or "sauce" in name or "dried" in name or "pickles" in name:
            return False
        return "raw" in name or not _COOKED_RE.search(name)

    # fish/shellfish: require raw & not canned
    if "finfish and shellfish products" in cat:
        return ("raw" in name) and not _CANNED_RE.search(name)

    # meats: beef/pork/lamb/poultry — require raw & not cured/smoked
    if any(k in cat for k in ("beef products","pork products","lamb, veal, and game products","poultry products")):
        if _COOKED_RE.search(name):
            return False
        if re.search(r"(?i)\b(cured|smoked|bacon|ham|frankfurter|sausage)\b", name):
            return False
        return "raw" in name or not _COOKED_RE.search(name)

    # nuts & seeds: allow raw; roasted/salted excluded. Seed/nut butters allowed only if additive-free AND include_derived
    if "nut and seed products" in cat:
        if "roast" in name or "salt" in name:
            return False
        if "butter" in name or "tahini" in name:
            return include_derived and _is_allowed_seed_butter(name)
        return True

    # cereals & grains: allow whole grains; flours/meals only if include_derived
    if "cereal grains and pasta" in cat:
        if any(tok in name for tok in ("flour","meal","semolina","masa","00")):
            return include_derived
        # polished/pearled grains are okay as base TP transforms; keep them
        return not _COOKED_RE.search(name)

    # fats & oils: only if include_derived (single-ingredient derivative)
    if "fats and oils" in cat:
        return include_derived and not _ADDED_RE.search(name)

    # spices/herbs: usually okay as base; but "iodized salt" only if include_derived
    if "spices and herbs" in cat:
        if "salt" in name:
            return include_derived
        return True

    # everything else: default to False in base pass
    return False

def filter_base_foods(records: List[Dict[str, Any]], include_derived: bool = False) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in records:
        if is_base_food_record(r, include_derived=include_derived):
            out.append(r)
    return out

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
