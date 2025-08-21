#!/usr/bin/env python3
"""
Fall Detection API Test Script
FastAPI servisini test etmek için kullanılır
"""

import requests
import json
import time
import os
from pathlib import Path

# API Configuration
API_BASE_URL = "http://localhost:8000"
TEST_IMAGES_DIR = "/mnt/c/Users/duggy/OneDrive/Belgeler/Github/FallDetection/test-images"

def test_health_check():
    """Health check endpoint test"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed!")
            print(f"   Status: {data.get('status')}")
            print(f"   Model loaded: {data.get('model_loaded')}")
            print(f"   Database connected: {data.get('database_connected')}")
            print(f"   GPU available: {data.get('gpu_available')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_single_image(image_path):
    """Tek görsel test"""
    print(f"\n🖼️ Testing single image: {os.path.basename(image_path)}")
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (os.path.basename(image_path), f, 'image/jpeg')}
            
            start_time = time.time()
            response = requests.post(f"{API_BASE_URL}/detect-fall/", files=files)
            elapsed_time = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Single image test passed!")
                print(f"   Result: {data.get('result')}")
                print(f"   Confidence: {data.get('confidence')}")
                print(f"   Processing time: {data.get('processing_time_ms')}ms")
                print(f"   Request time: {elapsed_time}ms")
                print(f"   Cached: {data.get('cached', False)}")
                print(f"   Image hash: {data.get('image_hash', '')[:16]}...")
                return True
            else:
                print(f"❌ Single image test failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Single image test error: {e}")
        return False

def test_batch_images(image_paths):
    """Batch görsel test"""
    print(f"\n📚 Testing batch images ({len(image_paths)} images)...")
    
    try:
        files = []
        for image_path in image_paths:
            files.append(('files', (os.path.basename(image_path), 
                                   open(image_path, 'rb'), 'image/jpeg')))
        
        start_time = time.time()
        response = requests.post(f"{API_BASE_URL}/detect-fall-batch/", files=files)
        elapsed_time = int((time.time() - start_time) * 1000)
        
        # Close files
        for _, file_tuple in files:
            file_tuple[1].close()
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            print("✅ Batch test passed!")
            print(f"   Total images: {len(results)}")
            print(f"   Request time: {elapsed_time}ms")
            
            fall_count = sum(1 for r in results if r.get('result') == 'Yes')
            cached_count = sum(1 for r in results if r.get('cached') == True)
            
            print(f"   Falls detected: {fall_count}/{len(results)}")
            print(f"   Cached results: {cached_count}/{len(results)}")
            
            for i, result in enumerate(results):
                if 'error' in result:
                    print(f"   ❌ {result['filename']}: {result['error']}")
                else:
                    print(f"   ✅ {result['filename']}: {result.get('result')} "
                          f"({result.get('processing_time_ms', 0)}ms)")
            return True
        else:
            print(f"❌ Batch test failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Batch test error: {e}")
        return False

def test_statistics():
    """İstatistik endpoint test"""
    print("\n📊 Testing statistics...")
    try:
        response = requests.get(f"{API_BASE_URL}/statistics")
        if response.status_code == 200:
            data = response.json()
            print("✅ Statistics test passed!")
            print(f"   Total processed: {data.get('total_processed')}")
            print(f"   Falls detected: {data.get('fall_detected')}")
            print(f"   No fall: {data.get('no_fall')}")
            print(f"   Avg processing time: {data.get('avg_processing_time_ms')}ms")
            print(f"   Days active: {data.get('days_active')}")
            return True
        else:
            print(f"❌ Statistics test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Statistics test error: {e}")
        return False

def get_test_images():
    """Test görsellerini bul"""
    if not os.path.exists(TEST_IMAGES_DIR):
        print(f"⚠️ Test images directory not found: {TEST_IMAGES_DIR}")
        return []
    
    supported_formats = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
    images = []
    
    for file in os.listdir(TEST_IMAGES_DIR):
        if any(file.lower().endswith(fmt) for fmt in supported_formats):
            images.append(os.path.join(TEST_IMAGES_DIR, file))
    
    return images[:5]  # Limit to first 5 images for testing

def main():
    """Ana test fonksiyonu"""
    print("🚀 Fall Detection API Test Started")
    print("=" * 50)
    
    # Test images
    test_images = get_test_images()
    if not test_images:
        print("❌ No test images found! Please add some images to test directory.")
        return
    
    print(f"📁 Found {len(test_images)} test images")
    
    # Test sequence
    tests_passed = 0
    total_tests = 0
    
    # 1. Health Check
    total_tests += 1
    if test_health_check():
        tests_passed += 1
    
    # 2. Single Image Test
    if test_images:
        total_tests += 1
        if test_single_image(test_images[0]):
            tests_passed += 1
    
    # 3. Batch Test (if multiple images)
    if len(test_images) > 1:
        total_tests += 1
        if test_batch_images(test_images[:3]):  # Test with 3 images
            tests_passed += 1
    
    # 4. Statistics Test
    total_tests += 1
    if test_statistics():
        tests_passed += 1
    
    # 5. Cache Test (same image again)
    if test_images:
        print(f"\n🔄 Testing cache with same image...")
        total_tests += 1
        if test_single_image(test_images[0]):  # Same image should be cached
            tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"🎉 Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! API is working correctly.")
    else:
        print("❌ Some tests failed. Check the API service.")

if __name__ == "__main__":
    main()
