"""
Generate visualization plots for parser validation report
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def load_report(filepath='parser_validation_report.json'):
    with open(filepath, 'r') as f:
        return json.load(f)

def plot_kappa_scores(report):
    """Plot inter-annotator agreement (Kappa scores)"""
    
    fields = []
    mean_kappas = []
    std_kappas = []
    
    for field, metrics in report['inter_annotator_agreement']['pairwise_kappa'].items():
        fields.append(field.replace('_', ' ').title())
        mean_kappas.append(metrics['mean'])
        std_kappas.append(metrics['std'])
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(fields))
    ax.bar(x, mean_kappas, yerr=std_kappas, capsize=5, alpha=0.7, color='steelblue')
    
    # Add horizontal lines for interpretation thresholds
    ax.axhline(y=0.81, color='green', linestyle='--', label='Almost Perfect (κ > 0.81)')
    ax.axhline(y=0.61, color='orange', linestyle='--', label='Substantial (κ > 0.61)')
    ax.axhline(y=0.41, color='red', linestyle='--', label='Moderate (κ > 0.41)')
    
    ax.set_xlabel('Field', fontsize=12, fontweight='bold')
    ax.set_ylabel("Cohen's Kappa (κ)", fontsize=12, fontweight='bold')
    ax.set_title('Inter-Annotator Agreement - ULS++ Parser Validation', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(fields, rotation=45, ha='right')
    ax.set_ylim(0, 1)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('kappa_scores.png', dpi=300)
    print("Saved: kappa_scores.png")

def plot_agreement_rates(report):
    """Plot agreement rates"""
    
    fields = []
    rates = []
    
    for field, rate in report['inter_annotator_agreement']['agreement_rates'].items():
        fields.append(field.replace('_', ' ').title())
        rates.append(rate * 100)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.barh(fields, rates, color='coral', alpha=0.7)
    
    # Add value labels
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 1, bar.get_y() + bar.get_height()/2, 
                f'{width:.1f}%', ha='left', va='center', fontweight='bold')
    
    ax.set_xlabel('Agreement Rate (%)', fontsize=12, fontweight='bold')
    ax.set_title('Full Agreement Rate (All Annotators Agree)', fontsize=14, fontweight='bold')
    ax.set_xlim(0, 105)
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('agreement_rates.png', dpi=300)
    print("Saved: agreement_rates.png")

def plot_error_distribution(report):
    """Plot error distribution by category"""
    
    categories = []
    counts = []
    
    for category, count in report['error_analysis']['common_failures'][:5]:
        categories.append(category.replace('_', ' ').title())
        counts.append(count)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.pie(counts, labels=categories, autopct='%1.1f%%', startangle=90, colors=sns.color_palette('Set2'))
    ax.set_title('Error Distribution by Sample Category', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('error_distribution.png', dpi=300)
    print("Saved: error_distribution.png")

if __name__ == '__main__':
    report = load_report()
    plot_kappa_scores(report)
    plot_agreement_rates(report)
    plot_error_distribution(report)
    print("\n✅ All plots generated successfully!")