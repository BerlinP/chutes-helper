import requests
import logging
import pandas as pd
import io
import json

def fetch_api_data():
    """
    Fetches CSV data from multiple Chutes.ai API endpoints and returns processed data
    as pandas DataFrames
    """
    base_url = "https://api.chutes.ai"
    
    try:
        node_details_resp = requests.get(f"{base_url}/nodes/?detailed=true").json()
        chute_mining_stats_resp = requests.get(f"{base_url}/miner/stats?per_chute=true").json()
        return {
            'node_details': node_details_resp,
            'chute_mining_stats': chute_mining_stats_resp,
        }
        
    except Exception as e:
        logging.error(f"Error fetching data: {str(e)}")
        return None

if __name__ == "__main__":
    data = fetch_api_data()
    
    if data:
        # Load GPU prices
        with open('gpu-price.json', 'r') as f:
            gpu_price_data = json.load(f)
        
        # Track GPU counts per chute
        # Track compute units per chute
        compute_units = {}
        
        # First get GPU counts from node details
        node_details = data['node_details']
        chute_mining_stats = data['chute_mining_stats']

        for key, value in node_details.items():
            provisioned = value['provisioned']
            for item in provisioned:
                chute_id = item['chute']['chute_id']
                gpu = item['gpu']
                
                # Initialize the chute_id dict if it doesn't exist
                if chute_id not in compute_units:
                    compute_units[chute_id] = {
                        'name': item['chute']['name'],
                        'gpus': {},
                        'total_compute': 0
                    }
                
                # Initialize or increment the GPU count
                if gpu not in compute_units[chute_id]['gpus']:
                    compute_units[chute_id]['gpus'][gpu] = 1
                else:
                    compute_units[chute_id]['gpus'][gpu] += 1

        # Then add compute units from mining stats
        compute_stats = chute_mining_stats['past_day']['compute_units']
        for stat in compute_stats:
            chute_id = stat['chute_id']
            if chute_id in compute_units:
                compute = stat['compute_units']
                compute_units[chute_id]['total_compute'] += compute
        
        result = []
        for key, value in compute_units.items():
            # Calculate daily cost
            daily_cost = 0
            for gpu, count in value['gpus'].items():
                gpu_price = gpu_price_data.get(gpu.lower(), 0)  # Get price per hour, default to 0 if GPU not found
                daily_cost += gpu_price * count * 24  # Multiply by 24 for daily cost
            
            # Calculate compute units per dollar
            compute_per_dollar = value['total_compute'] / daily_cost if daily_cost > 0 else 0
            
            result.append({
                'chute_id': key,
                **value,
                'daily_cost': daily_cost,
                'compute_per_dollar': compute_per_dollar
            })

        # Sort result by total_compute in descending order
        result.sort(key=lambda x: x['compute_per_dollar'], reverse=True)

        # Print results
        for item in result:
            print(f"\nChute: {item['name']} ({item['chute_id']})")
            print(f"Compute Units per Dollar: {item['compute_per_dollar']:.2f}")
            print("GPU count:")
            for gpu, count in item['gpus'].items():
                print(f"  {gpu}: {count}")

    else:
        print("Failed to fetch data")
