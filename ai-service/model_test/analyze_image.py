import torch
from PIL import Image
import os
import logging
from datetime import datetime
from transformers import AutoProcessor, AutoModelForImageTextToText

# Log system setup
def setup_logging():
	"""Setup logging system"""
	log_dir = "logs"
	if not os.path.exists(log_dir):
		os.makedirs(log_dir)
	
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	log_file = f"{log_dir}/smolvlm2_test_{timestamp}.log"
	
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(levelname)s - %(message)s',
		handlers=[
			logging.FileHandler(log_file, encoding='utf-8'),
			logging.StreamHandler()
		]
	)
	
	print(f"📝 Log file: {log_file}")
	return log_file

def check_gpu():
	"""Check GPU status"""
	logging.info("Checking GPU status...")
	
	if torch.cuda.is_available():
		gpu_name = torch.cuda.get_device_name(0)
		total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
		current_vram = torch.cuda.memory_allocated(0) / 1024**3
		
		print(f"✅ CUDA available")
		print(f"🎮 GPU: {gpu_name}")
		print(f"💾 VRAM: {total_vram:.1f} GB")
		print(f"🔥 Current VRAM: {current_vram:.1f} GB in use")
		
		logging.info(f"GPU: {gpu_name}, VRAM: {total_vram:.1f}GB")
		return True
	else:
		print("❌ CUDA not available!")
		logging.error("CUDA not available!")
		return False

def load_model():
	"""Load SmolVLM2 model"""
	logging.info("Loading model...")
	print("\n📥 Loading model... (First time will download)")
	
	model_path = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"
	
	try:
		logging.info(f"Loading processor: {model_path}")
		processor = AutoProcessor.from_pretrained(model_path)
		logging.info("Processor loaded successfully")
		
		logging.info(f"Loading model: {model_path}")
		model = AutoModelForImageTextToText.from_pretrained(
			model_path,
			torch_dtype=torch.float16,
			device_map="auto"
		)
		
		vram_usage = torch.cuda.memory_allocated(0) / 1024**3
		print("✅ Model loaded to GPU successfully!")
		print(f"💾 Model VRAM usage: {vram_usage:.1f} GB")
		
		logging.info(f"Model loaded successfully, VRAM: {vram_usage:.1f}GB")
		return processor, model
		
	except Exception as e:
		error_msg = f"Model loading error: {e}"
		print(f"❌ {error_msg}")
		logging.error(error_msg)
		return None, None

# Yardımcılar: çok-aşamalı evet/hayır ve çok-kırpım oylama

def _ask_yes_no(processor, model, image, question: str) -> str:
	"""Tek bir görüntü ve soru için deterministik Yes/No üretir."""
	messages = [
		{
			"role": "user",
			"content": [
				{"type": "image", "image": image},
				{"type": "text", "text": question},
			],
		}
	]
	inputs = processor.apply_chat_template(
		messages,
		add_generation_prompt=True,
		tokenize=True,
		return_dict=True,
		return_tensors="pt",
	)
	# Cihaza taşı, yalnızca görüntü tensörünü float16 yap
	inputs = {k: (v.to(model.device) if isinstance(v, torch.Tensor) else v) for k, v in inputs.items()}
	if "pixel_values" in inputs:
		inputs["pixel_values"] = inputs["pixel_values"].to(dtype=torch.float16)
	with torch.no_grad():
		ids = model.generate(
			**inputs,
			do_sample=False,
			max_new_tokens=2,
			temperature=0.0,
			pad_token_id=processor.tokenizer.eos_token_id,
			eos_token_id=processor.tokenizer.eos_token_id,
		)
	input_len = inputs["input_ids"].shape[1]
	new_tokens = ids[:, input_len:]
	text = processor.tokenizer.decode(new_tokens[0], skip_special_tokens=True).strip().lower()
	if text.startswith("yes"): return "Yes"
	if text.startswith("no"): return "No"
	if "yes" in text and "no" not in text: return "Yes"
	if "no" in text: return "No"
	return text.capitalize() if text else "No"


def _make_crops(image: Image.Image) -> list:
	"""Görüntüden birkaç merkez odaklı kırpım üretir."""
	imgs = [image]
	w, h = image.size
	m = min(w, h)
	# Kare merkez kırpım
	l = (w - m) // 2
	t = (h - m) // 2
	imgs.append(image.crop((l, t, l + m, t + m)))
	# %80 merkez kırpım
	s = int(m * 0.8)
	l2 = max(0, (w - s) // 2)
	t2 = max(0, (h - s) // 2)
	imgs.append(image.crop((l2, t2, l2 + s, t2 + s)))
	return imgs

def analyze_local_image(processor, model, image_path, prompt):
	"""Analyze local image using robust multi-step voting; returns 'Yes' or 'No'"""
	filename = os.path.basename(image_path)
	logging.info(f"Analyzing image: {filename}")
	print(f"\n🖼️ Analyzing image: {filename}")
	print(f"📝 Question: {prompt}")
	
	try:
		# Load image
		logging.info(f"Loading image: {image_path}")
		image = Image.open(image_path).convert("RGB")
		logging.info(f"Image loaded: {image.size[0]}x{image.size[1]} pixels")
		
		# Çok-kırpım
		crops = _make_crops(image)
		yes_votes = 0
		no_votes = 0
		for idx, img in enumerate(crops):
			logging.info(f"Crop {idx+1}/{len(crops)} evaluating person presence...")
			q_person = "Is there a person visible in this image? Answer Yes or No."
			seen = _ask_yes_no(processor, model, img, q_person)
			logging.info(f"Crop {idx+1} person visible: {seen}")
			if seen == "Yes":
				q_fall = "Is any person lying on the ground or floor (appears fallen)? Answer Yes or No."
				fallen = _ask_yes_no(processor, model, img, q_fall)
				logging.info(f"Crop {idx+1} fallen: {fallen}")
				if fallen == "Yes":
					yes_votes += 1
				else:
					no_votes += 1
			else:
				no_votes += 1
		
		logging.info(f"Votes -> YES: {yes_votes}, NO: {no_votes}")
		final = "Yes" if yes_votes > no_votes else "No"
		return final
		
	except Exception as e:
		error_msg = f"Image analysis error: {e}"
		print(f"❌ {error_msg}")
		logging.error(error_msg, exc_info=True)
		return None

def list_test_images():
	"""List test images"""
	test_dir = "/mnt/c/Users/duggy/OneDrive/Belgeler/Github/FallDetection/test-images"
	supported_formats = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff']
	
	logging.info(f"Searching for test images: {test_dir}")
	
	images = []
	if os.path.exists(test_dir):
		for file in os.listdir(test_dir):
			if any(file.lower().endswith(fmt) for fmt in supported_formats):
				images.append(os.path.join(test_dir, file))
	
	logging.info(f"{len(images)} test images found")
	return images

def main():
	"""Main function"""
	# Setup logging
	log_file = setup_logging()
	
	print("🚀 SmolVLM2 Fall Detection Test Starting...\n")
	logging.info("SmolVLM2 fall detection test starting")
	
	# Check GPU
	if not check_gpu():
		return
	
	# Load model
	processor, model = load_model()
	if processor is None or model is None:
		return
	
	# List test images
	test_images = list_test_images()
	
	if not test_images:
		print("❌ No test images found!")
		logging.warning("No test images found")
		return
	
	print(f"\n🖼️ {len(test_images)} test images found:")
	for i, img in enumerate(test_images):
		print(f"  {i+1}. {os.path.basename(img)}")
	
	# Test each image
	successful_tests = 0
	for i, image_path in enumerate(test_images):
		print(f"\n{'='*60}")
		print(f"🖼️ TEST {i+1}/{len(test_images)}: {os.path.basename(image_path)}")
		print(f"{'='*60}")
		
		logging.info(f"TEST {i+1}/{len(test_images)} starting: {os.path.basename(image_path)}")
		
		# Fall detection specific prompt - basit ve direkt
		prompt = "Fall detected: Yes or No?"
		
		try:
			# Analyze image
			result = analyze_local_image(processor, model, image_path, prompt)
			
			if result:
				print("\n🤖 FALL DETECTION RESULT:")
				print("-" * 40)
				print(result)
				print("-" * 40)
				
				# Simple result interpretation
				result_lower = result.lower().strip()
				if "yes" in result_lower:
					print("🚨 FALL DETECTED - Person on ground!")
				elif "no" in result_lower:
					print("✅ NO FALL - Person standing or not visible")
				else:
					print("❓ UNCLEAR - Model response unclear")
				
				successful_tests += 1
				logging.info(f"TEST {i+1} successful")
			else:
				logging.warning(f"TEST {i+1} failed")
			
			vram_usage = torch.cuda.memory_allocated(0) / 1024**3
			print(f"\n💾 VRAM usage: {vram_usage:.1f} GB")
			
		except Exception as e:
			error_msg = f"Test error: {e}"
			print(f"❌ {error_msg}")
			logging.error(error_msg)
			print("⚠️ CUDA error may require restarting the script if it persists.")
			break
		
		# Clear VRAM - CUDA hatası gelmesin diye try-catch
		try:
			torch.cuda.empty_cache()
			print("🧹 VRAM cleared.")
			logging.info("VRAM cleared")
		except Exception as e:
			print(f"⚠️ VRAM clear warning: {e}")
			logging.warning(f"VRAM clear warning: {e}")
	
	print(f"\n🎉 Fall Detection Test completed!")
	print(f"✅ Successful: {successful_tests}/{len(test_images)}")
	logging.info(f"Fall detection test completed: {successful_tests}/{len(test_images)} successful")
	print(f"📝 Detailed log: {log_file}")

if __name__ == "__main__":
	main()