"""End-to-end smoke tests for the ETL2 pipeline"""
import subprocess
import sys
from pathlib import Path

def test_full_pipeline_smoke(temp_ontology_dir, temp_build_dir):
    """Test that the full pipeline runs without errors on minimal data"""
    # Run the full pipeline
    result = subprocess.run([
        sys.executable, "-m", "mise", "run", "build",
        "--in", str(temp_ontology_dir),
        "--build", str(temp_build_dir),
        "--verbose"
    ], capture_output=True, text=True)
    
    # Should succeed
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"
    
    # Check that key artifacts were created
    assert (temp_build_dir / "compiled" / "taxa.jsonl").exists()
    assert (temp_build_dir / "compiled" / "docs.jsonl").exists()
    assert (temp_build_dir / "compiled" / "attributes.json").exists()
    assert (temp_build_dir / "compiled" / "nutrients.json").exists()
    assert (temp_build_dir / "compiled" / "parts.json").exists()

def test_pipeline_with_tests(temp_ontology_dir, temp_build_dir):
    """Test that the pipeline with contract verification works"""
    # Run the full pipeline with tests
    result = subprocess.run([
        sys.executable, "-m", "mise", "run", "build",
        "--in", str(temp_ontology_dir),
        "--build", str(temp_build_dir),
        "--with-tests",
        "--verbose"
    ], capture_output=True, text=True)
    
    # Should succeed
    assert result.returncode == 0, f"Pipeline with tests failed: {result.stderr}"
    
    # Check that verification reports were created
    assert (temp_build_dir / "report" / "verify_stage_0.json").exists()
    assert (temp_build_dir / "report" / "verify_stage_a.json").exists()
    assert (temp_build_dir / "report" / "verify_stage_b.json").exists()
    assert (temp_build_dir / "report" / "verify_stage_c.json").exists()

def test_individual_stage_testing(temp_ontology_dir, temp_build_dir):
    """Test that individual stage testing works"""
    # First run stage 0 to create artifacts
    result = subprocess.run([
        sys.executable, "-m", "mise", "run", "0",
        "--in", str(temp_ontology_dir),
        "--build", str(temp_build_dir),
        "--verbose"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Stage 0 failed: {result.stderr}"
    
    # Then test stage 0
    result = subprocess.run([
        sys.executable, "-m", "mise", "test", "0",
        "--in", str(temp_ontology_dir),
        "--build", str(temp_build_dir),
        "--verbose"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Stage 0 test failed: {result.stderr}"
