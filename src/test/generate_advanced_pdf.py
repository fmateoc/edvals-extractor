import reportlab.lib.pagesizes as pagesizes
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def create_advanced_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=pagesizes.letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Page 1: Text, then Table that continues
    elements.append(Paragraph("Some initial text on page 1. Not a header.", styles['Normal']))
    
    data1 = [
        ["Header 1", "Header 2", "Header 3"],
        ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
        ["Row 2 Col 1\nmultiline", "Row 2 Col 2", "Row 2 Col 3"],
        ["Row 3 Col 1", "Row 3 Col 2", "Row 3 Col 3"]
    ]
    t1 = Table(data1, style=[
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.grey)
    ])
    elements.append(t1)
    elements.append(PageBreak())
    
    # Page 2: Starts with the continued table (no header, just a continued row with >2 empty cells)
    data2 = [
        ["Row 3 continued", "", ""],
        ["Row 4 Col 1", "Row 4 Col 2", "Row 4 Col 3"],
        ["Row 5 Col 1", "Row 5 Col 2", "Row 5 Col 3"]
    ]
    t2 = Table(data2, style=[
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ])
    elements.append(t2)
    elements.append(Paragraph("Some text after the table on page 2.", styles['Normal']))
    
    doc.build(elements)

create_advanced_pdf("advanced_sample.pdf")