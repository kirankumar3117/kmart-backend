import os
import re
from difflib import SequenceMatcher
from typing import List, Dict, Optional

import pytesseract
from PIL import Image
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.product import Product
from app.models.order import Order
from app.models.cart_suggestion import CartSuggestion
from app.models.shop import Shop
from app.core.ws_manager import manager
import asyncio


# ==========================================
# 1. EXTRACT TEXT FROM IMAGE (Tesseract OCR)
# ==========================================
def extract_text_from_image(image_path: str) -> List[str]:
    """
    Opens the image file and runs Tesseract OCR on it.
    Returns a cleaned list of non-empty text lines.
    """
    img = Image.open(image_path)
    
    # Run Tesseract — returns raw text string
    raw_text = pytesseract.image_to_string(img)
    
    # Clean up: split into lines, strip whitespace, remove empty lines
    lines = []
    for line in raw_text.split("\n"):
        cleaned = line.strip()
        # Remove lines that are too short or just numbers/punctuation
        if cleaned and len(cleaned) > 2 and re.search(r'[a-zA-Z]', cleaned):
            lines.append(cleaned)
    
    return lines


# ==========================================
# 2. FUZZY MATCH LINES TO PRODUCTS
# ==========================================
def match_products(extracted_lines: List[str], db: Session) -> List[Dict]:
    """
    For each extracted text line, find the best matching product name
    from the database using fuzzy string matching.
    
    Returns a list of dicts:
    [{ "extracted_text": "...", "product_id": 1, "product_name": "...", "confidence": 0.85 }]
    """
    # Fetch all active products from the database
    all_products = db.query(Product).filter(Product.is_active == True).all()
    
    if not all_products:
        return [{"extracted_text": line, "product_id": None, "product_name": None, "confidence": 0.0} 
                for line in extracted_lines]
    
    # Build a lookup: { lowercase_name: product }
    product_map = {p.name.lower(): p for p in all_products}
    product_names = list(product_map.keys())
    
    results = []
    for line in extracted_lines:
        line_lower = line.lower()
        
        best_match = None
        best_score = 0.0
        
        # Compare this line against every product name
        for pname in product_names:
            # SequenceMatcher gives a ratio between 0.0 and 1.0
            score = SequenceMatcher(None, line_lower, pname).ratio()
            
            # Also check if the line CONTAINS the product name (partial match)
            if pname in line_lower or line_lower in pname:
                score = max(score, 0.75)  # Boost partial matches
            
            if score > best_score:
                best_score = score
                best_match = pname
        
        # Only suggest if confidence is reasonable (> 40%)
        if best_match and best_score > 0.4:
            matched_product = product_map[best_match]
            results.append({
                "extracted_text": line,
                "product_id": matched_product.id,
                "product_name": matched_product.name,
                "confidence": round(best_score, 2)
            })
        else:
            # No good match found — still record the line
            results.append({
                "extracted_text": line,
                "product_id": None,
                "product_name": None,
                "confidence": 0.0
            })
    
    return results


# ==========================================
# 3. MAIN BACKGROUND TASK
# ==========================================
def process_chitty_order(order_id: int):
    """
    Background task that:
    1. Reads the uploaded chitty image
    2. Extracts text via OCR
    3. Matches text to products
    4. Saves suggestions to the database
    5. Notifies the shopkeeper via WebSocket
    """
    # Create a fresh DB session for this background task
    db = SessionLocal()
    
    try:
        # 1. Get the order and its image path
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or not order.list_image_url:
            return
        
        # Convert the URL path ("/static/chitty_abc.jpg") to a file path ("uploads/chitty_abc.jpg")
        # 1. Strip the '/static/' prefix
        image_filename = order.list_image_url.replace("/static/", "")
        
        # 2. STRIP ANY LEADING SLASHES so os.path.join works correctly
        image_filename = image_filename.lstrip("/") 
        
        # 3. Safely join the path
        image_path = os.path.join("uploads", image_filename)
        
        # Add a quick debug print so you can see it working in your terminal!
        print(f"🤖 OCR Starting: Reading image from {image_path}") 
        
        if not os.path.exists(image_path):
            print(f"❌ OCR Error: File not found at {image_path}") # This helps immensely with debugging
            return
        
        # 2. Extract text from the image
        extracted_lines = extract_text_from_image(image_path)
        
        if not extracted_lines:
            return
        
        # 3. Match extracted lines to products
        matches = match_products(extracted_lines, db)
        
        # 4. Save each suggestion to the database
        for match in matches:
            suggestion = CartSuggestion(
                order_id=order_id,
                extracted_text=match["extracted_text"],
                product_id=match["product_id"],
                product_name=match["product_name"],
                confidence=match["confidence"],
                status="suggested"
            )
            db.add(suggestion)
        
        db.commit()
        
        # 5. Notify the shopkeeper via WebSocket!
        #    Find the shop owner's user_id to send the notification
        shop = db.query(Shop).filter(Shop.id == order.shop_id).first()
        if shop:
            # Run the async WebSocket send from this sync background task
            notification = {
                "type": "chitty_processed",
                "order_id": order_id,
                "items_found": len([m for m in matches if m["product_id"] is not None]),
                "total_lines": len(matches),
                "message": f"OCR complete! Found {len([m for m in matches if m['product_id']])} product matches from {len(matches)} lines."
            }
            
            # Use asyncio to send via the WebSocket manager
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(manager.send_to_user(shop.owner_id, notification))
                else:
                    loop.run_until_complete(manager.send_to_user(shop.owner_id, notification))
            except RuntimeError:
                # If no event loop exists, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(manager.send_to_user(shop.owner_id, notification))
    
    finally:
        db.close()
