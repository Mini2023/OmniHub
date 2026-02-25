import os
import time
from PIL import Image, ImageOps, ImageStat

class ImagePro:
    @staticmethod
    def strip_metadata(input_path, output_dir=None):
        base, ext = os.path.splitext(os.path.basename(input_path))
        target_dir = output_dir or os.path.dirname(input_path)
        output_path = os.path.join(target_dir, f"{base}_clean{ext}")
        try:
            img = Image.open(input_path)
            data = list(img.getdata())
            img_clean = Image.new(img.mode, img.size)
            img_clean.putdata(data)
            img_clean.save(output_path)
            return True, output_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def compress_image(input_path, quality=85, output_dir=None):
        base, ext = os.path.splitext(os.path.basename(input_path))
        target_dir = output_dir or os.path.dirname(input_path)
        output_path = os.path.join(target_dir, f"{base}_compressed{ext}")
        try:
            img = Image.open(input_path)
            if img.format in ['JPEG', 'JPG', 'WEBP']:
                img.save(output_path, optimize=True, quality=quality)
            else:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                output_path = os.path.join(target_dir, f"{base}_compressed.jpg")
                img.save(output_path, 'JPEG', optimize=True, quality=quality)
            return True, output_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def resize_image(input_path, width=None, height=None, quality=90, output_dir=None):
        try:
            img = Image.open(input_path)
            orig_w, orig_h = img.size
            
            if width and not height:
                height = int(orig_h * (width / orig_w))
            elif height and not width:
                width = int(orig_w * (height / orig_h))
            elif not width and not height:
                width, height = orig_w, orig_h

            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
            
            base, ext = os.path.splitext(os.path.basename(input_path))
            target_dir = output_dir or os.path.dirname(input_path)
            output_path = os.path.join(target_dir, f"{base}_resized{ext}")
            
            img_resized.save(output_path, quality=quality, optimize=True)
            return True, output_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def convert_format(input_path, target_format="PNG", output_dir=None):
        try:
            img = Image.open(input_path)
            base, _ = os.path.splitext(os.path.basename(input_path))
            target_dir = output_dir or os.path.dirname(input_path)
            ext = target_format.lower()
            if ext == "jpeg": ext = "jpg"
            output_path = os.path.join(target_dir, f"{base}.{ext}")
            
            if target_format.upper() == "JPG" or target_format.upper() == "JPEG":
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.save(output_path, "JPEG", quality=95)
            else:
                img.save(output_path, target_format.upper())
                
            return True, output_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_color_palette(input_path, num_colors=5):
        try:
            img = Image.open(input_path)
            img = img.resize((100, 100))
            result = img.convert('P', palette=Image.Palette.ADAPTIVE, colors=num_colors)
            result = result.convert('RGB')
            colors = result.getcolors(100*100)
            # Sort by count
            colors.sort(key=lambda x: x[0], reverse=True)
            palette = [f"#{r:02x}{g:02x}{b:02x}" for count, (r, g, b) in colors[:num_colors]]
            return True, palette
        except Exception as e:
            return False, str(e)

    @staticmethod
    def smart_focus_crop(input_path, aspect_ratio="1:1", output_dir=None):
        try:
            img = Image.open(input_path)
            w, h = img.size
            
            # Simple focus: assume interesting part is in center or rule of thirds
            # We'll do a center crop for now as "Smart Focus" placeholder
            target_ratio = 1.0
            if aspect_ratio == "16:9": target_ratio = 16/9
            elif aspect_ratio == "4:3": target_ratio = 4/3
            
            if w/h > target_ratio: # Wider than target
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                crop = (left, 0, left + new_w, h)
            else: # Taller than target
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                crop = (0, top, w, top + new_h)
                
            img_cropped = img.crop(crop)
            base, ext = os.path.splitext(os.path.basename(input_path))
            target_dir = output_dir or os.path.dirname(input_path)
            output_path = os.path.join(target_dir, f"{base}_cropped{ext}")
            img_cropped.save(output_path, quality=95)
            return True, output_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def remove_background(input_path, output_dir=None):
        try:
            from rembg import remove
            input_image = Image.open(input_path)
            output_image = remove(input_image)
            base, _ = os.path.splitext(os.path.basename(input_path))
            target_dir = output_dir or os.path.dirname(input_path)
            output_path = os.path.join(target_dir, f"{base}_no_bg.png")
            output_image.save(output_path)
            return True, output_path
        except ImportError:
            return False, "rembg not installed. Run 'pip install rembg'"
        except Exception as e:
            return False, str(e)
