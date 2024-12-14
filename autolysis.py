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
try:
    csv_path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Error: File '{csv_path}' does not exist.")
    data = pd.read_csv(csv_path, encoding='ISO-8859-1')
except FileNotFoundError as e:
    print(e)
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred while loading the CSV: {e}")
    sys.exit(1)

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

# Generate and save pairplot
sns.pairplot(data.select_dtypes(include=[np.number]))
plt.savefig(os.path.join(output_directory, "pairplot.png"))
plt.close()

# Generate scatter plots for top correlated columns
top_correlations = correlation_matrix.unstack().sort_values(ascending=False)
top_pairs = top_correlations[top_correlations != 1].drop_duplicates().head(3)
for (col1, col2) in top_pairs.index:
    plt.figure(figsize=(8, 6))
    sns.scatterplot(x=data[col1], y=data[col2])
    plt.title(f'Scatter plot of {col1} vs {col2}')
    plt.savefig(os.path.join(output_directory, f'scatter_{col1}_vs_{col2}.png'))
    plt.close()

# Notes on data analysis
analysis_notes = (
    "- Summary statistics offer insights into metrics like mean, median, and standard deviation.\n"
    "- Missing values are highlighted for data quality assessment.\n"
    "- Correlation matrix highlights relationships among numerical columns.\n"
    "- Distribution plots visualize the distribution of data and identify outliers.\n"
    "- Pairplot visualizes relationships and patterns between features.\n"
    "- Clustering can be explored with KMeans or DBSCAN methods."
)

# Create prompt for LLM analysis
sample_data = data.head(5).to_dict(orient="records")
llm_prompt = f"""
You are an AI analyst. Here is the dataset overview:
- Columns: {list(data.columns)}
- Data types: {data.dtypes.to_dict()}
- Missing values: {missing_values.to_dict()}
- Total Rows: {data.shape[0]}, Total Columns: {data.shape[1]}
- Sample Data: {sample_data}

Provide a comprehensive analysis by identifying key trends, relationships, and anomalies. Highlight interesting features, possible clustering, and actionable insights.
"""

# Request LLM analysis
try:
    llm_analysis = request_llm_analysis(llm_prompt)
except Exception as e:
    print(f"LLM request failed: {e}")
    llm_analysis = (
        "Fallback Analysis: Check data correlations using the heatmap. Investigate distributions for possible outliers. "
        "Consider missing data imputation strategies to improve model performance. Use clustering methods like KMeans or DBSCAN."
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

### Pair Plot
![Pair Plot](pairplot.png)

### Scatter Plots
"""

# Append scatter plot images to README
for (col1, col2) in top_pairs.index:
    readme_content += f"![{col1} vs {col2} Scatter Plot](scatter_{col1}_vs_{col2}.png)\n"

# Save README file to the output directory
readme_path = os.path.join(output_directory, "README.md")
with open(readme_path, "w") as readme_file:
    readme_file.write(readme_content)

print(f"Analysis complete. Results saved in '{output_directory}/README.md' and visualization files.")
