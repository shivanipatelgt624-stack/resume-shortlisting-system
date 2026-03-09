#!/usr/bin/env python3
"""
Test Database Insert and Select Operations
This script tests the PostgreSQL database connection and performs basic operations
"""

import sys
from datetime import datetime

# Add parent directory to path to import config
sys.path.insert(0, '..')

from config.database import db_config


def test_connection():
    """Test database connection"""
    print("\n" + "="*60)
    print("STEP 1: Testing Database Connection")
    print("="*60)
    if db_config.test_connection():
        return True
    return False


def test_create_tables():
    """Create necessary tables"""
    print("\n" + "="*60)
    print("STEP 2: Creating Tables")
    print("="*60)
    try:
        conn = db_config.get_connection()
        db_config.create_tables(conn)
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Failed to create tables: {str(e)}")
        return False


def test_insert_resume():
    """Test inserting a resume record"""
    print("\n" + "="*60)
    print("STEP 3: Testing INSERT Operation")
    print("="*60)
    try:
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Sample data
        test_resumes = [
            ('john_doe_resume.pdf', 'John Doe', 'john@example.com', '+1-555-0101'),
            ('jane_smith_resume.pdf', 'Jane Smith', 'jane@example.com', '+1-555-0102'),
            ('bob_johnson_resume.pdf', 'Bob Johnson', 'bob@example.com', '+1-555-0103'),
        ]
        
        for filename, name, email, phone in test_resumes:
            try:
                insert_query = """
                INSERT INTO resumes (filename, applicant_name, email, phone, content)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
                """
                cursor.execute(insert_query, (filename, name, email, phone, f"Resume content for {name}"))
                resume_id = cursor.fetchone()[0]
                conn.commit()
                print(f"✓ Inserted resume ID {resume_id}: {name} ({email})")
            except Exception as e:
                conn.rollback()
                if 'duplicate key' in str(e).lower():
                    print(f"⚠ Resume already exists: {filename}")
                else:
                    print(f"✗ Error inserting resume: {str(e)}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Failed to test INSERT: {str(e)}")
        return False


def test_select_resumes():
    """Test selecting resumes from database"""
    print("\n" + "="*60)
    print("STEP 4: Testing SELECT Operation")
    print("="*60)
    try:
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Select all resumes
        select_query = "SELECT id, filename, applicant_name, email, phone, upload_date FROM resumes ORDER BY id;"
        cursor.execute(select_query)
        
        resumes = cursor.fetchall()
        
        if resumes:
            print(f"\n✓ Found {len(resumes)} resume(s) in database:\n")
            print(f"{'ID':<5} {'Name':<20} {'Email':<25} {'Phone':<15} {'Upload Date':<20}")
            print("-" * 85)
            
            for resume in resumes:
                resume_id, filename, name, email, phone, upload_date = resume
                name = name or "N/A"
                email = email or "N/A"
                phone = phone or "N/A"
                upload_date_str = upload_date.strftime('%Y-%m-%d %H:%M:%S') if upload_date else "N/A"
                
                print(f"{resume_id:<5} {name:<20} {email:<25} {phone:<15} {upload_date_str:<20}")
        else:
            print("✓ No resumes found in database (table is empty)")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Failed to test SELECT: {str(e)}")
        return False


def test_update_resume():
    """Test updating a resume record"""
    print("\n" + "="*60)
    print("STEP 5: Testing UPDATE Operation")
    print("="*60)
    try:
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Update the first resume
        update_query = """
        UPDATE resumes 
        SET applicant_name = %s, email = %s 
        WHERE id = (SELECT MIN(id) FROM resumes)
        RETURNING id, applicant_name, email;
        """
        
        cursor.execute(update_query, ('John Updated', 'john.updated@example.com'))
        result = cursor.fetchone()
        
        if result:
            resume_id, name, email = result
            conn.commit()
            print(f"✓ Updated resume ID {resume_id}: {name} ({email})")
        else:
            print("⚠ No resume found to update")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Failed to test UPDATE: {str(e)}")
        return False


def test_delete_resume():
    """Test deleting a resume record"""
    print("\n" + "="*60)
    print("STEP 6: Testing DELETE Operation")
    print("="*60)
    try:
        conn = db_config.get_connection()
        cursor = conn.cursor()
        
        # Check if we can delete (delete the last added if exists)
        delete_query = """
        DELETE FROM resumes 
        WHERE id = (SELECT MAX(id) FROM resumes)
        RETURNING id, applicant_name;
        """
        
        cursor.execute(delete_query)
        result = cursor.fetchone()
        
        if result:
            resume_id, name = result
            conn.commit()
            print(f"✓ Deleted resume ID {resume_id}: {name}")
        else:
            print("⚠ No resume found to delete")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Failed to test DELETE: {str(e)}")
        return False


def main():
    """Run all database tests"""
    print("\n" + "█"*60)
    print("█  Resume Shortlisting System - Database Test Suite")
    print("█"*60)
    
    # Run tests in sequence
    results = {
        'Connection Test': test_connection(),
        'Create Tables': test_create_tables(),
        'INSERT Test': test_insert_resume(),
        'SELECT Test': test_select_resumes(),
        'UPDATE Test': test_update_resume(),
        'DELETE Test': test_delete_resume(),
    }
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:<30} {status}")
    
    print("="*60)
    print(f"Result: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
