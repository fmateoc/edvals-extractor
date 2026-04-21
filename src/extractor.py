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
                for j, t in enumerate(tables):
                    is_inner = False
                    for k, other_t in enumerate(tables):
                        if j == k: continue
                        if (t.bbox[0] >= other_t.bbox[0] and
                            t.bbox[1] >= other_t.bbox[1] and
                            t.bbox[2] <= other_t.bbox[2] and
                            t.bbox[3] <= other_t.bbox[3]):
                            is_inner = True
                            break
                            
                    num_rows = len(t.cells)
                    num_cols = len(t.cells[0]) if num_rows > 0 else 0
                    table_info.append((num_cols, num_rows, is_inner))
                    
                    if not is_inner:
                        extracted_tables.append(t)
                        
                if extracted_tables:
                    extracted_tables = sorted(extracted_tables, key=lambda tbl: tbl.bbox[1])
                    first_outer_table = extracted_tables[0]
                    last_outer_table = extracted_tables[-1]
                    
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
        outer_tables = page['outer_tables']
        
        if not outer_tables:
            continue
            
        for j, table in enumerate(outer_tables):
            table_data = table.extract()
            table_data = [["" if cell is None else cell for cell in row] for row in table_data]
            
            is_first_table_on_page = (j == 0)
            is_last_table_on_page = (j == len(outer_tables) - 1)
            
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
                                combined += "\n" + val2_clean
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

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        print("Please provide a PDF path: python extractor.py <path_to_pdf>")
        sys.exit(1)
        
    min_top, max_bot = calculate_margins(pdf_path)
    print(f"Global min table top: {min_top}")
    print(f"Global max table bottom: {max_bot}")
    
    metadata = extract_table_metadata(pdf_path, min_top, max_bot)
    merged_tables = identify_and_merge_tables(metadata)
    
    print(f"\nExtracted {len(merged_tables)} final table(s):")
    for idx, table in enumerate(merged_tables):
        print(f"\n--- Table {idx+1} ---")
        for row in table:
            print([repr(cell) for cell in row])