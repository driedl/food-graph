#!/bin/bash
# Cleanup script to remove rejected food mappings and their associated nutrient data

set -e

EVIDENCE_FILE="data/evidence/fdc-foundation/evidence_mappings.jsonl"
NUTRIENT_FILE="data/evidence/fdc-foundation/nutrient_data.jsonl"

echo "🔍 Finding rejected food IDs..."

# Get rejected food IDs
REJECTED_IDS=$(grep '"rejected"' $EVIDENCE_FILE | jq -r '.food_id' | sort -u)

if [ -z "$REJECTED_IDS" ]; then
    echo "✅ No rejected foods found"
    exit 0
fi

echo "Found rejected food IDs:"
echo "$REJECTED_IDS"
echo ""

# Confirm deletion
echo "⚠️  This will remove:"
echo "   - Rejected evidence mappings"
echo "   - Associated nutrient data rows"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 1
fi

# Backup files
echo "📦 Creating backups..."
cp $EVIDENCE_FILE "$EVIDENCE_FILE.backup"
cp $NUTRIENT_FILE "$NUTRIENT_FILE.backup"
echo "✅ Backups created"

# Remove rejected evidence mappings
echo "🗑️  Removing rejected evidence mappings..."
grep -v '"rejected"' $EVIDENCE_FILE > "${EVIDENCE_FILE}.tmp"
mv "${EVIDENCE_FILE}.tmp" $EVIDENCE_FILE

# Remove nutrient data for rejected foods
echo "🗑️  Removing nutrient data for rejected foods..."
while IFS= read -r food_id; do
    grep -v "\"food_id\": \"$food_id\"" $NUTRIENT_FILE > "${NUTRIENT_FILE}.tmp"
    mv "${NUTRIENT_FILE}.tmp" $NUTRIENT_FILE
done <<< "$REJECTED_IDS"

# Count results
EVIDENCE_COUNT=$(wc -l < $EVIDENCE_FILE)
NUTRIENT_COUNT=$(wc -l < $NUTRIENT_FILE)

echo ""
echo "✅ Cleanup complete!"
echo "   Evidence mappings: $EVIDENCE_COUNT rows"
echo "   Nutrient data: $NUTRIENT_COUNT rows"
echo ""
echo "📦 Backups saved:"
echo "   - ${EVIDENCE_FILE}.backup"
echo "   - ${NUTRIENT_FILE}.backup"
echo ""
echo "🚀 Ready to re-run evidence mapping with: pnpm evidence:map --resume"

