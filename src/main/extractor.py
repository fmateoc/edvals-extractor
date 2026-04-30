import pdfplumber

def calculate_margins(pdf_path):
    min_table_top = float('inf')
    max_table_bottom = float('-inf')
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.find_tables()
            for table in tables:
                bbox = table.bbox
                if bbox[1] < min_table_top:
                    min_table_top = bbox[1]
                if bbox[3] > max_table_bottom:
                    max_table_bottom = bbox[3]
                    
    if min_table_top == float('inf'):
        min_table_top = 0
    if max_table_bottom == float('-inf'):
        max_table_bottom = float('inf')
        
    return min_table_top, max_table_bottom

def is_nested(table_bbox, other_tables):
    for other in other_tables:
        if other == table_bbox: continue
        if (table_bbox[0] >= other[0] and
            table_bbox[1] >= other[1] and
            table_bbox[2] <= other[2] and
            table_bbox[3] <= other[3]):
            return True
    return False

def format_nested_cell(page, cell_bbox):
    try:
        padded_bbox = (cell_bbox[0]+1, cell_bbox[1]+1, cell_bbox[2]-1, cell_bbox[3]-1)
        cropped = page.crop(padded_bbox)

        inner_tables = cropped.find_tables()
        if inner_tables:
            html_table = "<table>"
            inner = inner_tables[0]
            data = inner.extract()
            for row in data:
                html_table += "<tr>"
                for cell in row:
                    text = str(cell).replace('\n', '<br>') if cell else ""
                    html_table += f"<td>{text}</td>"
                html_table += "</tr>"
            html_table += "</table>"
            return html_table
        else:
            text = cropped.extract_text(layout=True)
            if not text: return ""
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return "<br>".join(lines)
    except:
        return ""

def extract_table_metadata(pdf_path, min_table_top, max_table_bottom):
    page_metadata = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.find_tables()
            words = page.extract_words()
            
            valid_words = [w for w in words if w['bottom'] > min_table_top and w['top'] < max_table_bottom]
            
            starts_with_table = False
            ends_with_table = False
            table_info = []
            extracted_tables = []
            
            if tables:
                outer_tables = []
                for t in tables:
                    if not is_nested(t.bbox, [ot.bbox for ot in tables]):
                        outer_tables.append(t)

                outer_tables = sorted(outer_tables, key=lambda tbl: tbl.bbox[1])

                for outer in outer_tables:
                    raw_data = outer.extract()
                    raw_cells = outer.cells

                    merged_data = []
                    current_row = None
                    current_bbox_group = None
                    
                    for row_idx, r in enumerate(raw_data):
                        r = [c if c else "" for c in r]
                        has_main_text = any(str(c).strip() for c in r[:3])
                        
                        if has_main_text:
                            if current_row:
                                merged_data.append((current_row, current_bbox_group))
                            current_row = r
                            # cells is a list of tuples or Nones. We need a list of actual tuples to track bbox
                            current_bbox_group = list(raw_cells[row_idx]) if row_idx < len(raw_cells) else [None]*len(r)
                        else:
                            if current_row:
                                for i_col in range(len(current_row)):
                                    if i_col < len(r) and str(r[i_col]).strip():
                                        if str(current_row[i_col]).strip():
                                            current_row[i_col] = str(current_row[i_col]) + "<br>" + str(r[i_col]).strip()
                                        else:
                                            current_row[i_col] = str(r[i_col]).strip()

                                if current_bbox_group and row_idx < len(raw_cells):
                                    new_row_cells = raw_cells[row_idx]
                                    for idx, c_box in enumerate(current_bbox_group):
                                        if idx < len(new_row_cells) and new_row_cells[idx] and isinstance(new_row_cells[idx], tuple):
                                            if c_box and isinstance(c_box, tuple):
                                                current_bbox_group[idx] = (
                                                    min(c_box[0], new_row_cells[idx][0]),
                                                    min(c_box[1], new_row_cells[idx][1]),
                                                    max(c_box[2], new_row_cells[idx][2]),
                                                    max(c_box[3], new_row_cells[idx][3])
                                                )
                                            else:
                                                current_bbox_group[idx] = new_row_cells[idx]
                            else:
                                current_row = r
                                current_bbox_group = list(raw_cells[row_idx]) if row_idx < len(raw_cells) else [None]*len(r)

                    if current_row:
                        merged_data.append((current_row, current_bbox_group))

                    cleaned_data = []
                    for row_text, row_boxes in merged_data:
                        new_row = []
                        for col_idx in range(min(4, len(row_text))):
                            if col_idx < 3:
                                new_row.append(row_text[col_idx].replace('\n', '<br>'))
                            else:
                                if row_boxes:
                                    last_boxes = [b for b in row_boxes[3:] if b and isinstance(b, tuple)]
                                    if last_boxes:
                                        min_x = min(b[0] for b in last_boxes)
                                        min_y = min(b[1] for b in last_boxes)
                                        max_x = max(b[2] for b in last_boxes)
                                        max_y = max(b[3] for b in last_boxes)
                                        cell_bbox = (min_x, min_y, max_x, max_y)
                                        html_val = format_nested_cell(page, cell_bbox)
                                        new_row.append(html_val)
                                    else:
                                        combined_rules = "<br>".join(str(c) for c in row_text[3:] if str(c).strip())
                                        new_row.append(combined_rules.replace('\n', '<br>'))
                                else:
                                    combined_rules = "<br>".join(str(c) for c in row_text[3:] if str(c).strip())
                                    new_row.append(combined_rules.replace('\n', '<br>'))
                        cleaned_data.append(new_row)

                    extracted_tables.append(cleaned_data)
                    table_info.append((4, len(cleaned_data), False))

                if outer_tables:
                    first_outer_table = outer_tables[0]
                    last_outer_table = outer_tables[-1]
                    
                    words_before = [w for w in valid_words if w['bottom'] < first_outer_table.bbox[1]]
                    starts_with_table = (len(words_before) == 0)
                    
                    words_after = [w for w in valid_words if w['top'] > last_outer_table.bbox[3]]
                    ends_with_table = (len(words_after) == 0)
                    
            page_metadata.append({
                'page_index': i,
                'starts_with_table': starts_with_table,
                'ends_with_table': ends_with_table,
                'table_info': table_info,
                'outer_tables': extracted_tables
            })
            
    return page_metadata

def identify_and_merge_tables(page_metadata):
    final_tables = []
    pending_table = None
    
    for i in range(len(page_metadata)):
        page = page_metadata[i]
        outer_tables_data = page['outer_tables']
        
        if not outer_tables_data:
            continue
            
        for j, table_data in enumerate(outer_tables_data):
            is_first_table_on_page = (j == 0)
            is_last_table_on_page = (j == len(outer_tables_data) - 1)
            
            if is_first_table_on_page and page['starts_with_table'] and pending_table is not None:
                if len(table_data) > 0 and len(pending_table) > 0:
                    if table_data[0] == pending_table[0]:
                        table_data = table_data[1:]
                
                if len(table_data) > 0 and len(pending_table) > 0:
                    first_row = table_data[0]
                    empty_count = sum(1 for cell in first_row if not str(cell).strip())
                    
                    is_row_continuation = False
                    if empty_count >= 2:
                        is_row_continuation = True
                    elif len(first_row) > 0 and "(continued)" in str(first_row[0]).lower():
                        is_row_continuation = True
                        
                    if is_row_continuation:
                        last_row_prev = pending_table[-1]
                        merged_row = []
                        max_cols = max(len(last_row_prev), len(first_row))
                        for col_idx in range(max_cols):
                            val1 = str(last_row_prev[col_idx]).strip() if col_idx < len(last_row_prev) else ""
                            val2 = str(first_row[col_idx]).strip() if col_idx < len(first_row) else ""
                            
                            val2_clean = val2.replace("(Continued)", "").replace("(continued)", "").strip()
                            
                            combined = val1
                            if combined and val2_clean:
                                combined += "<br>" + val2_clean
                            elif val2_clean:
                                combined = val2_clean
                            merged_row.append(combined)
                            
                        pending_table[-1] = merged_row
                        table_data = table_data[1:]
                
                pending_table.extend(table_data)
                
            else:
                if pending_table is not None:
                    final_tables.append(pending_table)
                pending_table = table_data
                
            if is_last_table_on_page:
                if page['ends_with_table']:
                    pass
                else:
                    final_tables.append(pending_table)
                    pending_table = None
            else:
                final_tables.append(pending_table)
                pending_table = None
                
    if pending_table is not None:
        final_tables.append(pending_table)
        
    return final_tables

def convert_to_markdown(tables):
    md_output = ""
    for table in tables:
        if not table: continue
        if len(table) > 0:
            header = table[0]
            md_output += "| " + " | ".join(str(c).replace("|", "\\|") for c in header) + " |\n"
            md_output += "| " + " | ".join("---" for _ in header) + " |\n"
            for row in table[1:]:
                md_output += "| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |\n"
        md_output += "\n"
    return md_output

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        print("Please provide a PDF path: python extractor.py <path_to_pdf>")
        sys.exit(1)
        
    min_top, max_bot = calculate_margins(pdf_path)
    metadata = extract_table_metadata(pdf_path, min_top, max_bot)
    merged_tables = identify_and_merge_tables(metadata)
    
    print(convert_to_markdown(merged_tables))
