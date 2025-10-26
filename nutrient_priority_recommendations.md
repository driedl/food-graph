# FDC Nutrient Priority Recommendations

## Analysis Summary
- **Total FDC nutrients**: 477
- **Currently mapped**: 172 (36%)
- **Unmapped**: 391 (64%)

## Priority 1: HIGH PRIORITY - Add These Essential Nutrients

### Vitamin K Variants (High Frequency)
- **FDC 1184**: Vitamin K (Dihydrophylloquinone) - 512 foods
- **FDC 1183**: Vitamin K (Menaquinone-4) - 438 foods

### Dietary Fiber Subtypes (Important for Nutrition)
- **FDC 2038**: High Molecular Weight Dietary Fiber (HMWDF) - 171 foods
- **FDC 2065**: Low Molecular Weight Dietary Fiber (LMWDF) - 171 foods

### Folate Variants (Important for Health)
- **FDC 1188**: 5-methyl tetrahydrofolate (5-MTHF) - 98 foods

### Trans Fat Subtypes (Important for Health)
- **FDC 1329**: Fatty acids, total trans-monoenoic - 78 foods
- **FDC 1330**: Fatty acids, total trans-dienoic - 70 foods
- **FDC 1331**: Fatty acids, total trans-polyenoic - 37 foods

## Priority 2: MEDIUM PRIORITY - Important Amino Acids & Carotenoids

### Essential Amino Acids (High Frequency)
- **FDC 1210**: Tryptophan - 433 foods
- **FDC 1214**: Lysine - 433 foods
- **FDC 1215**: Methionine - 433 foods
- **FDC 1232**: Cysteine - 241 foods

### Important Carotenoids (High Frequency)
- **FDC 1122**: Lycopene - 293 foods
- **FDC 1161**: cis-Lutein/Zeaxanthin - 191 foods
- **FDC 1123**: Lutein + zeaxanthin - 170 foods
- **FDC 1119**: Zeaxanthin - 151 foods

## Priority 3: LOW PRIORITY - Specialized Nutrients

### Common Fatty Acid Subtypes (High Frequency but Specialized)
- **FDC 1002**: Nitrogen - 3593 foods (not nutritionally relevant)
- **FDC 1265**: SFA 16:0 - 1168 foods
- **FDC 1266**: SFA 18:0 - 1168 foods
- **FDC 1264**: SFA 14:0 - 1132 foods
- **FDC 1315**: MUFA 18:1 c - 1057 foods
- **FDC 1075**: Galactose - 936 foods

## Priority 4: IGNORE - Rare or Archived

### Archived/Deprecated (0 foods)
- FDC 1006: Fiber, crude (DO NOT USE - Archived)
- FDC 1066: Fiber, neutral detergent (DO NOT USE - Archived)
- FDC 1148: Fluoride - DO NOT USE

### Rare Nutrients (Low frequency, specialized)
- Most nutrients with <100 occurrences
- Specialized sterols, ergothioneine, etc.

## Recommendations

### Immediate Action (Priority 1)
Add the 8 high-priority nutrients to `nutrients.json`:
1. Vitamin K variants (2 nutrients)
2. Dietary fiber subtypes (2 nutrients) 
3. Folate variant (1 nutrient)
4. Trans fat subtypes (3 nutrients)

### Future Consideration (Priority 2)
Consider adding amino acids and carotenoids if comprehensive coverage is needed.

### Skip (Priority 3 & 4)
The remaining nutrients are either:
- Not nutritionally relevant (Nitrogen)
- Too specialized for general nutrition ontology
- Archived/deprecated
- Rare/experimental

## Impact Assessment
Adding Priority 1 nutrients would:
- Cover 8 additional essential nutrients
- Improve coverage for 1,000+ food entries
- Maintain focus on nutritionally relevant compounds
- Keep ontology manageable and focused
