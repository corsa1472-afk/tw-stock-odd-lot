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
            
        pattern = r'(?:[１２３123一二三]\s*[、.．：:]\s*)?(處置原因|處置期間|處置措施|原因|期間|措施)\s*[：:]\s*'
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

    for code, history in data.items():
        for date_key, disp in history.items():
            start = parse_minguo_date(disp.get("k"))
            end = parse_minguo_date(disp.get("f"))
            if start and end and start <= today <= end:
                reason, period, measures = extract_disposition_fields(disp.get("e", ""))
                if not reason:
                    reason = disp.get("i", "")
                
                print(f"Code: {code}")
                print(f"  Raw: {disp.get('e')}")
                print(f"  Raw i: {disp.get('i')}")
                print(f"  Processed Reason: {reason}")
                print(f"  Processed Period: {period}")
                print(f"  Processed Measures: {measures}")
                print("-" * 50)

if __name__ == '__main__':
    main()
