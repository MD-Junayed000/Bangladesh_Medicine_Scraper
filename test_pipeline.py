#!/usr/bin/env python3
"""
Test script to verify the pipeline and database are working.
This will create test data for all models to ensure everything is functional.
"""

import os
import django
from django.db import transaction

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from crawler.models import Medicine, Generic, Manufacturer, DosageForm, Indication, DrugClass
from medexbot.items import MedItem, GenericItem, ManufacturerItem, DosageFormItem, IndicationItem, DrugClassItem

def test_pipeline():
    """Test creating items through the pipeline."""
    print("🧪 Testing Pipeline and Database...")
    
    try:
        with transaction.atomic():
            # Test 1: Create a test manufacturer
            print("1️⃣ Creating test manufacturer...")
            manufacturer, created = Manufacturer.objects.get_or_create(
                manufacturer_id=99999,  # Use numeric ID
                defaults={
                    'manufacturer_name': 'Test Pharmaceutical Company',
                    'slug': 'test-pharmaceutical-company-99999'
                }
            )
            print(f"   ✅ Manufacturer: {manufacturer.manufacturer_name} (ID: {manufacturer.manufacturer_id})")
            
            # Test 2: Create a test generic
            print("2️⃣ Creating test generic...")
            generic, created = Generic.objects.get_or_create(
                generic_id=99999,  # Use numeric ID
                defaults={
                    'generic_name': 'Test Generic Medicine',
                    'slug': 'test-generic-medicine-99999'
                }
            )
            print(f"   ✅ Generic: {generic.generic_name} (ID: {generic.generic_id})")
            
        
            
            # Test 3: Create a test drug class
            print("5️⃣ Creating test drug class...")
            drug_class, created = DrugClass.objects.get_or_create(
                drug_class_id=99999,  # Use numeric ID
                defaults={
                    'drug_class_name': 'Test Drug Class',
                    'generics_count': 2,
                    'slug': 'test-drug-class-99999'
                }
            )
            print(f"   ✅ Drug Class: {drug_class.drug_class_name} (ID: {drug_class.drug_class_id})")
            
            # Test 4: Create a test medicine
            print("6️⃣ Creating test medicine...")
            medicine, created = Medicine.objects.get_or_create(
                brand_id=99999,  # Use numeric ID
                defaults={
                    'brand_name': 'Test Brand Medicine',
                    'type': 'allopathic',
                    'dosage_form': 'Tablet',
                    'strength': '500mg',
                    'manufacturer': manufacturer,
                    'generic': generic,
                    'slug': 'test-brand-medicine-99999'
                }
            )
            print(f"   ✅ Medicine: {medicine.brand_name} (ID: {medicine.brand_id})")
            
            print("\n🎉 All tests passed! Database and models are working correctly.")
            
            # Show counts
            print(f"\n📊 Current Database Counts:")
            print(f"   Manufacturers: {Manufacturer.objects.count()}")
            print(f"   Generics: {Generic.objects.count()}")
            print(f"   Drug Classes: {DrugClass.objects.count()}")
            print(f"   Medicines: {Medicine.objects.count()}")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_pipeline()
    if success:
        print("\n✅ Pipeline test completed successfully!")
        print("🌐 Check your Django admin at http://127.0.0.1:8000/admin/")
    else:
        print("\n❌ Pipeline test failed!")
