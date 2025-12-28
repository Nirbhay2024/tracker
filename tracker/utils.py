# from PIL import Image, ImageDraw, ImageFont
# from io import BytesIO
# from django.core.files.base import ContentFile
# import datetime

# def watermark_image(image_field, lat, lon):
#     try:
#         img = Image.open(image_field)
#         img = img.convert('RGB')
#         draw = ImageDraw.Draw(img)
#         width, height = img.size
        
#         # Dynamic font size
#         font_size = int(width * 0.04) 
        
#         try:
#     # Try standard Windows font (Arial)
#             font = ImageFont.truetype("arial.ttf", font_size)
#         except OSError:
#             try:
#                 # Try standard Linux font
#                 font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
#             except OSError:
#                 # Final fallback (Last resort, might be tiny)
#                 font = ImageFont.load_default()

#         # Text Content
#         company_text = "Nexsafe"
#         location_text = f"{lat}, {lon}"
#         time_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

#         # Top Bar (Company)
#         draw.rectangle([(0, 0), (width, font_size * 2)], fill=(0, 0, 0, 160))
#         draw.text((20, 20), company_text, fill=(255, 165, 0), font=font)

#         # Bottom Bar (Location)
#         bottom_box = font_size * 2.5
#         draw.rectangle([(0, height - bottom_box), (width, height)], fill=(0, 0, 0, 160))
#         draw.text((20, height - bottom_box + 10), location_text, fill=(255, 255, 255), font=font)
#         draw.text((20, height - font_size - 10), time_text, fill=(200, 200, 200), font=font)

#         buffer = BytesIO()
#         img.save(buffer, format='JPEG', quality=85)
#         return ContentFile(buffer.getvalue())

#     except Exception as e:
#         print(f"Watermark Error: {e}")
#         return image_field



from PIL import Image, ImageDraw, ImageFont, ExifTags, ImageOps
from io import BytesIO
from django.core.files.base import ContentFile
import datetime

# ==========================================
# 1. GPS EXTRACTION LOGIC (This was missing)
# ==========================================

def _convert_to_degrees(value):
    """Helper to convert GPS (Degrees, Minutes, Seconds) to a decimal float."""
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def get_gps_from_image(image_field):
    """
    Extracts latitude and longitude from an image's EXIF data.
    Returns: (lat_string, lon_string) or (None, None)
    """
    try:
        img = Image.open(image_field)
        exif_data = img._getexif()

        if not exif_data:
            return None, None

        # Find the GPSInfo tag
        gps_info = None
        for tag, value in ExifTags.TAGS.items():
            if value == 'GPSInfo':
                if tag in exif_data:
                    gps_info = exif_data[tag]
                break

        if not gps_info:
            return None, None

        # GPSInfo keys: 1=LatRef, 2=Lat, 3=LonRef, 4=Lon
        lat_gps = gps_info.get(2)
        lat_ref = gps_info.get(1)
        lon_gps = gps_info.get(4)
        lon_ref = gps_info.get(3)

        if lat_gps and lat_ref and lon_gps and lon_ref:
            # Convert to decimal
            lat = _convert_to_degrees(lat_gps)
            if lat_ref != 'N':
                lat = -lat
            
            lon = _convert_to_degrees(lon_gps)
            if lon_ref != 'E':
                lon = -lon
                
            # Return formatted as strings (to match your existing logic)
            return f"{lat:.6f}", f"{lon:.6f}"
            
    except Exception as e:
        print(f"EXIF Extraction Warning: {e}")
        
    return None, None

# ==========================================
# 2. WATERMARKING LOGIC
# ==========================================

def watermark_image(image_field, lat, lon):
    """
    Applies a watermark with Company Name, GPS, and Timestamp.
    Rotates image correctly based on EXIF data.
    """
    try:
        img = Image.open(image_field)
        
        # FIX: Rotate the image if it's sideways (common with phone photos)
        img = ImageOps.exif_transpose(img)
        
        img = img.convert('RGB')
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Dynamic font size (4% of image width)
        font_size = int(width * 0.04) 
        
        # Font Loading (Cross-Platform)
        try:
            # Windows
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            try:
                # Linux / Server
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except OSError:
                # Fallback
                font = ImageFont.load_default()
                
        # Text Content
        company_text = "Nexsafe"
        location_text = f"{lat}, {lon}"
        time_text = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        # Top Bar (Orange Company Name)
        # Draw semi-transparent background
        draw.rectangle([(0, 0), (width, font_size * 2)], fill=(0, 0, 0, 160))
        # Draw text
        draw.text((20, 20), company_text, fill=(255, 165, 0), font=font)

        # Bottom Bar (White Location & Time)
        bottom_box_height = font_size * 2.5
        # Draw semi-transparent background
        draw.rectangle([(0, height - bottom_box_height), (width, height)], fill=(0, 0, 0, 160))
        # Draw Location
        draw.text((20, height - bottom_box_height + 10), location_text, fill=(255, 255, 255), font=font)
        # Draw Time (smaller or slightly lower)
        draw.text((20, height - font_size - 10), time_text, fill=(200, 200, 200), font=font)

        # Save to buffer
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        
        # Return a Django ContentFile that can be saved to the model
        return ContentFile(buffer.getvalue())

    except Exception as e:
        print(f"Watermark Failed: {e}")
        # If watermarking crashes, ensure we return the original file pointer safely
        image_field.seek(0)
        return image_field