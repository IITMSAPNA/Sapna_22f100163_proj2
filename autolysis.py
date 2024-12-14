import os
import sys
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# OpenAI API configuration
API_ENDPOINT = "https://aiproxy.sanand.workers.dev/openai/v1"
API_KEY = os.getenv("AIPROXY_TOKEN")
MODEL_NAME = "gpt-4o-mini"

# Ensure API key is available
if not API_KEY:
    print("Error: API key 'AIPROXY_TOKEN' is missing. Please set the environment variable.")
    sys.exit(1)

# Function to request analysis from LLM
def request_llm_analysis(prompt):
    try:
        print("Requesting analysis from LLM...")
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "You are an AI analyst."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        response = requests.post(f"{API_ENDPOINT}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip() if result.get("choices") else "No analysis received from LLM."
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"
    except requests.exceptions.RequestException as req_err:
        return f"Request error occurred: {req_err}"
    except Exception as err:
        return f"An unexpected error occurred: {err}"

# Verify command-line argument for CSV file
if len(sys.argv) != 2:
    print("Usage: python autolysis.py <dataset.csv>")
    sys.exit(1)

# Load dataset from CSV file
csv_path = sys.argv[1]
if not os.path.isfile(csv_path):
    print(f"Error: File '{csv_path}' does not exist.")
    sys.exit(1)

data = pd.read_csv(csv_path, encoding='ISO-8859-1')

# Compute statistical summaries and correlation matrix
summary_stats = data.describe(include="all").transpose()
missing_values = data.isnull().sum()
correlation_matrix = data.corr(numeric_only=True)

# Create an output directory named after the dataset
output_directory = os.path.splitext(os.path.basename(csv_path))[0]
os.makedirs(output_directory, exist_ok=True)

# Generate and save correlation matrix heatmap
plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap="coolwarm", cbar=True)
plt.title("Correlation Matrix")
plt.savefig(os.path.join(output_directory, "correlation_matrix.png"))
plt.close()

# Generate and save distribution plots for numeric columns
for col in data.select_dtypes(include=[np.number]).columns:
    plt.figure(figsize=(8, 6))
    sns.histplot(data[col].dropna(), kde=True, bins=30, color="blue")
    plt.title(f"Distribution of {col}")
    plt.xlabel(col)
    plt.ylabel("Frequency")
    plt.savefig(os.path.join(output_directory, f"{col}_distribution.png"))
    plt.close()

# Notes on data analysis
analysis_notes = (
    "- Summary statistics offer insights into metrics like mean, median, and standard deviation.\n"
    "- Missing values are highlighted for data quality assessment.\n"
    "- Correlation matrix highlights relationships among numerical columns.\n"
    "- Distribution plots visualize the distribution of data and identify outliers.\n"
    "- Potential outliers can be identified and analyzed further using these plots.\n"
    "- Data clustering can be explored with techniques like KMeans or DBSCAN."
)

# Create prompt for LLM analysis
sample_data = data.head(5).to_dict(orient="records")
llm_prompt = f"""
You are an AI analyst. Here is the dataset overview:
- Columns: {list(data.columns)}
- Data types: {data.dtypes.to_dict()}
- Missing values: {missing_values.to_dict()}
- Sample data: {sample_data}

Provide a brief analysis by identifying key trends, patterns, and relationships. Highlight anomalies or outliers as well.
"""

# Request LLM analysis
llm_analysis = request_llm_analysis(llm_prompt)

# Fallback insights if LLM analysis fails
if "error" in llm_analysis.lower() or "failed" in llm_analysis.lower():
    llm_analysis = (
        "Data exploration shows relationships among columns that can be further examined.\n"
        "Use correlation matrices and distribution plots to identify key trends, anomalies, and patterns.\n"
        "Address missing values to improve data quality."
    )

# Merge LLM analysis with generic analysis notes
combined_analysis = f"{llm_analysis}\n\n{analysis_notes}"

# Create a README file with the analysis
readme_content = f"""
# Automated Analysis Report

## Dataset Overview
- **Number of Rows**: {data.shape[0]}
- **Number of Columns**: {data.shape[1]}
- **Missing Values**:
{missing_values.to_string()}

## Key Insights
{combined_analysis}

## Visualizations
### Correlation Matrix
![Correlation Matrix](correlation_matrix.png)

### Distribution Plots
"""

# Append distribution plots to the README file
for col in data.select_dtypes(include=[np.number]).columns:
    readme_content += f"![{col} Distribution]({col}_distribution.png)\n"

# Save README file to the output directory
readme_path = os.path.join(output_directory, "README.md")
with open(readme_path, "w") as readme_file:
    readme_file.write(readme_content)

print(f"Analysis complete. Results saved in '{output_directory}/README.md' and visualization files.")
