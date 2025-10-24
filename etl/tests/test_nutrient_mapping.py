#!/usr/bin/env python3
"""
Tests for the comprehensive nutrient mapping system
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

from etl.evidence.lib.nutrient_mapper import NutrientMapper, MappedNutrient, UnmappedNutrientInfo
from etl.evidence.lib.nutrient_store import NutrientStore, NutrientRow
from etl.evidence.lib.unmapped_nutrients import UnmappedNutrientCollector, UnmappedNutrient

class TestNutrientMapper:
    """Test the comprehensive nutrient mapper"""
    
    def setup_method(self):
        """Set up test data"""
        # Create a minimal nutrients.json for testing
        self.test_nutrients = {
            "canonical_scheme": "INFOODS_tagnames",
            "version": "v1.1",
            "nutrients": [
                {
                    "id": "ENERC_KCAL",
                    "name": "Energy (kcal)",
                    "class": "proximate",
                    "unit": "kcal",
                    "fdc_candidates": ["208", "957", "958"],
                    "fdc_unit": "KCAL",
                    "unit_factor_from_fdc": 1.0,
                    "confidence": "high"
                },
                {
                    "id": "PROT",
                    "name": "Protein",
                    "class": "proximate",
                    "unit": "g",
                    "fdc_candidates": ["203"],
                    "fdc_unit": "G",
                    "unit_factor_from_fdc": 1.0,
                    "confidence": "high"
                },
                {
                    "id": "F",
                    "name": "Fluoride",
                    "class": "mineral",
                    "unit": "mg",
                    "fdc_candidates": ["313"],
                    "fdc_unit": "UG",
                    "unit_factor_from_fdc": 0.001,
                    "confidence": "high"
                }
            ]
        }
        
        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_nutrients, self.temp_file)
        self.temp_file.close()
        
        self.mapper = NutrientMapper(Path(self.temp_file.name))
    
    def teardown_method(self):
        """Clean up test data"""
        Path(self.temp_file.name).unlink()
    
    def test_build_fdc_to_infoods_mapping(self):
        """Test that FDC to INFOODS mapping is built correctly"""
        mapping = self.mapper.fdc_to_infoods_mapping
        
        # Should have 5 FDC IDs total
        assert len(mapping) == 5
        
        # Test specific mappings
        assert "208" in mapping
        assert mapping["208"].infoods_id == "ENERC_KCAL"
        assert mapping["208"].conversion_factor == 1.0
        
        assert "203" in mapping
        assert mapping["203"].infoods_id == "PROT"
        assert mapping["203"].conversion_factor == 1.0
        
        assert "313" in mapping
        assert mapping["313"].infoods_id == "F"
        assert mapping["313"].conversion_factor == 0.001
    
    def test_map_fdc_nutrient_success(self):
        """Test successful mapping of FDC nutrient"""
        fdc_nutrient = {
            'nutrient_id': '208',
            'fdc_id': '12345',
            'amount': '100.5',
            'unit': 'KCAL'
        }
        
        result = self.mapper.map_fdc_nutrient(fdc_nutrient)
        
        assert result.mapped == True
        assert result.nutrient_row is not None
        assert result.nutrient_row['nutrient_id'] == 'ENERC_KCAL'
        assert result.nutrient_row['amount'] == 100.5
        assert result.nutrient_row['unit'] == 'kcal'
        assert result.nutrient_row['original_amount'] == 100.5
        assert result.nutrient_row['original_unit'] == 'KCAL'
        assert result.nutrient_row['conversion_factor'] == 1.0
    
    def test_map_fdc_nutrient_with_conversion(self):
        """Test mapping with unit conversion"""
        fdc_nutrient = {
            'nutrient_id': '313',
            'fdc_id': '12345',
            'amount': '1000',
            'unit': 'UG'
        }
        
        result = self.mapper.map_fdc_nutrient(fdc_nutrient)
        
        assert result.mapped == True
        assert result.nutrient_row['nutrient_id'] == 'F'
        assert result.nutrient_row['amount'] == 1.0  # 1000 * 0.001
        assert result.nutrient_row['unit'] == 'mg'
        assert result.nutrient_row['original_amount'] == 1000
        assert result.nutrient_row['original_unit'] == 'UG'
        assert result.nutrient_row['conversion_factor'] == 0.001
    
    def test_map_fdc_nutrient_unmapped(self):
        """Test mapping of unmapped FDC nutrient"""
        fdc_nutrient = {
            'nutrient_id': '9999',  # Not in our test data
            'fdc_id': '12345',
            'amount': '50.0',
            'unit': 'G'
        }
        
        result = self.mapper.map_fdc_nutrient(fdc_nutrient)
        
        assert result.mapped == False
        assert result.unmapped_info is not None
        assert result.unmapped_info.fdc_id == '9999'
        assert result.unmapped_info.food_id == '12345'
        assert result.unmapped_info.amount == 50.0
    
    def test_get_mapping_stats(self):
        """Test mapping statistics"""
        stats = self.mapper.get_mapping_stats()
        
        assert stats['total_fdc_ids_mapped'] == 5
        assert stats['unmapped_nutrients'] == 0  # No unmapped yet
        assert 'high' in stats['confidence_breakdown']
        assert stats['confidence_breakdown']['high'] == 3
    
    def test_validate_mappings(self):
        """Test mapping validation"""
        issues = self.mapper.validate_mappings()
        assert len(issues) == 0  # Our test data should be valid


class TestNutrientStore:
    """Test the enhanced nutrient store"""
    
    def setup_method(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False)
        self.temp_db.close()
        
        self.store = NutrientStore(Path(self.temp_db.name))
        self.store.create_tables()
    
    def teardown_method(self):
        """Clean up test database"""
        Path(self.temp_db.name).unlink()
    
    def test_nutrient_row_creation(self):
        """Test creating NutrientRow with new fields"""
        nutrient_row = NutrientRow(
            id="test_123_ENERC_KCAL",
            food_id="123",
            nutrient_id="ENERC_KCAL",
            amount=100.5,
            unit="kcal",
            original_amount=100.5,
            original_unit="KCAL",
            original_nutrient_id="208",
            conversion_factor=1.0,
            source="fdc_foundation",
            confidence=0.9,
            nutrient_name="Energy (kcal)",
            nutrient_class="proximate"
        )
        
        assert nutrient_row.id == "test_123_ENERC_KCAL"
        assert nutrient_row.amount == 100.5
        assert nutrient_row.original_amount == 100.5
        assert nutrient_row.conversion_factor == 1.0
        assert nutrient_row.nutrient_name == "Energy (kcal)"
    
    def test_store_and_retrieve_nutrient_row(self):
        """Test storing and retrieving nutrient rows"""
        nutrient_row = NutrientRow(
            id="test_123_ENERC_KCAL",
            food_id="123",
            nutrient_id="ENERC_KCAL",
            amount=100.5,
            unit="kcal",
            original_amount=100.5,
            original_unit="KCAL",
            original_nutrient_id="208",
            conversion_factor=1.0,
            source="fdc_foundation",
            confidence=0.9,
            nutrient_name="Energy (kcal)",
            nutrient_class="proximate"
        )
        
        # Store
        self.store.store_nutrient_row(nutrient_row)
        
        # Retrieve
        retrieved = self.store.get_nutrient_rows_for_food("123")
        assert len(retrieved) == 1
        
        retrieved_row = retrieved[0]
        assert retrieved_row.id == nutrient_row.id
        assert retrieved_row.amount == nutrient_row.amount
        assert retrieved_row.original_amount == nutrient_row.original_amount
        assert retrieved_row.conversion_factor == nutrient_row.conversion_factor
        assert retrieved_row.nutrient_name == nutrient_row.nutrient_name


class TestUnmappedNutrientCollector:
    """Test the unmapped nutrient proposal system"""
    
    def setup_method(self):
        """Set up test directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.collector = UnmappedNutrientCollector(Path(self.temp_dir))
    
    def teardown_method(self):
        """Clean up test directory"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_add_unmapped_nutrient(self):
        """Test adding unmapped nutrients"""
        unmapped = UnmappedNutrientInfo(
            fdc_id="9999",
            fdc_name="Test Nutrient",
            fdc_unit="G",
            food_id="123",
            amount=50.0
        )
        
        self.collector.add_unmapped_nutrient(unmapped)
        assert len(self.collector.unmapped_nutrients) == 1
    
    def test_collect_unmapped_nutrients(self):
        """Test collecting and grouping unmapped nutrients"""
        # Add multiple unmapped nutrients with same FDC ID
        for i in range(3):
            unmapped = UnmappedNutrientInfo(
                fdc_id="9999",
                fdc_name="Test Nutrient",
                fdc_unit="G",
                food_id=f"food_{i}",
                amount=50.0
            )
            self.collector.add_unmapped_nutrient(unmapped)
        
        # Add one with different FDC ID
        unmapped2 = UnmappedNutrientInfo(
            fdc_id="8888",
            fdc_name="Another Nutrient",
            fdc_unit="MG",
            food_id="food_4",
            amount=25.0
        )
        self.collector.add_unmapped_nutrient(unmapped2)
        
        # Collect proposals
        proposals = self.collector.collect_unmapped_nutrients()
        
        assert len(proposals) == 2  # Two unique FDC IDs
        
        # Find the proposal for FDC 9999
        proposal_9999 = next(p for p in proposals if p.fdc_id == "9999")
        assert proposal_9999.occurrence_count == 3
        assert len(proposal_9999.sample_food_ids) == 3
        assert proposal_9999.suggested_action == "map"  # High occurrence
        assert proposal_9999.confidence == "high"
        
        # Find the proposal for FDC 8888
        proposal_8888 = next(p for p in proposals if p.fdc_id == "8888")
        assert proposal_8888.occurrence_count == 1
        assert proposal_8888.suggested_action == "ignore"  # Low occurrence
        assert proposal_8888.confidence == "low"
    
    def test_save_and_load_proposals(self):
        """Test saving and loading proposals"""
        # Create a proposal
        proposal = UnmappedNutrient(
            fdc_id="9999",
            fdc_name="Test Nutrient",
            fdc_unit="G",
            occurrence_count=5,
            sample_food_ids=["food1", "food2"],
            suggested_action="map",
            confidence="high",
            notes="Test notes"
        )
        
        # Save
        self.collector.save_unmapped_proposals([proposal])
        
        # Load
        loaded = self.collector.load_existing_proposals()
        assert len(loaded) == 1
        assert loaded[0].fdc_id == proposal.fdc_id
        assert loaded[0].occurrence_count == proposal.occurrence_count


if __name__ == "__main__":
    pytest.main([__file__])
