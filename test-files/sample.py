# Sample Python file for project analysis testing
from typing import List, Dict
import asyncio

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def add_data(self, item: Dict):
        """Add data item to processor"""
        self.data.append(item)
    
    async def process_data(self) -> List[Dict]:
        """Process all data items asynchronously"""
        results = []
        for item in self.data:
            # Simulate async processing
            await asyncio.sleep(0.1)
            processed = {
                'id': item.get('id'),
                'processed': True,
                'value': item.get('value', 0) * 2
            }
            results.append(processed)
        return results

def calculate_metrics(data: List[Dict]) -> Dict:
    """Calculate basic metrics from data"""
    if not data:
        return {'count': 0, 'average': 0}
    
    values = [item.get('value', 0) for item in data]
    return {
        'count': len(values),
        'average': sum(values) / len(values),
        'max': max(values),
        'min': min(values)
    }