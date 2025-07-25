#!/usr/bin/env python3
"""
Test script to validate MT5 instance database functionality.
"""
import os
import tempfile
from src.mt5_instance_database import MT5InstanceDatabase

def test_database():
    """Test the MT5 instance database."""
    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    try:
        # Initialize database
        db = MT5InstanceDatabase(test_db_path)
        print(f"✅ Database initialized: {test_db_path}")
        
        # Add some test instances
        db.add_instance("master", "C:\\MT5_Master", account_number=12345, broker="TestBroker", description="Test master")
        db.add_instance("slave", "C:\\MT5_Slaves\\Account2", account_number=67890, broker="TestBroker", description="Test slave")
        print("✅ Test instances added")
        
        # Get statistics
        stats = db.get_database_stats()
        print(f"✅ Database stats: {stats['total_instances']} total, {stats['active_instances']} active")
        
        # List all instances
        instances = db.get_all_instances()
        print(f"✅ Retrieved {len(instances)} instances")
        
        for instance in instances:
            print(f"   - {instance['role']}: {instance['instance_path']}")
        
        # Test retrieval by role
        master = db.get_instance("master")
        if master:
            print(f"✅ Found master instance: {master['instance_path']}")
        
        print("✅ All database tests passed!")
        
    finally:
        # Clean up test database
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)
            print(f"🧹 Cleaned up test database: {test_db_path}")

if __name__ == "__main__":
    test_database() 