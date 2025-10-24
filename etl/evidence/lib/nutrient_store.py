#!/usr/bin/env python3
"""
Nutrient Storage System

Handles storage and retrieval of nutrient data using the nutrient_row table.
Provides functionality for storing FDC nutrient data and mapping to canonical nutrients.
"""

from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class NutrientRow:
    """Nutrient row data structure with original and converted values"""
    id: str
    food_id: str
    nutrient_id: str  # Canonical INFOODS ID
    amount: float  # Canonical converted amount
    unit: str  # Canonical unit
    original_amount: float  # Original FDC amount
    original_unit: str  # Original FDC unit
    original_nutrient_id: str  # Original FDC nutrient ID
    conversion_factor: float  # Factor applied
    source: str
    confidence: float
    notes: Optional[str] = None
    created_at: Optional[str] = None
    nutrient_name: Optional[str] = None  # Human-readable nutrient name
    nutrient_class: Optional[str] = None  # Nutrient class (proximate, vitamin, etc.)

class NutrientStore:
    """Nutrient storage and retrieval system"""
    
    def __init__(self, db_path: Path):
        """Initialize with database path"""
        self.db_path = db_path
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def create_tables(self) -> None:
        """Create nutrient storage tables if they don't exist"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            # Create nutrient_row table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nutrient_row (
                    id TEXT PRIMARY KEY,
                    food_id TEXT NOT NULL,
                    nutrient_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    unit TEXT NOT NULL,
                    original_amount REAL NOT NULL,
                    original_unit TEXT NOT NULL,
                    original_nutrient_id TEXT NOT NULL,
                    conversion_factor REAL NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    notes TEXT,
                    created_at TEXT,
                    nutrient_name TEXT,
                    nutrient_class TEXT,
                    FOREIGN KEY (nutrient_id) REFERENCES nutrients(id)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_nutrient_row_food_id 
                ON nutrient_row(food_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_nutrient_row_nutrient_id 
                ON nutrient_row(nutrient_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_nutrient_row_source 
                ON nutrient_row(source)
            """)
            
            conn.commit()
    
    def store_nutrient_row(self, nutrient_row: NutrientRow) -> None:
        """Store a single nutrient row"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO nutrient_row 
                (id, food_id, nutrient_id, amount, unit, original_amount, original_unit, 
                 original_nutrient_id, conversion_factor, source, confidence, notes, created_at,
                 nutrient_name, nutrient_class)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nutrient_row.id,
                nutrient_row.food_id,
                nutrient_row.nutrient_id,
                nutrient_row.amount,
                nutrient_row.unit,
                nutrient_row.original_amount,
                nutrient_row.original_unit,
                nutrient_row.original_nutrient_id,
                nutrient_row.conversion_factor,
                nutrient_row.source,
                nutrient_row.confidence,
                nutrient_row.notes,
                nutrient_row.created_at or datetime.now().isoformat(),
                nutrient_row.nutrient_name,
                nutrient_row.nutrient_class
            ))
            
            conn.commit()
    
    def store_nutrient_rows(self, nutrient_rows: List[NutrientRow]) -> None:
        """Store multiple nutrient rows"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            for nutrient_row in nutrient_rows:
                cursor.execute("""
                    INSERT OR REPLACE INTO nutrient_row 
                    (id, food_id, nutrient_id, amount, unit, original_amount, original_unit, 
                     original_nutrient_id, conversion_factor, source, confidence, notes, created_at,
                     nutrient_name, nutrient_class)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nutrient_row.id,
                    nutrient_row.food_id,
                    nutrient_row.nutrient_id,
                    nutrient_row.amount,
                    nutrient_row.unit,
                    nutrient_row.original_amount,
                    nutrient_row.original_unit,
                    nutrient_row.original_nutrient_id,
                    nutrient_row.conversion_factor,
                    nutrient_row.source,
                    nutrient_row.confidence,
                    nutrient_row.notes,
                    nutrient_row.created_at or datetime.now().isoformat(),
                    nutrient_row.nutrient_name,
                    nutrient_row.nutrient_class
                ))
            
            conn.commit()
    
    def get_nutrient_rows_for_food(self, food_id: str) -> List[NutrientRow]:
        """Get all nutrient rows for a specific food"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, food_id, nutrient_id, amount, unit, original_amount, original_unit,
                       original_nutrient_id, conversion_factor, source, confidence, notes, created_at,
                       nutrient_name, nutrient_class
                FROM nutrient_row
                WHERE food_id = ?
                ORDER BY nutrient_id
            """, (food_id,))
            
            rows = cursor.fetchall()
            return [
                NutrientRow(
                    id=row[0],
                    food_id=row[1],
                    nutrient_id=row[2],
                    amount=row[3],
                    unit=row[4],
                    original_amount=row[5],
                    original_unit=row[6],
                    original_nutrient_id=row[7],
                    conversion_factor=row[8],
                    source=row[9],
                    confidence=row[10],
                    notes=row[11],
                    created_at=row[12],
                    nutrient_name=row[13],
                    nutrient_class=row[14]
                )
                for row in rows
            ]
    
    def get_nutrient_rows_by_nutrient(self, nutrient_id: str) -> List[NutrientRow]:
        """Get all nutrient rows for a specific nutrient"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, food_id, nutrient_id, amount, unit, original_amount, original_unit,
                       original_nutrient_id, conversion_factor, source, confidence, notes, created_at,
                       nutrient_name, nutrient_class
                FROM nutrient_row
                WHERE nutrient_id = ?
                ORDER BY food_id
            """, (nutrient_id,))
            
            rows = cursor.fetchall()
            return [
                NutrientRow(
                    id=row[0],
                    food_id=row[1],
                    nutrient_id=row[2],
                    amount=row[3],
                    unit=row[4],
                    original_amount=row[5],
                    original_unit=row[6],
                    original_nutrient_id=row[7],
                    conversion_factor=row[8],
                    source=row[9],
                    confidence=row[10],
                    notes=row[11],
                    created_at=row[12],
                    nutrient_name=row[13],
                    nutrient_class=row[14]
                )
                for row in rows
            ]
    
    def get_nutrient_rows_by_source(self, source: str) -> List[NutrientRow]:
        """Get all nutrient rows from a specific source"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, food_id, nutrient_id, amount, unit, original_amount, original_unit,
                       original_nutrient_id, conversion_factor, source, confidence, notes, created_at,
                       nutrient_name, nutrient_class
                FROM nutrient_row
                WHERE source = ?
                ORDER BY food_id, nutrient_id
            """, (source,))
            
            rows = cursor.fetchall()
            return [
                NutrientRow(
                    id=row[0],
                    food_id=row[1],
                    nutrient_id=row[2],
                    amount=row[3],
                    unit=row[4],
                    original_amount=row[5],
                    original_unit=row[6],
                    original_nutrient_id=row[7],
                    conversion_factor=row[8],
                    source=row[9],
                    confidence=row[10],
                    notes=row[11],
                    created_at=row[12],
                    nutrient_name=row[13],
                    nutrient_class=row[14]
                )
                for row in rows
            ]
    
    def delete_nutrient_rows_for_food(self, food_id: str) -> None:
        """Delete all nutrient rows for a specific food"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM nutrient_row
                WHERE food_id = ?
            """, (food_id,))
            
            conn.commit()
    
    def get_nutrient_summary(self, food_id: str) -> Dict[str, Any]:
        """Get nutrient summary for a food"""
        nutrient_rows = self.get_nutrient_rows_for_food(food_id)
        
        if not nutrient_rows:
            return {
                'food_id': food_id,
                'nutrient_count': 0,
                'sources': [],
                'avg_confidence': 0.0
            }
        
        sources = list(set(row.source for row in nutrient_rows))
        avg_confidence = sum(row.confidence for row in nutrient_rows) / len(nutrient_rows)
        
        return {
            'food_id': food_id,
            'nutrient_count': len(nutrient_rows),
            'sources': sources,
            'avg_confidence': avg_confidence,
            'nutrients': [
                {
                    'nutrient_id': row.nutrient_id,
                    'amount': row.amount,
                    'unit': row.unit,
                    'confidence': row.confidence
                }
                for row in nutrient_rows
            ]
        }
    
    def map_fdc_nutrients(self, fdc_nutrients: List[Dict[str, Any]], 
                         nutrient_mapping: Dict[str, str]) -> List[NutrientRow]:
        """Map FDC nutrients to canonical nutrients and create nutrient rows"""
        nutrient_rows = []
        
        for fdc_nutrient in fdc_nutrients:
            fdc_id = fdc_nutrient.get('fdc_id', fdc_nutrient.get('food_id', ''))
            nutrient_id = fdc_nutrient.get('nutrient_id', '')
            amount = float(fdc_nutrient.get('amount', 0))
            unit = fdc_nutrient.get('unit', 'g')
            
            # Map to canonical nutrient ID
            canonical_nutrient_id = nutrient_mapping.get(nutrient_id, nutrient_id)
            
            # Create nutrient row with original values (legacy method for backward compatibility)
            nutrient_row = NutrientRow(
                id=f"{fdc_id}_{canonical_nutrient_id}",
                food_id=fdc_id,
                nutrient_id=canonical_nutrient_id,
                amount=amount,
                unit=unit,
                original_amount=amount,
                original_unit=unit,
                original_nutrient_id=nutrient_id,
                conversion_factor=1.0,
                source='fdc_foundation',
                confidence=0.9,  # High confidence for FDC data
                notes=f"FDC nutrient: {nutrient_id}"
            )
            
            nutrient_rows.append(nutrient_row)
        
        return nutrient_rows
    
    def map_fdc_nutrients_with_mapper(self, fdc_nutrients: List[Dict[str, Any]], 
                                    nutrient_mapper) -> Tuple[List[NutrientRow], List[Any]]:
        """Map FDC nutrients using the comprehensive nutrient mapper"""
        nutrient_rows = []
        unmapped_nutrients = []
        
        for fdc_nutrient in fdc_nutrients:
            result = nutrient_mapper.map_fdc_nutrient(fdc_nutrient)
            if result.mapped:
                # Convert the nutrient row data to NutrientRow object
                nutrient_row = NutrientRow(
                    id=result.nutrient_row['id'],
                    food_id=result.nutrient_row['food_id'],
                    nutrient_id=result.nutrient_row['nutrient_id'],
                    amount=result.nutrient_row['amount'],
                    unit=result.nutrient_row['unit'],
                    original_amount=result.nutrient_row['original_amount'],
                    original_unit=result.nutrient_row['original_unit'],
                    original_nutrient_id=result.nutrient_row['original_nutrient_id'],
                    conversion_factor=result.nutrient_row['conversion_factor'],
                    source=result.nutrient_row['source'],
                    confidence=result.nutrient_row['confidence'],
                    notes=result.nutrient_row['notes'],
                    nutrient_name=result.nutrient_row.get('nutrient_name'),
                    nutrient_class=result.nutrient_row.get('nutrient_class')
                )
                nutrient_rows.append(nutrient_row)
            else:
                unmapped_nutrients.append(result.unmapped_info)
        
        return nutrient_rows, unmapped_nutrients
    
    def get_canonical_nutrients(self) -> List[Dict[str, Any]]:
        """Get canonical nutrients from the database"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, unit
                FROM nutrients
                ORDER BY id
            """)
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'unit': row[2]
                }
                for row in rows
            ]
    
    def create_nutrient_mapping(self) -> Dict[str, str]:
        """Create mapping from FDC nutrient IDs to canonical nutrient IDs"""
        canonical_nutrients = self.get_canonical_nutrients()
        mapping = {}
        
        # Simple mapping based on nutrient names (can be enhanced)
        for nutrient in canonical_nutrients:
            nutrient_id = nutrient['id']
            name = nutrient['name'].lower()
            
            # Map common FDC nutrient names to canonical IDs
            if 'energy' in name and 'kcal' in nutrient['unit']:
                mapping['1008'] = nutrient_id  # Energy (kcal)
            elif 'protein' in name:
                mapping['1003'] = nutrient_id  # Protein
            elif 'fat' in name and 'total' in name:
                mapping['1004'] = nutrient_id  # Total fat
            elif 'carbohydrate' in name and 'total' in name:
                mapping['1005'] = nutrient_id  # Total carbohydrate
            elif 'fiber' in name and 'dietary' in name:
                mapping['1079'] = nutrient_id  # Dietary fiber
            elif 'sugar' in name and 'total' in name:
                mapping['2000'] = nutrient_id  # Total sugars
            elif 'sodium' in name:
                mapping['1093'] = nutrient_id  # Sodium
            elif 'calcium' in name:
                mapping['1087'] = nutrient_id  # Calcium
            elif 'iron' in name:
                mapping['1089'] = nutrient_id  # Iron
            elif 'vitamin c' in name:
                mapping['1162'] = nutrient_id  # Vitamin C
        
        return mapping
