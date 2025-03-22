import requests

# Replace with your API key
API_KEY = "77d75f22-76e322b0-ee8ac8a1-80cf2f95"

# Fetch all cosmetics
url = "https://fortniteapi.io/v2/items/list"
headers = {
    "Authorization": API_KEY
}

response = requests.get(url, headers=headers)

# Debugging: Print the response status code and content
print(f"Status Code: {response.status_code}")
print(f"Response Content: {response.text}")

if response.status_code == 200:
    cosmetics = response.json().get("items", [])
    
    # Debugging: Print the first few cosmetics with their price
    print("\nFirst 5 Cosmetics with Price:")
    for cosmetic in cosmetics[:5]:
        print(f"ID: {cosmetic['id']}, Name: {cosmetic['name']}, Price: {cosmetic.get('price', 'N/A')}")
    
    # Filter shop-exclusive cosmetics (items with a non-zero price)
    shop_exclusive_cosmetics = [cosmetic["id"] for cosmetic in cosmetics if cosmetic.get("price", 0) > 0]
    
    # Save to a file
    with open("shop_exclusive.txt", "w", encoding="utf-8") as f:
        for cosmetic_id in shop_exclusive_cosmetics:
            f.write(f"{cosmetic_id}\n")
    
    print(f"\nSaved {len(shop_exclusive_cosmetics)} shop-exclusive cosmetics to 'shop_exclusive.txt'.")
else:
    print(f"Failed to fetch cosmetics: {response.status_code}")