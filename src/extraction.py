import pandas as pd
import os

# 1. Setup the Path (Using your verified folder)
file_path = r"C:\Users\hello\OneDrive\Documents\Intern\Layer10_Project\data\email.csv"

try:
    df = pd.read_csv(file_path, nrows=100, on_bad_lines='skip', engine='python')
    
    print("✅ Success! CSV loaded.")
    print("\n--- Column Names Found ---")
    print(df.columns.tolist())
    print("\n--- First Row Preview ---")
    print(df.iloc[0])

except Exception as e:
    print(f"❌ CSV failed, trying Excel: {e}")
    try:
        # 3. Fallback to Excel if CSV fails
        df = pd.read_excel(file_path, nrows=100, engine='openpyxl')
        print("✅ Success! Excel loaded.")
        print(df.columns.tolist())
    except Exception as e2:
        print(f"❌ Both failed. Error: {e2}")