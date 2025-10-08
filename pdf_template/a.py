#!/usr/bin/env python3
"""
PDF Placeholder → Invisible Form Fields (removes ALL placeholder text)
"""

import sys
import re
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import (
    DictionaryObject, ArrayObject, TextStringObject,
    NameObject, NumberObject
)
import fitz  # PyMuPDF


class PDFFormConverter:
    def __init__(self, src, dst):
        self.src = Path(src)
        self.dst = Path(dst)

    def get_field_dimensions(self, field_name, original_rect):
        """Customize field dimensions based on field type"""
        x0, y0, x1, y1 = original_rect
        original_width = x1 - x0
        original_height = y1 - y0

        # Title fields - make them longer
        if 'title' in field_name.lower():
            return [x0+4, y0-300, x0 + 400, y1 ]

        # Comment fields - keep them within reasonable bounds
        elif 'comment' in field_name.lower() or field_name == '2.c':
            return [x0, y0-18, x0 + 400, y1]

        # Name fields - make them 2 lines (increased height)
        elif any(pattern in field_name for pattern in ['r1_name', 'r2_name', 'guide_name']):
          return [x0+5, y1-160, x1 +70, y1 +4]# Increased height for 2 lines

        # Marks fields in table - keep original width, center aligned
        elif any(pattern in field_name for pattern in ['2.1', '2.2', '2.3', '2.4','2.5','2.6','2.7','2.8']):
            return [x0, y0-3, x1, y0 + max(15, original_height)]

        # Default case - standard sizing
        else:
            return [x0, y0-3, x0 + max(100, original_width), y0 + max(15, original_height)]



    def find_all_placeholders(self):
        """Dynamically find ALL placeholders in the PDF using regex"""
        doc = fitz.open(str(self.src))
        positions = []
        
        # Regex pattern to find ANY text between {{ and }}
        placeholder_pattern = r'\{\{([^}]+)\}\}'
        
        for pno in range(len(doc)):
            page = doc[pno]
            
            # Get all text from the page
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            
                            # Find all placeholder matches in this text span
                            matches = re.finditer(placeholder_pattern, text)
                            
                            for match in matches:
                                placeholder_full = match.group(0)  # Full {{placeholder}}
                                field_name = match.group(1)        # Just the name inside
                                
                                # Search for this specific placeholder on the page
                                text_instances = page.search_for(placeholder_full)
                                
                                for rect in text_instances:
                                    # Convert to PDF coordinates
                                    h = page.rect.height
                                    x1, y1 = rect.x0, h - rect.y1
                                    x2, y2 = rect.x1, h - rect.y0
                                    
                                    positions.append((pno, field_name, [x1, y1, x2, y2], placeholder_full))
                                    print(f"Found placeholder: {placeholder_full} → field: {field_name}")
        
        doc.close()
        return positions

    def remove_placeholder_text(self, positions):
        """Remove ALL placeholder text by redacting it"""
        temp_path = self.src.with_suffix('.temp.pdf')
        doc = fitz.open(str(self.src))
        
        removed_count = 0
        for pno, name, rect, full_placeholder in positions:
            page = doc[pno]
            # Find and redact all instances of this placeholder
            text_instances = page.search_for(full_placeholder)
            
            for text_rect in text_instances:
                # Add redaction annotation (removes text)
                page.add_redact_annot(text_rect, text="")
                removed_count += 1
                print(f"Removing: {full_placeholder}")
        
        # Apply all redactions
        for pno in range(len(doc)):
            doc[pno].apply_redactions()
        
        doc.save(str(temp_path))
        doc.close()
        
        print(f"✅ Removed {removed_count} placeholder instances")
        return temp_path

    def insert_fields(self, temp_path, positions):
        reader = PdfReader(str(temp_path))
        writer = PdfWriter()
        bypage = {}
        for pno, name, rect, _ in positions:
            bypage.setdefault(pno, []).append((name, rect))

        field_count = 0
        for i, page in enumerate(reader.pages):
            annots = page.get("/Annots", ArrayObject())
            if i in bypage:
                for name, original_rect in bypage[i]:
                    # Get customized dimensions for this field
                    rect = self.get_field_dimensions(name, original_rect)
                    
                    # In the insert_fields method, replace the widget creation with:
                    widget = DictionaryObject({
                        NameObject("/Type"):     NameObject("/Annot"),
                        NameObject("/Subtype"):  NameObject("/Widget"),
                        NameObject("/FT"):       NameObject("/Tx"),
                        NameObject("/T"):        TextStringObject(name),
                        NameObject("/Rect"):     ArrayObject([NumberObject(v) for v in rect]),
                        # NameObject("/Ff"):       NumberObject(0),
                        NameObject("/Ff"): NumberObject(4096) if ('comment' in name.lower()  or 
                                         any(pattern in name for pattern in ['r1_name', 'r2_name', 'guide_name','title','2.c'])) else NumberObject(0),
                         
                        NameObject("/DA"): TextStringObject(
                        "0 0 0 rg /TiRo 13 Tf" if ('comment' in name.lower() or name == '2.c') 
                        else "0 0 0 rg /TiRo 13 Tf"
                        ),

                        # Center alignment for marks fields
                        NameObject("/Q"):        NumberObject(1) if any(pattern in name for pattern in ['2.1', '2.2', '2.3', '2.4','2.5','2.6','2.7','2.8']) else NumberObject(0),
                        # Invisible border
                        NameObject("/BS"):       DictionaryObject({
                            NameObject("/W"): NumberObject(0),
                            NameObject("/S"): NameObject("/S")
                        }),
                        # Invisible background
                        NameObject("/MK"):       DictionaryObject({
                            NameObject("/BC"): ArrayObject([]),
                            NameObject("/BG"): ArrayObject([])
                        })
                    })
                    annots.append(writer._add_object(widget))
                    field_count += 1
                    print(f"Added field: {name} with dimensions: {rect}")
            
            if annots:
                page[NameObject("/Annots")] = annots
            writer.add_page(page)

        # Create AcroForm so fields show up
        widgets = []
        for obj in writer._objects:
            if isinstance(obj, DictionaryObject) and obj.get("/Subtype") == "/Widget":
                widgets.append(writer._add_object(obj))
        
        if widgets:
            writer._root_object[NameObject("/AcroForm")] = writer._add_object(
                DictionaryObject({
                    NameObject("/Fields"): ArrayObject(widgets),
                    NameObject("/NeedAppearances"): NumberObject(1),
                    NameObject("/DA"): TextStringObject("0 0 0 rg /TiRo 12 Tf")
                })
            )

        with open(self.dst, "wb") as f:
            writer.write(f)
        
        print(f"✅ Added {field_count} transparent form fields")

    def convert(self):
        print("🔍 Scanning PDF for ALL placeholders...")
        positions = self.find_all_placeholders()
        
        if not positions:
            print("❌ No {{placeholders}} found in the PDF!")
            return False
        
        print(f"\n📋 Found {len(positions)} unique placeholders:")
        unique_fields = set(pos[1] for pos in positions)
        for field in sorted(unique_fields):
            print(f"   - {field}")
        
        print(f"\n🗑️  Removing placeholder text...")
        temp_path = self.remove_placeholder_text(positions)
        
        print(f"\n📝 Inserting transparent form fields...")
        self.insert_fields(temp_path, positions)
        
        # Clean up temp file
        temp_path.unlink()
        
        print(f"\n✅ Conversion completed!")
        print(f"📄 Output: {self.dst}")
        return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python pdf_converter.py input.pdf output.pdf")
        sys.exit(1)
    
    converter = PDFFormConverter(sys.argv[1], sys.argv[2])
    success = converter.convert()
    
    if success:
        print("\n🎉 Success! All placeholders converted to invisible form fields.")
    else:
        print("\n❌ Conversion failed.")