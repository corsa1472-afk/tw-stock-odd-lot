import json
import datetime
import re

def main():
    with open('backend/data/dispositions_sw.json', 'r', encoding='utf-8') as f:
        data = json.load(f)['data']
    
    today = datetime.date(2026, 6, 14)
    
    def parse_minguo_date(date_str):
        if not date_str:
            return None
        try:
            parts = date_str.split('/')
            return datetime.date(int(parts[0]) + 1911, int(parts[1]), int(parts[2]))
        except Exception:
            return None

    def extract_disposition_fields(detail_text):
        reason = ""
        period = ""
        measures = ""
        if not detail_text:
            return reason, period, measures
            
        pattern = r'(?:[１２３123一二三]\s*[、.．：:]?\s*)?(處置原因|處置期間|處置措施|原因|期間|措施)\s*[：:]\s*'
        parts = re.split(pattern, detail_text)
        
        for i in range(1, len(parts), 2):
            heading = parts[i]
            content = parts[i+1].strip() if i+1 < len(parts) else ""
            if "原因" in heading:
                reason = content
            elif "期間" in heading:
                period = content
            elif "措施" in heading:
                measures = content
                
        return reason.strip(), period.strip(), measures.strip()

    with open('backend/active_disposition_details.txt', 'w', encoding='utf-8') as out:
        for code, history in data.items():
            for date_key, disp in history.items():
                start = parse_minguo_date(disp.get("k"))
                end = parse_minguo_date(disp.get("f"))
                if start and end and start <= today <= end:
                    reason, period, measures = extract_disposition_fields(disp.get("e", ""))
                    raw_reason = reason
                    if not reason:
                        reason = disp.get("i", "")
                    
                    # Clean up any leftover leading serial numbers
                    reason = re.sub(r'^[１２３123一二三][、.．：:]?\s*', '', reason).strip()
                    # Clean up trailing numbers
                    reason = re.sub(r'[\r\n\s]+[１２３123一二三123]$', '', reason).strip()
                    reason = re.sub(r'\s+[１２３123一二三123]$', '', reason).strip()
                    
                    # Supplement if matches 連續N個營業日
                    m = re.match(r'^(?:因)?連續([0-9一二三四五六七八九十]+)個?(營業日|交易日|日)$', reason)
                    if m:
                        n = m.group(1)
                        reason = f"連續{n}個交易日經本中心公布注意交易"
                    
                    out.write(f"Code: {code}\n")
                    out.write(f"  Raw: {disp.get('e')}\n")
                    out.write(f"  Raw i: {disp.get('i')}\n")
                    out.write(f"  Extracted Reason: {raw_reason}\n")
                    out.write(f"  Final Reason: {reason}\n")
                    out.write(f"  Extracted Period: {period}\n")
                    out.write(f"  Extracted Measures: {measures}\n")
                    out.write("-" * 50 + "\n")

if __name__ == '__main__':
    main()
