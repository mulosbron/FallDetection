import torch
from PIL import Image
import asyncio
import logging
from transformers import AutoProcessor, AutoModelForImageTextToText
from typing import Dict, Optional
import time

class ModelService:
    def __init__(self):
        self.processor = None
        self.model = None
        self.model_lock = asyncio.Lock()
        self.is_initialized = False
        
    async def initialize(self):
        """Model ve processor'u yükle"""
        logging.info("🔥 Loading SmolVLM2 model...")
        
        try:
            model_path = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"
            
            # Check GPU
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
                logging.info(f"🎮 GPU: {gpu_name}, VRAM: {total_vram:.1f}GB")
            else:
                logging.warning("⚠️ CUDA not available, using CPU")
            
            # Load processor
            self.processor = AutoProcessor.from_pretrained(model_path)
            logging.info("✅ Processor loaded")
            
            # Load model
            self.model = AutoModelForImageTextToText.from_pretrained(
                model_path,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            if torch.cuda.is_available():
                vram_usage = torch.cuda.memory_allocated(0) / 1024**3
                logging.info(f"✅ Model loaded to GPU, VRAM usage: {vram_usage:.1f}GB")
            else:
                logging.info("✅ Model loaded to CPU")
            
            self.is_initialized = True
            logging.info("🎉 Model service initialized successfully!")
            
        except Exception as e:
            logging.error(f"❌ Model initialization failed: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Model sağlık kontrolü"""
        return self.is_initialized and self.processor is not None and self.model is not None
    
    def _ask_yes_no(self, image: Image.Image, question: str) -> str:
        """Tek bir görüntü ve soru için deterministik Yes/No üretir"""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": question},
                ],
            }
        ]
        
        inputs = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        
        # Move to device and convert image tensors to float16 if using GPU
        device = next(self.model.parameters()).device
        inputs = {k: (v.to(device) if isinstance(v, torch.Tensor) else v) for k, v in inputs.items()}
        
        if "pixel_values" in inputs and torch.cuda.is_available():
            inputs["pixel_values"] = inputs["pixel_values"].to(dtype=torch.float16)
        
        with torch.no_grad():
            ids = self.model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=2,
                temperature=0.0,
                pad_token_id=self.processor.tokenizer.eos_token_id,
                eos_token_id=self.processor.tokenizer.eos_token_id,
            )
        
        input_len = inputs["input_ids"].shape[1]
        new_tokens = ids[:, input_len:]
        text = self.processor.tokenizer.decode(new_tokens[0], skip_special_tokens=True).strip().lower()
        
        # Interpret result
        if text.startswith("yes"): 
            return "Yes"
        if text.startswith("no"): 
            return "No"
        if "yes" in text and "no" not in text: 
            return "Yes"
        if "no" in text: 
            return "No"
        
        return text.capitalize() if text else "No"
    
    def _make_crops(self, image: Image.Image) -> list:
        """Görüntüden birkaç merkez odaklı kırpım üretir"""
        imgs = [image]
        w, h = image.size
        m = min(w, h)
        
        # Square center crop
        l = (w - m) // 2
        t = (h - m) // 2
        imgs.append(image.crop((l, t, l + m, t + m)))
        
        # 80% center crop
        s = int(m * 0.8)
        l2 = max(0, (w - s) // 2)
        t2 = max(0, (h - s) // 2)
        imgs.append(image.crop((l2, t2, l2 + s, t2 + s)))
        
        return imgs
    
    async def detect_fall(self, image: Image.Image) -> Dict:
        """Düşme tespiti ana fonksiyonu"""
        if not self.is_initialized:
            raise RuntimeError("Model not initialized")
        
        # Thread-safe model usage
        async with self.model_lock:
            try:
                # Multi-crop voting approach
                crops = self._make_crops(image)
                yes_votes = 0
                no_votes = 0
                
                for idx, img in enumerate(crops):
                    # Check if person is visible
                    q_person = "Is there a person visible in this image? Answer Yes or No."
                    seen = self._ask_yes_no(img, q_person)
                    
                    if seen == "Yes":
                        # Check if person is fallen
                        q_fall = "Is any person lying on the ground or floor (appears fallen)? Answer Yes or No."
                        fallen = self._ask_yes_no(img, q_fall)
                        
                        if fallen == "Yes":
                            yes_votes += 1
                        else:
                            no_votes += 1
                    else:
                        no_votes += 1
                
                # Determine final result
                final_result = "Yes" if yes_votes > no_votes else "No"
                confidence = max(yes_votes, no_votes) / len(crops)
                
                # Clear GPU cache if available
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                return {
                    "result": final_result,
                    "confidence": round(confidence, 3),
                    "votes": {"yes": yes_votes, "no": no_votes, "total_crops": len(crops)}
                }
                
            except Exception as e:
                logging.error(f"❌ Fall detection error: {e}")
                raise
    
    async def cleanup(self):
        """Cleanup resources"""
        logging.info("🧹 Cleaning up model service...")
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.processor = None
        self.model = None
        self.is_initialized = False
        
        logging.info("✅ Model service cleanup completed")
