import os
import pandas as pd
import numpy as np

def generate_schema_report():
    data_dir = "data/raw"
    report_path = "reports/schema_report.md"
    
    report = "# Schema Report\n\n"
    
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    
    if not files:
        report += "## ERROR: No CSV files found in data/raw\n"
        with open(report_path, "w") as f:
            f.write(report)
        return

    for file in files:
        file_path = os.path.join(data_dir, file)
        print(f"[INFO] Inspecting {file}...")
        
        # Load small subset for inspection
        try:
            df = pd.read_csv(file_path, nrows=1000)
            report += f"## Dataset: {file}\n"
            report += f"- **Shape (Sample):** {df.shape}\n"
            
            report += "### Columns & Types\n"
            report += "| Column | Type | Null % | Sample Value |\n"
            report += "| --- | --- | --- | --- |\n"
            
            # Since we only loaded 1000 rows, Null % might not be accurate for the whole file
            # but it's a start for discovery.
            for col in df.columns:
                null_pct = df[col].isnull().mean() * 100
                sample = df[col].iloc[0] if len(df) > 0 else "N/A"
                report += f"| {col} | {df[col].dtype} | {null_pct:.2f}% | {sample} |\n"
            
            report += "\n"
        except Exception as e:
            report += f"### Error Reading {file}: {e}\n\n"

    # Candidate Feature Analysis Section
    report += "## Feature Availability Matrix (Context Engine)\n"
    report += "| Feature | Existing Column (Guess) | Availability |\n"
    report += "| --- | --- | --- |\n"
    report += "| Account Age | | |\n"
    report += "| Beneficiary Info | | |\n"
    report += "| Transaction Velocity | | |\n"
    report += "| Geographic Info | | |\n"
    report += "| Device Info | | |\n"
    report += "| Timestamps | | |\n"
    
    with open(report_path, "w") as f:
        f.write(report)
    print(f"[SUCCESS] Schema report generated at {report_path}")

if __name__ == "__main__":
    generate_schema_report()
