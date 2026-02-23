import os
from PIL import Image

class ImagePro:
    @staticmethod
    def strip_metadata(input_path):
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_clean{ext}"
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
    def compress_image(input_path, quality=85):
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_compressed{ext}"
        try:
            img = Image.open(input_path)
            if img.format in ['JPEG', 'JPG', 'WEBP']:
                img.save(output_path, optimize=True, quality=quality)
            else:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                output_path = f"{base}_compressed.jpg"
                img.save(output_path, 'JPEG', optimize=True, quality=quality)
            return True, output_path
        except Exception as e:
            return False, str(e)
