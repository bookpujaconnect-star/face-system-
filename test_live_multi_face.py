import base64
import cv2
import json
import urllib.request
import numpy as np
from evaluation.synthetic_dataset import SyntheticDatasetGenerator

def run_test():
    print("[TEST] Generating frame with multiple students walking into campus entrance...")
    # Generate frame with 2 students
    img = SyntheticDatasetGenerator.create_multi_face_frame([101, 202])
    
    # Encode as JPEG
    _, buffer = cv2.imencode('.jpg', img)
    b64_str = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
    
    # Make POST request to /api/camera/process-frame
    url = "http://127.0.0.1:5050/api/camera/process-frame"
    payload = json.dumps({
        "image": b64_str,
        "camera_id": "Gate-North-01",
        "camera_name": "Main Entrance Gate Lane 1",
        "save_log": False
    }).encode('utf-8')
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"[TEST] Sending frame to {url}...")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            res_body = json.loads(resp.read().decode('utf-8'))
            print(f"[TEST] Response Status: {status}")
            print(f"[TEST] Faces detected count: {res_body.get('faces_count')}")
            print(f"[TEST] Total Frame Latency: {res_body.get('total_frame_latency_ms')} ms")
            print(f"[TEST] Estimated FPS: {res_body.get('fps_estimate')}")
            
            results = res_body.get("results", [])
            print(f"[TEST] Processed Face Results count: {len(results)}")
            for i, det in enumerate(results):
                stu = det.get("student") or {}
                print(f"  Face #{i+1}: BBox={det.get('bbox')}, Status={det.get('status')}, Student={stu.get('name')}, Reg={stu.get('reg_no')}, SimScore={det.get('similarity_score')}, Latency={det.get('total_face_latency_ms')}ms")
            
            # Assertions
            assert status == 200, f"Expected 200, got {status}"
            assert res_body.get("faces_count") >= 2, f"Expected at least 2 faces, got {res_body.get('faces_count')}"
            assert len(results) >= 2, f"Expected at least 2 result entries, got {len(results)}"
            
            # Check disjoint identity assignment
            recognized_ids = [d["student"]["student_id"] for d in results if d.get("student") and d.get("student", {}).get("student_id")]
            assert len(recognized_ids) == len(set(recognized_ids)), f"Duplicate student assigned to multiple faces! {recognized_ids}"
            
            print("\n=======================================================")
            print("[SUCCESS] MULTI-STUDENT CONCURRENT IDENTIFICATION PASSED!")
            print("All students in camera range are detected and disambiguated without confusion.")
            print("=======================================================")
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        raise

if __name__ == "__main__":
    run_test()
