# I was having a lot of trouble loading the Enron CSV because of 
# some weird formatting in the email bodies. 
# I added 'on_bad_lines' to just skip the broken rows so the 
# whole thing doesn't crash. 

import pandas as pd
import os

# Using the full path for now to make sure it finds the file
csv_path = r"C:\Users\hello\OneDrive\Documents\Intern\Project_10\data\email.csv"

def test_data_load():
    try:
        # Testing with just 100 rows to see the column structure
        # Added the python engine because it's usually better at handling messy text
        print(f"Attempting to read: {csv_path}")
        
        df = pd.read_csv(
            csv_path, 
            nrows=100, 
            on_bad_lines='skip', 
            engine='python'
        )
        
        print("Success! The CSV loaded fine.")
        print("\nColumns we have to work with:")
        print(df.columns.tolist())
        
        # Checking the first row to see if the message content looks right
        print("\nSample Data (Row 0):")
        print(df.iloc[0])

    except Exception as first_error:
        print(f"CSV didn't work, checking if it's actually an Excel file: {first_error}")
        
        try:
            # Sometimes these files get renamed incorrectly, so trying Excel as a backup
            df = pd.read_excel(csv_path, nrows=100)
            print("Loaded as Excel successfully.")
            print(df.columns.tolist())
        except Exception as second_error:
            print(f"Both formats failed. Might be a path or permission issue: {second_error}")

if __name__ == "__main__":
    test_data_load()